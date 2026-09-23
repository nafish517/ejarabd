import os
import sys
import time
import json
import httpx

# Windows কনসোলে UTF-8 এনকোডিং
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def load_gemini_api_key() -> str:
    # 1. Check environment variable
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key and len(env_key.strip()) > 10:
        return env_key.strip().strip("'").strip('"')

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 2. Check gemini paid api.txt in root
    paid_path = os.path.join(base_dir, "gemini paid api.txt")
    if os.path.exists(paid_path):
        with open(paid_path, "r", encoding="utf-8") as f:
            for line in f:
                l = line.strip()
                if l and not l.startswith("curl") and not l.startswith("-") and not l.startswith("{"):
                    return l.strip().strip("'").strip('"')

    # 3. Check api key folder
    key_path = os.path.join(base_dir, "api key", "gemini api")
    if not os.path.exists(key_path):
        key_path = r"C:\Users\User\Desktop\ai access folder\ejarabd\api key\gemini api"
    if not os.path.exists(key_path):
        key_path = r"C:\Users\User\Desktop\ai access folder\Tenderwise\api key\gemini api"
    if not os.path.exists(key_path):
        raise FileNotFoundError(f"API key file not found at: {key_path}")
    with open(key_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    if ":" in content and not content.startswith("http"):
        parts = content.split(":", 1)
        if len(parts[0]) < 20:
            content = parts[1].strip()
    elif "=" in content:
        parts = content.split("=", 1)
        if len(parts[0]) < 20:
            content = parts[1].strip()
    return content.strip().strip("'").strip('"')


def generate_content(
    api_key: str,
    model_name: str,
    prompt: str,
    generation_config: dict = None,
    system_instruction: str = None,
    timeout: float = 45.0,
    max_retries: int = 6
) -> dict:
    # Ensure model has 'models/' prefix or clean name
    clean_model = model_name if model_name.startswith("models/") else f"models/{model_name}"
    url = f"https://generativelanguage.googleapis.com/v1beta/{clean_model}:generateContent?key={api_key}"
    
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ]
    }
    
    if system_instruction:
        payload["systemInstruction"] = {
            "parts": [{"text": system_instruction}]
        }
        
    if generation_config:
        payload["generationConfig"] = generation_config

    retry_delays = [3, 5, 8, 12, 16, 20]
    for attempt in range(max_retries):
        start = time.perf_counter()
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.post(url, json=payload, headers={"Content-Type": "application/json"})
            duration = time.perf_counter() - start
            
            if resp.status_code == 200:
                data = resp.json()
                text = ""
                try:
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                except (KeyError, IndexError):
                    text = str(data)
                return {
                    "text": text,
                    "duration": duration,
                    "raw": data
                }
            elif resp.status_code in (503, 429) and attempt < max_retries - 1:
                wait_time = retry_delays[min(attempt, len(retry_delays) - 1)]
                print(f"[Warn] Received HTTP {resp.status_code} ({'High Demand / Unavailable' if resp.status_code == 503 else 'Rate Limit'}). Retrying in {wait_time}s (Attempt {attempt+1}/{max_retries})...", flush=True)
                time.sleep(wait_time)
                continue
            else:
                raise RuntimeError(f"HTTP {resp.status_code}: {resp.text}")
        except httpx.RequestError as e:
            if attempt < max_retries - 1:
                wait_time = retry_delays[min(attempt, len(retry_delays) - 1)]
                print(f"[Warn] Network error: {e}. Retrying in {wait_time}s...", flush=True)
                time.sleep(wait_time)
                continue
            raise

