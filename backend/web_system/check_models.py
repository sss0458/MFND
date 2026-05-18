import os
import google.generativeai as genai
from dotenv import load_dotenv

# 加载 .env 中的 API KEY
load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

if not api_key:
    print("❌ 找不到 API KEY，请检查 .env 文件。")
else:
    genai.configure(api_key=api_key)
    print("✅ API Key 加载成功！你当前可用的支持大文本/多模态生成的模型有：\n")
    
    # 遍历并打印所有支持生成内容的模型
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"👉 {m.name}")