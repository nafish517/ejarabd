import os
import re
import sys
import time
import random
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Union, Set
import httpx
from bs4 import BeautifulSoup

# Windows কনসোলে UTF-8 এনকোডিং
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.ingestion import (
    clean_text,
    clean_numeric_value,
    clean_datetime_value,
    to_en_number
)

logger = logging.getLogger("ejarabd.egp_client")
logging.basicConfig(level=logging.INFO)

# Verified official URLs from backend/EGP_SOURCE_DISCOVERY.md
EGP_BASE_URL = "https://www.eprocure.gov.bd"
EGP_INDEX_URL = f"{EGP_BASE_URL}/Index.jsp"
EGP_ALL_TENDERS_URL = f"{EGP_BASE_URL}/resources/common/AllTenders.jsp?h=t"
EGP_SEARCH_SERVLET_URL = f"{EGP_BASE_URL}/TenderDetailsServlet"
EGP_VIEW_TENDER_URL = f"{EGP_BASE_URL}/resources/common/ViewTender.jsp"

DEFAULT_DELAY_MIN = 1.0  # seconds
DEFAULT_DELAY_MAX = 2.0  # seconds
DEFAULT_TIMEOUT = 25.0   # seconds
DEFAULT_MAX_RETRIES = 3


class EGPSessionError(httpx.HTTPError):
    """e-GP সেশন সংক্রান্ত ব্যতিক্রম"""
    def __init__(self, message: str):
        super().__init__(message)