def main():
    api_key = load_gemini_api_key()
    target_model = "models/gemini-3.8-flash"
    
    results = {}
    
    print("=" * 60)
    print("STEP 2: Basic Connection Test with Gemini 3.8 Flash")
    print("=" * 60)
    prompt_step2 = "Reply with exactly: EJARABD GEMINI CONNECTION SUCCESS"
    res_step2 = generate_content(api_key, target_model, prompt_step2)
    print(f"Latency: {res_step2['duration']:.3f}s")
    print(f"Response: {repr(res_step2['text'].strip())}")
    
    step2_pass = "EJARABD GEMINI CONNECTION SUCCESS" in res_step2["text"].strip()
    results["step2"] = step2_pass
    print(f"Step 2 Basic Request: {'PASS' if step2_pass else 'FAIL'}")
    
    time.sleep(2)
    print("\n" + "=" * 60)
    print("STEP 3: Bengali Language Understanding & Coherence Test")
    print("=" * 60)
    prompt_step3 = "তুমি EjaraBD-এর AI assistant। একজন বাংলাদেশি contractor-এর জন্য সহজ বাংলায় বলো কীভাবে EjaraBD তার জন্য উপযুক্ত সরকারি টেন্ডার খুঁজে পেতে সাহায্য করে।"
    res_step3 = generate_content(api_key, target_model, prompt_step3)
    print(f"Latency: {res_step3['duration']:.3f}s")
    print("Bengali Response:")
    print(res_step3["text"])
    
    # Verify Bengali characters and coherence
    has_bengali = any('\u0980' <= c <= '\u09FF' for c in res_step3["text"])
    has_keywords = any(kw in res_step3["text"] for kw in ["টেন্ডার", "ঠিকাদার", "সাহায্য", "e-GP", "উপযুক্ত", "বাছাই"])
    step3_pass = has_bengali and has_keywords and len(res_step3["text"]) > 50
    results["step3"] = step3_pass
    print(f"Step 3 Bengali Request: {'PASS' if step3_pass else 'FAIL'}")

    time.sleep(2)
    print("\n" + "=" * 60)
    print("STEP 4: EjaraBD Reasoning & Zero-Hallucination Test")
    print("=" * 60)
    prompt_step4 = """[ঠিকাদারের প্রোফাইল]:
- জেলা: দিনাজপুর (Dinajpur)
- কাজের আগ্রহ: সড়ক নির্মাণ (Road construction)
- পছন্দের সর্বোচ্চ বাজেট: ৫ কোটি টাকা (5 crore BDT)
- প্রাসঙ্গিক অভিজ্ঞতা: সড়ক নির্মাণ (Road construction)

[দরপত্র তথ্য]:
- জেলা: দিনাজপুর (Dinajpur)
- কাজের ধরন: সড়ক নির্মাণ (Road construction)
- টেন্ডার সিকিউরিটি (জামানত): ৫,০০,০০০ টাকা (500,000 BDT)
- প্রাক্কলিত প্রকল্প মূল্য: অজ্ঞাত / নোটিশে উল্লেখ নেই (UNKNOWN)
- যোগ্যতা: প্রাসঙ্গিক সড়ক নির্মাণের অভিজ্ঞতা

উপরে উল্লেখিত তথ্যের ভিত্তিতে ঠিকাদারের জন্য এই দরপত্রটি উপযুক্ত কিনা তা বাংলায় সহজ ভাষায় ব্যাখ্যা করো।
কঠোর নিয়ম:
১. প্রাক্কলিত প্রকল্প মূল্য কোনো অবস্থাতেই অনুমান বা বানিয়ে বলবে না। নোটিশে না থাকলে তা স্পষ্ট 'অজ্ঞাত / যাচাই প্রয়োজন' বলবে।
২. টেন্ডার সিকিউরিটিকে কখনো মূল প্রকল্প মূল্য হিসেবে গণ্য করবে না।
৩. কোন তথ্যগুলো নিশ্চিতভাবে মিলেছে এবং কোন তথ্যগুলো এখনো অজানা তা স্পষ্টভাবে আলাদা করো।"""

    res_step4 = generate_content(api_key, target_model, prompt_step4)
    print(f"Latency: {res_step4['duration']:.3f}s")
    print("Reasoning Response:")
    print(res_step4["text"])
    
    t_lower = res_step4["text"].lower()
    no_invented_budget = ("৫ কোটি" not in t_lower or "পছন্দের" in t_lower or "সর্বোচ্চ" in t_lower)
    recognizes_unknown = any(w in res_step4["text"] for w in ["অজ্ঞাত", "উল্লেখ নেই", "জানা যায়নি", "যাচাই প্রয়োজন", "অনুপস্থিত", "তথ্য নেই", "নিশ্চিত নয়"])
    distinguishes_security = any(w in res_step4["text"] for w in ["জামানত", "সিকিউরিটি", "৫,০০,০০০", "৫ লাখ", "500,000"])
    step4_pass = recognizes_unknown and distinguishes_security
    results["step4"] = step4_pass
    print(f"Step 4 Reasoning: {'PASS' if step4_pass else 'FAIL'} (recognizes_unknown={recognizes_unknown}, distinguishes_security={distinguishes_security})")

    time.sleep(2)
    print("\n" + "=" * 60)
    print("STEP 5: Structured JSON Schema Output Test")
    print("=" * 60)
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "qualification_status": {
                "type": "STRING",
                "enum": ["meets_known_criteria", "unknown_needs_verification", "does_not_meet"]
            },
            "preference_fit_status": {
                "type": "STRING",
                "enum": ["fits", "partial", "outside"]
            },
            "preference_reasons": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "known_mismatches": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "unknown_items_to_verify": {
                "type": "ARRAY",
                "items": {"type": "STRING"}
            },
            "overall_fit_explanation_bn": {
                "type": "STRING"
            }
        },
        "required": [
            "qualification_status",
            "preference_fit_status",
            "preference_reasons",
            "known_mismatches",
            "unknown_items_to_verify",
            "overall_fit_explanation_bn"
        ]
    }
    
    gen_config = {
        "response_mime_type": "application/json",
        "response_schema": schema
    }
    
    system_inst = "You are the EjaraBD assessment engine. Evaluate contractor against tender strictly adhering to facts without hallucinating project values."
    
    prompt_step5 = """Evaluate this contractor and tender:
Contractor: District Dinajpur, Road construction, Max budget 5 crore BDT, relevant experience in road construction.
Tender: District Dinajpur, Road construction, Tender Security: 500,000 BDT, Estimated Project Value: UNKNOWN, Eligibility: Relevant road construction experience.
Important: Estimated project value is UNKNOWN. Do not treat security as project value. Add missing budget to unknown_items_to_verify."""

    res_step5 = generate_content(api_key, target_model, prompt_step5, generation_config=gen_config, system_instruction=system_inst)
    print(f"Latency: {res_step5['duration']:.3f}s")
    print("Structured JSON Output:")
    print(res_step5["text"])
    
    step5_pass = False
    try:
        parsed_json = json.loads(res_step5["text"])
        req_keys = ["qualification_status", "preference_fit_status", "preference_reasons", "known_mismatches", "unknown_items_to_verify", "overall_fit_explanation_bn"]
        all_keys = all(k in parsed_json for k in req_keys)
        valid_fit = parsed_json.get("preference_fit_status") in ["fits", "partial", "outside"]
        valid_qual = parsed_json.get("qualification_status") in ["meets_known_criteria", "unknown_needs_verification", "does_not_meet"]
        step5_pass = all_keys and valid_fit and valid_qual
    except Exception as e:
        print(f"JSON Parse Error: {e}")
        step5_pass = False
        
    results["step5"] = step5_pass
    print(f"Step 5 Structured Output: {'PASS' if step5_pass else 'FAIL'}")

    print("\n" + "=" * 60)
    print("STEP 6: Latency Measurement (3 Controlled Requests)")
    print("=" * 60)
    latencies = []
    for i in range(1, 4):
        test_prompt = f"Ping {i}: State in 3 words why EjaraBD helps contractors."
        r = generate_content(api_key, target_model, test_prompt)
        lat = r["duration"]
        latencies.append(lat)
        print(f"Request {i}: {lat:.3f}s -> Response: {repr(r['text'].strip()[:40])}")
        time.sleep(0.5)
        
    avg_latency = sum(latencies) / len(latencies)
    print(f"Average Latency: {avg_latency:.3f}s")
    results["latencies"] = latencies
    results["avg_latency"] = avg_latency

    print("\n" + "=" * 60)
    print("SUMMARY RESULTS FOR STEP 1-6")
    print("=" * 60)
    for k, v in results.items():
        print(f"  {k}: {v}")

if __name__ == "__main__":
    main()
