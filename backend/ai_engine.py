import sys
import json
import logging
from typing import Dict, Any, List, Optional
import httpx

# Windows কনসোলে UTF-8 এনকোডিং
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from backend.models import ContractorProfile, Tender
from backend.matching import evaluate_tender_for_contractor as rule_based_evaluate
from backend.matching import generate_whatsapp_message as rule_based_draft_message

logger = logging.getLogger("ejarabd.ai")

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "qwen2.5:3b" # Default lightweight model; fallback/compatible with qwen2.5:7b or gemma2:2b

class LocalAIEngine:
    def __init__(self, base_url: str = OLLAMA_BASE_URL, default_model: str = DEFAULT_MODEL):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model

    async def get_status(self) -> Dict[str, Any]:
        """লোকাল এআই সার্ভার (Ollama) এবং মডেলের উপস্থিতি পরীক্ষা"""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    active_model = self.default_model if self.default_model in models else (models[0] if models else None)
                    return {
                        "is_available": True,
                        "server": "Ollama (Local)",
                        "installed_models": models,
                        "active_model": active_model or self.default_model,
                        "gpu_accelerated": True
                    }
        except Exception as e:
            logger.debug(f"Ollama not reachable: {e}")
        
        return {
            "is_available": False,
            "server": "Offline (Fallback Rule Engine Active)",
            "installed_models": [],
            "active_model": None,
            "gpu_accelerated": False
        }

    async def evaluate_eligibility_ai(
        self,
        contractor: ContractorProfile,
        tender: Tender,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        লোকাল LLM (Qwen/Gemma) ব্যবহার করে টেন্ডারের জটিল শর্তাবলি বিশ্লেষণ ও মিল যাচাই
        """
        model = model_name or self.default_model
        system_prompt = """তুমি 'EjaraBD' (ইজারাবিডি)-এর বিশেষজ্ঞ দরপত্র বিশ্লেষক এআই।
তোমার দায়িত্ব হলো অভিজ্ঞ বাংলাদেশি ঠিকাদারের প্রোফাইলের সাথে সরকারি e-GP টেন্ডার নোটিশের জটিল শর্তাবলি যাচাই করে স্বচ্ছ মূল্যায়ন তৈরি করা।

কঠোর নিয়মাবলী:
১. কোনো কাল্পনিক তথ্য বা অনুমান তৈরি করবে না। শুধুমাত্র সরবরাহকৃত তথ্যের ভিত্তিতে বিশ্লেষণ করবে।
২. টেন্ডারে প্রাক্কলিত মূল্য (আনুমানিক বাজেট) না থাকলে তা অবশ্যই 'অজ্ঞাত / নোটিশে উল্লেখ নেই (যাচাই প্রয়োজন)' হিসেবে চিহ্নিত রাখবে। কোনো অবস্থাতেই নিজের থেকে কোনো প্রাক্কলিত মূল্য অনুমান করবে না।
৩. টেন্ডার সিকিউরিটি (জামানত)-কে কখনো মূল প্রজেক্ট ভ্যালু হিসেবে গণ্য করবে না। সিকিউরিটি ও প্রজেক্ট ভ্যালু সম্পূর্ণ আলাদা।
৪. কোনো মনগড়া যোগ্যতা বা সনদ অনুমান করবে না। নোটিশে কোনো শর্ত না থাকলে তা 'unknown_items_to_verify'-এ রাখবে।
৫. কোনো কৃত্রিম শতকরা (যেমন ৯১% বা ৮৭%) ম্যাচ স্কোর দেবে না।
৬. 'preference_fit_status' অবশ্যই 'fits', 'partial', অথবা 'outside' এর মধ্যে একটি হবে।
৭. 'qualification_status' অবশ্যই 'meets_known_criteria', 'does_not_meet', অথবা 'unknown_needs_verification' এর মধ্যে একটি হবে।
৮. আউটপুট অবশ্যই নিচের স্ট্রাকচার অনুযায়ী কেবলমাত্র বৈধ JSON (Valid JSON) হতে হবে:
{
  "preference_fit_status": "fits" | "partial" | "outside",
  "preference_reasons": ["কাজের এলাকার মিলের কারণ", "ক্যাটাগরির সামঞ্জস্য"],
  "qualification_status": "meets_known_criteria" | "does_not_meet" | "unknown_needs_verification",
  "known_mismatches": ["কোনো গরমিল থাকলে তার তালিকা"],
  "unknown_items_to_verify": ["যে যে শর্তাবলী এখনো যাচাই করা প্রয়োজন, যেমন লিকুইড অ্যাসেট বা অভিজ্ঞতার সনদ"],
  "overall_fit_explanation_bn": "ঠিকাদারের জন্য বাংলায় সহজ, স্পষ্ট ও আন্তরিক সার্বিক সারসংক্ষেপ"
}"""

        budget_str = f"৳ {tender.estimated_value_bdt:,.0f} টাকা" if tender.estimated_value_bdt is not None else "অজ্ঞাত / নোটিশে উল্লেখ নেই (যাচাই প্রয়োজন)"
        security_str = f"৳ {tender.tender_security_bdt:,.0f} টাকা" if tender.tender_security_bdt is not None else "অজ্ঞাত / নোটিশে উল্লেখ নেই"

        user_content = f"""[ঠিকাদারের প্রোফাইল]:
- প্রতিষ্ঠান: {contractor.business_name}
- ঠিকাদার: {contractor.contact_person}
- পছন্দের জেলা: {', '.join(contractor.preferred_districts or ['Dinajpur'])}
- কাজের ধরন: {', '.join(contractor.work_categories or ['Civil Works'])}
- পছন্দের সংস্থা: {', '.join(contractor.preferred_agencies or ['LGED', 'RHD'])}
- ধারণক্ষমতা: {contractor.min_project_value_bdt or 'তথ্য নেই'} হতে {contractor.max_project_value_bdt or 'তথ্য নেই'} টাকা
- বাস্তব অভিজ্ঞতা: {contractor.experience_notes or 'তথ্য নেই'}
- সীমাবদ্ধতা: {contractor.known_constraints or 'তথ্য নেই'}

[দরপত্র তথ্য]:
- আইডি: {tender.tender_id}
- শিরোনাম: {tender.title}
- সংস্থা: {tender.agency}
- আহবানকারী অফিস: {tender.procuring_entity_office}
- কাজের জেলা: {tender.project_location_district} ({tender.project_location_details or ''})
- কাজের ধরন: {tender.category}
- প্রাক্কলিত বাজেট (Project Value): {budget_str}
- জামানত (Tender Security): {security_str} (সতর্কতা: এটি জামানত, প্রজেক্ট ভ্যালু নয়)
- নোটিশের মূল শর্তাবলি: {tender.raw_eligibility_text or 'নোটিশে বিস্তারিত যোগ্যতা উল্লেখ নেই; শিডিউলের ITT বা TDS অংশ দেখে শর্ত নিশ্চিত হতে হবে।'}
- সংশোধনী: {'হ্যাঁ: ' + (tender.amendment_details or '') if tender.is_amendment else 'না'}

উপরের তথ্যের ভিত্তিতে JSON আউটপুট প্রদান করো:"""

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "system": system_prompt,
                        "prompt": user_content,
                        "format": "json",
                        "stream": False,
                        "options": {
                            "temperature": 0.2, # ফোকাসড ও বাস্তবসম্মত আউটপুটের জন্য কম টেম্পারেচার
                            "num_predict": 1024
                        }
                    }
                )
                if res.status_code == 200:
                    response_data = res.json()
                    response_text = response_data.get("response", "").strip()
                    parsed = json.loads(response_text)

                    # Normalization and Validation
                    pref_status = parsed.get("preference_fit_status", "fits")
                    if pref_status not in ["fits", "partial", "outside"]:
                        pref_status = "partial" if "আংশিক" in str(pref_status) else ("outside" if "বাইরে" in str(pref_status) or "না" in str(pref_status) else "fits")

                    qual_status = parsed.get("qualification_status", "unknown_needs_verification")
                    if qual_status not in ["meets_known_criteria", "does_not_meet", "unknown_needs_verification"]:
                        qual_status = "does_not_meet" if "না" in str(qual_status) else ("meets_known_criteria" if "মেলে" in str(qual_status) else "unknown_needs_verification")

                    pref_reasons = parsed.get("preference_reasons")
                    if not isinstance(pref_reasons, list):
                        pref_reasons = [str(pref_reasons)] if pref_reasons else []

                    known_mismatches = parsed.get("known_mismatches")
                    if not isinstance(known_mismatches, list):
                        known_mismatches = [str(known_mismatches)] if known_mismatches else []

                    unknown_items = parsed.get("unknown_items_to_verify")
                    if not isinstance(unknown_items, list):
                        unknown_items = [str(unknown_items)] if unknown_items else []

                    # Hard rule check: If tender.estimated_value_bdt is None, ensure unknown_items notes it
                    if tender.estimated_value_bdt is None:
                        budget_note = "নোটিশে প্রাক্কলিত কাজের মূল্য উল্লেখ নেই; টেন্ডার শিডিউল কিনে সঠিক প্রাক্কলন নিশ্চিত করতে হবে।"
                        if not any("প্রাক্কলিত" in u or "মূল্য" in u or "বাজেট" in u for u in unknown_items):
                            unknown_items.append(budget_note)

                    explanation = parsed.get("overall_fit_explanation_bn")
                    if not explanation or not isinstance(explanation, str) or len(explanation.strip()) < 10:
                        explanation = "এআই দ্বারা মূল্যায়িত: শর্ত ও তথ্যের ঘাটতি যাচাই করে সিদ্ধান্ত নিন।"

                    return {
                        "preference_fit_status": pref_status,
                        "preference_reasons": pref_reasons,
                        "qualification_status": qual_status,
                        "known_mismatches": known_mismatches,
                        "unknown_items_to_verify": unknown_items,
                        "overall_fit_explanation_bn": explanation.strip(),
                        "ai_generated": True,
                        "model_used": model
                    }
        except Exception as e:
            logger.warning(f"AI evaluation failed or Ollama not running ({e}). Falling back to rule-based engine.")

        # ফলব্যাক: আমাদের বিদ্যমান স্বচ্ছ রুল-বেসড মূল্যায়ন
        fallback_res = rule_based_evaluate(contractor, tender)
        fallback_res["ai_generated"] = False
        fallback_res["model_used"] = None
        return fallback_res

    async def polish_whatsapp_draft_ai(
        self,
        contractor: ContractorProfile,
        tender: Tender,
        assessment_data: Dict[str, Any],
        model_name: Optional[str] = None
    ) -> str:
        """
        লোকাল LLM ব্যবহার করে সম্পূর্ণ মানুষের মতো সাবলীল, শ্রদ্ধাশীল ও গোছানো বাংলা হোয়াটসঅ্যাপ ড্রাফট তৈরি
        """
        model = model_name or self.default_model
        system_prompt = """তুমি 'EjaraBD' (ইজারাবিডি)-এর জন্য সিনিয়র বাংলাদেশি ঠিকাদারদের উপযুক্ত হোয়াটসঅ্যাপ বার্তা লেখক।
তোমার তৈরি বার্তাটি হতে হবে অত্যন্ত শ্রদ্ধাশীল, প্রাঞ্জল এবং তথ্যবহুল বাংলায়।

নিয়মাবলী:
১. শুরু করবে আন্তরিক সম্ভাষণ দিয়ে (যেমন: 'আসসালামু আলাইকুম ঠিকাদার সাহেব/চাচা')।
২. নোটিশে প্রাক্কলিত মূল্য না থাকলে কখনো নিজের থেকে অনুমান করবে না, স্পষ্টভাবে বলবে 'অফিসিয়াল নোটিশে প্রাক্কলিত মূল্য উল্লেখ নেই (দলিল দেখতে হবে)'।
৩. টেন্ডার সিকিউরিটি এবং প্রজেক্টের বাজেটকে সম্পূর্ণ আলাদা রাখবে।
৪. তারিখ ও সময় অবশ্যই বাংলাদেশ সময় (BST) ফরম্যাটে স্পষ্ট করবে।
৫. অফিসিয়াল সরকারি দরপত্র লিংক হুবহু অন্তর্ভুক্ত করবে।
৬. কেন তার কাজের সাথে মেলে এবং জমা দেওয়ার আগে কি কি কাগজপত্র যাচাই করতে হবে তা পয়েন্ট আকারে লিখবে।"""

        user_content = f"""[প্রাপক]: {contractor.contact_person} ({contractor.business_name})
[কাজের এলাকা]: {tender.project_location_district}
[দরপত্রের তথ্য]:
- আইডি: {tender.tender_id}
- কাজ: {tender.title}
- সংস্থা: {tender.agency}
- বাজেট: {tender.estimated_value_bdt if tender.estimated_value_bdt else 'নোটিশে উল্লেখ নেই'}
- সিকিউরিটি: {tender.tender_security_bdt if tender.tender_security_bdt else 'নোটিশে উল্লেখ নেই'}
- শেষ তারিখ: {tender.closing_date}
- অফিসিয়াল লিংক: {tender.source_url}
- সংশোধনী: {tender.amendment_details if tender.is_amendment else 'নেই'}

[মূল্যায়ন ফলাফল]:
- মিলের দিক: {', '.join(assessment_data.get('preference_reasons', []))}
- যাচাইয়ের দিক: {', '.join(assessment_data.get('unknown_items_to_verify', []))}

হোয়াটসঅ্যাপে পাঠানোর জন্য একটি পূর্ণাঙ্গ, গোছানো বাংলা বার্তা তৈরি করো:"""

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                res = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": model,
                        "system": system_prompt,
                        "prompt": user_content,
                        "stream": False,
                        "options": {
                            "temperature": 0.3,
                            "num_predict": 1024
                        }
                    }
                )
                if res.status_code == 200:
                    response_data = res.json()
                    draft_text = response_data.get("response", "").strip()
                    if draft_text and len(draft_text) > 80:
                        return {
                            "draft_message_bn": draft_text,
                            "ai_generated": True,
                            "model_used": model
                        }
        except Exception as e:
            logger.warning(f"AI draft polish failed ({e}). Falling back to template-based draft.")

        # ফলব্যাক: আমাদের স্ট্যান্ডার্ড বাংলায় তৈরি মেসেজ
        fallback_msg = rule_based_draft_message(contractor, tender, assessment_data)
        return {
            "draft_message_bn": fallback_msg,
            "ai_generated": False,
            "model_used": None
        }

ai_engine = LocalAIEngine()