class EGPClient:
    """
    বাংলাদেশ জাতীয় e-GP পোর্টালের (eprocure.gov.bd) জন্য প্রোডাকশন-রেডি ক্লায়েন্ট।
    
    বৈশিষ্ট্যসমূহ:
    - স্বয়ংক্রিয় সেশন হ্যান্ডলিং (JSESSIONID নিশ্চিতকরণ)
    - সেশন টাইমআউট ডিটেকশন ও স্বয়ংক্রিয় রিকভারি
    - নম্র ক্রলিং ও কনফিগারযোগ্য বিলম্ব (Polite Rate Limiting)
    - এক্সপোনেনশিয়াল ব্যাকঅফ সহ নিয়ন্ত্রিত রিট্রাই (Max Retries)
    - নিশ্চিত উৎস আর্কিটেকচার অনুযায়ী লিস্টিং ও ডিটেইল পার্সিং
    - অনুমানহীন মান: estimated_value_bdt কঠোরভাবে None রাখা
    - নিরাপদ ও ডুপ্লিকেট-রোধী পেজিনেশন (Multi-page safe pagination)
    """

    def __init__(
        self,
        base_url: str = EGP_BASE_URL,
        delay_min: float = DEFAULT_DELAY_MIN,
        delay_max: float = DEFAULT_DELAY_MAX,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        user_agent: Optional[str] = None
    ):
        self.base_url = base_url.rstrip("/")
        self.delay_min = max(0.0, float(delay_min))
        self.delay_max = max(self.delay_min, float(delay_max))
        self.timeout = float(timeout)
        self.max_retries = int(max_retries)
        self.last_request_time = 0.0
        self.session_initialized = False

        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/122.0.0.0 Safari/537.36"
        )

        self._init_http_client()

    def _init_http_client(self):
        """নতুন HTTPX ক্লায়েন্ট প্রস্তুত করা"""
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive"
        }
        self.client = httpx.Client(
            headers=headers,
            follow_redirects=True,
            timeout=self.timeout,
            verify=False  # e-GP পোর্টাল ইন্টারনাল সার্টিফিকেট ইস্যু প্রতিরোধের জন্য
        )
        self.session_initialized = False

    def close(self):
        """ক্লায়েন্ট সেশন বন্ধ করা"""
        if hasattr(self, "client") and self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.session_initialized = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _sleep_polite(self):
        """সরকারি সার্ভারে অতিরিক্ত চাপ না দিতে কনফিগারযোগ্য বিলম্ব"""
        if self.delay_max > 0:
            delay = random.uniform(self.delay_min, self.delay_max)
            elapsed = time.time() - self.last_request_time
            if elapsed < delay:
                sleep_duration = delay - elapsed
                time.sleep(sleep_duration)
        self.last_request_time = time.time()

    def polite_delay(self):
        """পাবলিক ইন্টারফেস: নম্র ক্রলিং স্লিপ"""
        self._sleep_polite()

    @property
    def has_active_session(self) -> bool:
        """সেশন সক্রিয় আছে কিনা"""
        return bool(self.session_initialized)

    def init_session(self, force_refresh: bool = False) -> bool:
        """সেশন শুরু করার পাবলিক মেথড"""
        return self.ensure_session(force_refresh=force_refresh)

    def is_session_timed_out(self, html_or_text: str = "", status_code: int = 200) -> bool:
        """সেশন মেয়াদোত্তীর্ণের বার্তা কি না তা নির্ণয়"""
        if status_code in [301, 302]:
            return True
        text_lower = html_or_text.lower() if html_or_text else ""
        return (
            "session has been expired" in text_lower or
            "session expired" in text_lower or
            "session timed out" in text_lower or
            "<title>session expired</title>" in text_lower or
            "sessiontimedout.jsp" in text_lower
        )

    def recover_session_if_needed(self):
        """সেশন নবায়ন বা রিকভারি করা"""
        self.init_session(force_refresh=True)

    def ensure_session(self, force_refresh: bool = False) -> bool:
        """
        /Index.jsp ভিজিট করে JSESSIONID সেশন কুকি প্রতিষ্ঠা বা রিনিউ করা
        """
        if self.session_initialized and not force_refresh:
            return True

        if force_refresh:
            self.close()
            self._init_http_client()

        url = f"{self.base_url}/Index.jsp"
        logger.info(f"Establishing e-GP session via {url}...")
        self._sleep_polite()

        try:
            r = self.client.get(url)
            if r.status_code == 200:
                cookies = dict(self.client.cookies)
                if "JSESSIONID" in cookies:
                    logger.info(f"e-GP session established successfully. JSESSIONID: {cookies['JSESSIONID'][:10]}...")
                    self.session_initialized = True
                    return True
                else:
                    logger.warning("No JSESSIONID in response cookies, session may be incomplete.")
                    self.session_initialized = True
                    return True
            else:
                logger.error(f"Failed to reach e-GP Index.jsp (HTTP {r.status_code})")
                return False
        except Exception as e:
            logger.error(f"Error establishing e-GP session: {e}")
            return False

    def _execute_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """
        স্বয়ংক্রিয় সেশন রিকভারি এবং রিট্রাই সহ HTTP রিকোয়েস্ট সম্পাদন
        """
        self.ensure_session()

        req_headers = dict(headers or {})
        retries = 0

        while retries <= self.max_retries:
            self._sleep_polite()
            try:
                if method.upper() == "POST":
                    r = self.client.post(url, data=data, headers=req_headers)
                else:
                    r = self.client.get(url, headers=req_headers)

                # সেশন মেয়াদোত্তীর্ণ হয়েছে কিনা পরীক্ষা
                if self.is_session_timed_out(r.text, r.status_code):
                    logger.warning("e-GP session timeout detected. Reinitializing session and retrying...")
                    self.ensure_session(force_refresh=True)
                    retries += 1
                    continue

                if r.status_code == 200:
                    return r

                # সাময়িক সার্ভার এরর (5xx)
                if r.status_code >= 500:
                    retries += 1
                    wait_time = (2 ** retries) * 0.5
                    logger.warning(f"e-GP server error HTTP {r.status_code}. Retrying in {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue

                return r

            except (httpx.TimeoutException, httpx.NetworkError) as e:
                retries += 1
                if retries > self.max_retries:
                    logger.error(f"Request failed after {self.max_retries} retries: {e}")
                    raise
                wait_time = (2 ** retries) * 0.5
                logger.warning(f"Connection issue ({e}). Retrying ({retries}/{self.max_retries}) in {wait_time:.1f}s...")
                time.sleep(wait_time)

        raise EGPSessionError(f"Failed to execute {method} {url} after {self.max_retries} retries")

    def _safe_request(
        self,
        method: str,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> httpx.Response:
        """অভ্যন্তরীণ ও টেস্টের জন্য নিরাপদ রিকোয়েস্ট ইন্টারফেস"""
        return self._execute_request(method=method, url=url, data=data, headers=headers)

    # -------------------------------------------------------------------------
    # PARSING METHODS (Deterministic & Pure)
    # -------------------------------------------------------------------------

    @staticmethod
    def parse_listing_html(html: str, base_url: str = EGP_BASE_URL) -> List[Dict[str, Any]]:
        """
        TenderDetailsServlet থেকে প্রাপ্ত HTML টেবিল রো (<tr>...</tr>) পার্স করা।
        বিশুদ্ধ ডিটারমিনিস্টিক মেথড (স্ট্যাটিক ফিক্সচারেও সরাসরি টেস্টযোগ্য)।
        """
        if not html or not html.strip():
            return []

        soup = BeautifulSoup(html, "html.parser")
        rows = soup.find_all("tr")
        tenders: List[Dict[str, Any]] = []

        for tr in rows:
            tds = tr.find_all("td")
            if len(tds) < 6:
                continue

            try:
                # 1. টেন্ডার আইডি নিষ্কাশন (একাধিক নিশ্চিত কৌশলের মাধ্যমে)
                tender_id = ""
                # কৌশল ১: হিডেন ইনপুট ফিল্ড (<input type="hidden" name="id" value="...">)
                hidden_id = tr.find("input", {"name": "id"})
                if hidden_id and hidden_id.get("value", "").strip():
                    tender_id = hidden_id["value"].strip()

                # কৌশল ২: জাভাস্ক্রিপ্ট viewTender ফাংশন বা URL প্যারামিটার
                if not tender_id:
                    row_html = str(tr)
                    link_match = re.search(r"viewTender\(['\"]?(\d+)['\"]?\)", row_html)
                    if link_match:
                        tender_id = link_match.group(1)

                # কৌশল ৩: Col 1 বা Col 0 থেকে ডিজিট লাইন
                col1_lines = [clean_text(x) for x in tds[1].get_text(separator="\n").split("\n") if clean_text(x)]
                if not tender_id and col1_lines:
                    for line in col1_lines:
                        clean_l = line.replace(",", "").strip()
                        if clean_l.isdigit() and len(clean_l) >= 4:
                            tender_id = clean_l
                            break

                if not tender_id and len(tds) > 0:
                    col0_text = clean_text(tds[0].get_text()).replace(",", "").strip()
                    if col0_text.isdigit() and len(col0_text) >= 5:
                        tender_id = col0_text

                # 2. রেফারেন্স নম্বর ও স্ট্যাটাস
                reference_no = ""
                status = "active"

                for line in col1_lines:
                    clean_l = line.replace(",", "").strip()
                    if clean_l == tender_id:
                        continue
                    clean_lower = clean_l.lower()
                    if "live" in clean_lower:
                        status = "active"
                    elif "corrigendum" in clean_lower or "amend" in clean_lower:
                        status = "amended"
                    elif "cancel" in clean_lower:
                        status = "cancelled"
                    elif not reference_no:
                        reference_no = clean_l

                if not reference_no and len(tds) > 1:
                    raw_col1 = clean_text(tds[1].get_text())
                    if raw_col1 != tender_id and not reference_no:
                        reference_no = raw_col1

                # 3. Procurement Nature & Title
                col2_text = tds[2].get_text(separator="\n")
                col2_lines = [clean_text(x) for x in col2_text.split("\n") if clean_text(x)]
                proc_nature = col2_lines[0].replace(",", "").strip() if col2_lines else "Works"

                title_tag = tds[2].find("span", id=lambda x: x and x.startswith("tenderBrief"))
                if title_tag:
                    title = clean_text(title_tag.get_text())
                else:
                    p_tag = tds[2].find("p")
                    if p_tag:
                        title = clean_text(p_tag.get_text())
                    elif len(col2_lines) > 1:
                        title = " ".join(col2_lines[1:])
                    else:
                        title = clean_text(tds[2].get_text())

                # 4. Ministry, Division, Organization, PE Office
                col3_lines = [clean_text(x) for x in tds[3].get_text(separator="\n").split("\n") if clean_text(x)]
                ministry = col3_lines[0].replace(",", "").strip() if len(col3_lines) > 0 else "Government of Bangladesh"
                if len(col3_lines) >= 4:
                    division = col3_lines[1].replace(",", "").strip()
                    agency = col3_lines[2].replace(",", "").strip()
                    pe_office = col3_lines[3].replace(",", "").strip()
                elif len(col3_lines) == 3:
                    division = None
                    agency = col3_lines[1].replace(",", "").strip()
                    pe_office = col3_lines[2].replace(",", "").strip()
                elif len(col3_lines) == 2:
                    division = None
                    agency = col3_lines[1].replace(",", "").strip()
                    pe_office = col3_lines[1].replace(",", "").strip()
                else:
                    division = None
                    agency = ministry
                    pe_office = ministry

                # 5. Procurement Type, Procurement Method
                col4_lines = [clean_text(x) for x in tds[4].get_text(separator="\n").split("\n") if clean_text(x)]
                proc_type = col4_lines[0].replace(",", "").strip() if len(col4_lines) > 0 else "NCT"
                proc_method = col4_lines[1].replace(",", "").strip() if len(col4_lines) > 1 else "OTM"

                # 6. Publishing Date & Closing Date
                col5_lines = [clean_text(x) for x in tds[5].get_text(separator="\n").split("\n") if clean_text(x)]
                pub_date = None
                closing_date = None
                if len(col5_lines) > 0:
                    pub_date = clean_datetime_value(col5_lines[0].replace(",", "").strip())
                if len(col5_lines) > 1:
                    closing_date = clean_datetime_value(col5_lines[1].replace(",", "").strip())

                # Source URL
                source_url = f"{base_url}/resources/common/ViewTender.jsp?id={tender_id}&h=t"

                tenders.append({
                    "tender_id": tender_id,
                    "reference_no": reference_no,
                    "title": title,
                    "category": proc_nature,
                    "procurement_nature": proc_nature,
                    "procurement_type": proc_type,
                    "procurement_method": proc_method,
                    "ministry": ministry,
                    "division": division,
                    "agency": agency,
                    "procuring_entity_office": pe_office,
                    "publication_date": pub_date,
                    "closing_date": closing_date,
                    "status": status,
                    "is_amendment": (status == "amended"),
                    "source_url": source_url,
                    "source_type": "e-GP National Portal"
                })
            except Exception as e:
                logger.debug(f"Error parsing row in listing HTML: {e}")
                continue

        return tenders

    @staticmethod
    def parse_tender_details_html(html: str, tender_id: Optional[str] = None) -> Dict[str, Any]:
        """
        ViewTender.jsp থেকে প্রাপ্ত বিস্তারিত নোটিশের তথ্য পার্স করা।
        - যোগ্যতা শর্তাবলি (Eligibility of Tenderer)
        - টেন্ডার সিকিউরিটি (Lot table)
        - শিডিউল মূল্য
        - তারিখসমূহ
        - কাজের এলাকা/জেলা
        - বাজেট: কঠোরভাবে None (আইনগতভাবে নোটিশে অপ্রকাশিত)
        """
        if not html:
            return {}

        soup = BeautifulSoup(html, "html.parser")
        details: Dict[str, Any] = {}

        # ১. টেবিল সেলসমূহ থেকে লেবেল-ভ্যালু সংগ্রহ
        fields_map: Dict[str, str] = {}
        for tr in soup.find_all("tr"):
            tds = tr.find_all(["td", "th"])
            if len(tds) >= 2:
                for i in range(0, len(tds) - 1, 2):
                    lbl = clean_text(tds[i].get_text())
                    val = clean_text(tds[i + 1].get_text())
                    if lbl and val:
                        fields_map[lbl.lower().rstrip(" :")] = val

        # টেন্ডার আইডি
        discovered_id = fields_map.get("tender/proposal id") or tender_id
        if discovered_id:
            details["tender_id"] = str(discovered_id).strip()

        # জেলা ও অফিস
        pe_district = fields_map.get("procuring entity district") or fields_map.get("district")
        if pe_district:
            details["procuring_entity_district"] = pe_district
            details["project_location_district"] = pe_district

        pe_name = fields_map.get("procuring entity name")
        if pe_name:
            details["procuring_entity_office"] = pe_name

        agency_name = fields_map.get("organization")
        if agency_name:
            details["agency"] = agency_name

        # ২. যোগ্যতা শর্তাবলি (Eligibility of Tenderer)
        elig_text = None
        for td in soup.find_all("td"):
            txt = td.get_text(strip=True)
            if "Eligibility of Tenderer" in txt:
                next_td = td.find_next_sibling("td")
                if next_td:
                    elig_text = clean_text(next_td.get_text(separator=" ", strip=True))
                else:
                    parent = td.find_parent("tr")
                    if parent:
                        cells = parent.find_all("td")
                        if len(cells) > 1:
                            elig_text = clean_text(cells[-1].get_text(separator=" ", strip=True))
                break

        details["raw_eligibility_text"] = elig_text
        details["eligibility_criteria"] = elig_text

        # ৩. লট টেবিল থেকে টেন্ডার সিকিউরিটি ও নির্দিষ্ট লোকেশন
        security_amount = None
        location_details = None
        for table in soup.find_all("table"):
            table_str = table.get_text()
            if "Tender/Proposal security" in table_str or "Amount in BDT" in table_str or "Lot No." in table_str:
                for tr in table.find_all("tr"):
                    row_cells = [clean_text(c.get_text()) for c in tr.find_all(["td", "th"])]
                    if len(row_cells) >= 4 and row_cells[0] and row_cells[0].isdigit():
                        location_details = row_cells[2]
                        sec_parsed = clean_numeric_value(row_cells[3])
                        if sec_parsed is not None:
                            security_amount = sec_parsed
                        break
                if security_amount is not None:
                    break

        details["tender_security_bdt"] = security_amount
        if location_details:
            details["location"] = location_details
            details["project_location_details"] = location_details

        # ৪. আর্থিক তথ্য: বাজেট কঠোরভাবে None (কখনো সিকিউরিটি থেকে অনুমান নয়)
        details["estimated_value_bdt"] = None

        # ফিল্ড প্যাটার্ন সার্চ হেল্পার (স্পেস ও স্ল্যাশ নিরপেক্ষ)
        def get_by_pattern(*keywords: str) -> Optional[str]:
            for kw in keywords:
                clean_kw = kw.lower().replace(" ", "").replace("/", "")
                for k, v in fields_map.items():
                    clean_k = k.lower().replace(" ", "").replace("/", "")
                    if clean_kw in clean_k:
                        return v
            return None

        # শিডিউল মূল্য (Document Price)
        doc_price = clean_numeric_value(
            get_by_pattern("documentprice", "priceinbdt") or
            fields_map.get("document price")
        )
        details["document_price_bdt"] = doc_price

        # ৫. তারিখসমূহ
        details["publication_date"] = clean_datetime_value(
            get_by_pattern("publicationdate") or
            fields_map.get("scheduled tender/proposal publication date and time")
        )
        details["document_last_selling_date"] = clean_datetime_value(
            get_by_pattern("lastselling", "downloadingdate") or
            fields_map.get("last selling date and time")
        )
        details["closing_date"] = clean_datetime_value(
            get_by_pattern("closingdate") or
            fields_map.get("closing date and time")
        )
        details["opening_date"] = clean_datetime_value(
            get_by_pattern("openingdate") or
            fields_map.get("opening date and time")
        )

        # স্ট্যাটাস
        raw_st = fields_map.get("tender/proposal status", "").lower()
        if "live" in raw_st:
            details["status"] = "active"
            details["is_amendment"] = False
        elif "corrigendum" in raw_st or "amend" in raw_st:
            details["status"] = "amended"
            details["is_amendment"] = True
        elif raw_st:
            details["status"] = raw_st

        return details

    # -------------------------------------------------------------------------
    # OPERATIONAL API & PAGINATION METHODS
    # -------------------------------------------------------------------------

    def _search_page_raw(self, page: int, page_size: int, **kwargs) -> List[Dict[str, Any]]:
        """Mockable raw page search returning list of tenders"""
        res = self.search_page(page_no=page, size=page_size, **kwargs)
        if isinstance(res, dict):
            return res.get("tenders", [])
        elif isinstance(res, list):
            return res
        return []

    def search_page(
        self,
        page_no: int = 1,
        size: int = 10,
        proc_nature: str = "2",
        proc_type: str = "",
        proc_method: str = "0",
        tender_id: str = "",
        ref_no: str = "",
        pub_dt_from: str = "",
        pub_dt_to: str = "",
        close_dt_from: str = "",
        close_dt_to: str = "",
        cpv_category: str = "",
        is_frame: str = "0",
        view_type: str = "Live",
        keyword: str = ""
    ) -> Dict[str, Any]:
        """TenderDetailsServlet-এ একক পৃষ্ঠা অনুসন্ধান"""
        headers = {
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Referer": f"{self.base_url}/resources/common/AllTenders.jsp?h=t"
        }

        post_data = {
            "funName": "AllTenders",
            "viewType": view_type,
            "departmentId": "",
            "office": "",
            "procNature": str(proc_nature),
            "procType": str(proc_type),
            "procMethod": str(proc_method),
            "tenderId": str(tender_id).strip(),
            "refNo": str(ref_no).strip(),
            "pubDtFrm": pub_dt_from,
            "pubDtTo": pub_dt_to,
            "closeDtFrm": close_dt_from,
            "closeDtTo": close_dt_to,
            "cpvCategory": cpv_category,
            "isFrame": str(is_frame),
            "pageNo": str(page_no),
            "size": str(size),
            "h": "t"
        }

        if keyword:
            post_data["keyword"] = str(keyword).strip()
            post_data["homeWSearch"] = "homeWSearch"

        r = self._execute_request(
            method="POST",
            url=EGP_SEARCH_SERVLET_URL,
            data=post_data,
            headers=headers
        )

        html = r.text
        tenders = self.parse_listing_html(html, base_url=self.base_url)

        total_pages = 1
        count_on_page = len(tenders)

        soup = BeautifulSoup(html, "html.parser")
        tp_input = soup.find("input", id="totalPages")
        if tp_input and tp_input.get("value", "").isdigit():
            total_pages = int(tp_input["value"])

        cnt_input = soup.find("input", id="cntTenBrief")
        if cnt_input and cnt_input.get("value", "").isdigit():
            count_on_page = int(cnt_input["value"])

        return {
            "page_no": page_no,
            "size": size,
            "total_pages": total_pages,
            "count_on_page": count_on_page,
            "tenders": tenders
        }

    def search_tenders(
        self,
        page_no: Optional[int] = None,
        page_number: Optional[int] = None,
        page_size: Optional[int] = None,
        size: Optional[int] = None,
        max_pages: Optional[int] = None,
        procurement_nature: Optional[str] = None,
        proc_nature: str = "2",
        procurement_type: Optional[str] = None,
        proc_type: str = "",
        procurement_method: Optional[str] = None,
        proc_method: str = "0",
        tender_id: str = "",
        ref_no: str = "",
        reference_no: Optional[str] = None,
        publication_date_from: str = "",
        pub_dt_from: str = "",
        publication_date_to: str = "",
        pub_dt_to: str = "",
        closing_date_from: str = "",
        close_dt_from: str = "",
        closing_date_to: str = "",
        close_dt_to: str = "",
        cpv_category: str = "",
        is_frame: str = "0",
        view_type: str = "Live",
        keyword: str = ""
    ) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
        """
        টেন্ডার অনুসন্ধান ও নিরাপদ পেজিনেশন।
        - page_no বা page_number নির্দিষ্ট থাকলে এবং max_pages না থাকলে একক পৃষ্ঠার ডিকশনারি রিটার্ন করে।
        - max_pages নির্দিষ্ট থাকলে পৃষ্ঠাসমূহ নিরাপদে ক্রল করে ইউনিক টেন্ডার তালিকা রিটার্ন করে।
        """
        p_no = page_no or page_number
        p_size = page_size or size or 10
        p_nature = procurement_nature if procurement_nature is not None else proc_nature
        p_type = procurement_type if procurement_type is not None else proc_type
        p_method = procurement_method if procurement_method is not None else proc_method
        r_no = reference_no if reference_no is not None else ref_no
        p_from = publication_date_from or pub_dt_from
        p_to = publication_date_to or pub_dt_to
        c_from = closing_date_from or close_dt_from
        c_to = closing_date_to or close_dt_to

        # যদি একক কোনো পেজ চাওয়া হয় এবং max_pages নির্ধারিত না থাকে
        if p_no is not None and max_pages is None:
            return self.search_page(
                page_no=p_no,
                size=p_size,
                proc_nature=p_nature,
                proc_type=p_type,
                proc_method=p_method,
                tender_id=tender_id,
                ref_no=r_no,
                pub_dt_from=p_from,
                pub_dt_to=p_to,
                close_dt_from=c_from,
                close_dt_to=c_to,
                cpv_category=cpv_category,
                is_frame=is_frame,
                view_type=view_type,
                keyword=keyword
            )

        # অন্যথায় নিরাপদ পেজিনেশন লুপ (Multi-page safe pagination)
        limit_pages = max_pages if max_pages is not None else 999999
        all_unique_tenders: List[Dict[str, Any]] = []
        seen_ids: Set[str] = set()

        curr_page = 1
        while curr_page <= limit_pages:
            display_limit = str(limit_pages) if max_pages is not None else "all"
            logger.info(f"Scanning e-GP listing page {curr_page}/{display_limit} (size={p_size})...")
            page_tenders = self._search_page_raw(
                page=curr_page,
                page_size=p_size,
                proc_nature=p_nature,
                proc_type=p_type,
                proc_method=p_method,
                tender_id=tender_id,
                ref_no=r_no,
                pub_dt_from=p_from,
                pub_dt_to=p_to,
                close_dt_from=c_from,
                close_dt_to=c_to,
                cpv_category=cpv_category,
                is_frame=is_frame,
                view_type=view_type,
                keyword=keyword
            )

            if not page_tenders:
                logger.info(f"No tenders returned on page {curr_page}. Stopping pagination.")
                break

            new_count = 0
            for t in page_tenders:
                tid = t.get("tender_id")
                if tid and tid not in seen_ids:
                    seen_ids.add(tid)
                    all_unique_tenders.append(t)
                    new_count += 1

            logger.info(f"Page {curr_page}: found {len(page_tenders)} rows, {new_count} new unique tenders.")
            if new_count == 0:
                logger.info(f"No new unique tenders found on page {curr_page}. Stopping to avoid pagination loop.")
                break

            curr_page += 1

        return all_unique_tenders

    def get_tender_details(self, tender_id: str) -> Dict[str, Any]:
        """
        ViewTender.jsp থেকে নির্দিষ্ট টেন্ডারের বিস্তারিত নোটিশ আনা
        """
        tid = str(tender_id).strip()
        url = f"{EGP_VIEW_TENDER_URL}?id={tid}&h=t"
        headers = {
            "Referer": f"{self.base_url}/resources/common/AllTenders.jsp?h=t"
        }

        r = self._execute_request(method="GET", url=url, headers=headers)
        details = self.parse_tender_details_html(r.text, tender_id=tid)

        if not details.get("source_url"):
            details["source_url"] = url

        return details
