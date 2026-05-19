import os
import google.generativeai as genai
import requests
from dotenv import load_dotenv

load_dotenv()

provider = (
    os.environ.get("PRO_API_PROVIDER")
    or ("openai_compatible" if os.environ.get("PRO_API_BASE_URL") else "gemini")
).strip().lower()

if provider == "gemini":
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("PRO_API_KEY")
    if not api_key:
        print("❌ 找不到 GEMINI_API_KEY 或 PRO_API_KEY，请检查环境变量。")
    else:
        genai.configure(api_key=api_key)
        print("✅ Gemini API Key 加载成功！可用的生成模型有：\n")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"👉 {m.name}")
else:
    api_key = os.environ.get("PRO_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = (os.environ.get("PRO_API_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "").rstrip("/")
    if not api_key or not base_url:
        print("❌ 找不到 PRO_API_KEY 或 PRO_API_BASE_URL，请检查环境变量。")
    else:
        models_base_url = base_url.rsplit("/chat/completions", 1)[0]
        models_url = f"{models_base_url}/models" if models_base_url.endswith("/v1") else f"{models_base_url}/v1/models"
        response = requests.get(
            models_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        response.raise_for_status()
        print("✅ OpenAI 兼容 API Key 加载成功！接口返回的模型有：\n")
        for item in response.json().get("data", []):
            print(f"👉 {item.get('id')}")
