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
    # Check if there is a prefix like "key:" or "key="
    if ":" in content and not content.startswith("http"):
        parts = content.split(":", 1)
        if len(parts[0]) < 20:
            content = parts[1].strip()
    elif "=" in content:
        parts = content.split("=", 1)
        if len(parts[0]) < 20:
            content = parts[1].strip()
    return content.strip().strip("'").strip('"')


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
