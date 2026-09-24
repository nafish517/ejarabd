import os
import sys
import httpx
import json

# Windows কনসোলে UTF-8 এনকোডিং
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

def load_gemini_api_key() -> str:
    """Load Gemini API key exclusively from the GEMINI_API_KEY environment variable."""
    env_key = os.getenv("GEMINI_API_KEY")
    if env_key and len(env_key.strip()) > 10:
        return env_key.strip().strip("'").strip('"')
    raise ValueError("GEMINI_API_KEY environment variable is not set or invalid.")


def main():
    try:
        api_key = load_gemini_api_key()
        print(f"API key loaded successfully (length: {len(api_key)}, starts_with_AIza: {api_key.startswith('AIza')})")
    except Exception as e:
        print(f"Failed to load API key: {e}")
        return

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    print("Querying Google Gemini API models list...")
    with httpx.Client(timeout=15.0) as client:
        r = client.get(url)
        print(f"Status Code: {r.status_code}")
        if r.status_code != 200:
            print(f"Error response: {r.text}")
            return
        
        data = r.json()
        models = data.get("models", [])
        print(f"Total models returned: {len(models)}")
        print("\nAll Available Models:")
        flash_models = []
        gemini_3_models = []
        for m in models:
            name = m.get("name", "")
            methods = m.get("supportedGenerationMethods", [])
            display_name = m.get("displayName", "")
            if "generateContent" in methods:
                print(f"  • {name} ({display_name})")
                if "flash" in name.lower():
                    flash_models.append(name)
                if "3" in name or "3.8" in name or "3-8" in name:
                    gemini_3_models.append(name)
        
        print("\n--- Summary of Relevant Flash Models ---")
        for fm in flash_models:
            print(f"  Flash: {fm}")
            
        print("\n--- Any Gemini 3.x Models Found ---")
        for g3 in gemini_3_models:
            print(f"  Gemini 3: {g3}")

if __name__ == "__main__":
    main()
