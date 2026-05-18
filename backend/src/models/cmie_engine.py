import os
import json
import time
import io
from PIL import Image
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class CMIEEngine:
    def __init__(self):
        print("🧠 [CMIE Engine] 正在初始化真实的云端 MLLM (Gemini Pro) 客户端...")
        
        # 从环境变量中读取 API Key。请确保在运行前设置了 export GEMINI_API_KEY="你的key"
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            print("⚠️ [警告] 未找到 GEMINI_API_KEY 环境变量！请务必配置，否则 Pro 引擎将调用失败。")
        
        genai.configure(api_key=self.api_key)
        
        # 使用最新的多模态 Pro 模型
        self.model = genai.GenerativeModel('gemini-2.5-flash')

    def detect(self, text: str, image_path: str, video_path: str) -> dict:
        """
        通过 API 调用 MLLM，执行 CMIE 逻辑，内置抗 429 并发重试装甲。
        """
        print(f"🕵️‍♂️ [CMIE Engine] 正在向云端 MLLM 发送跨模态数据进行深度语义推理...")
        
        prompt = """
        你是一个资深的“多模态假新闻”和“脱离语境(Out-of-Context)”检测专家。
        请仔细观察我提供的图片/视频和文本描述，执行以下分析步骤：
        
        1. [实体提取]：分别从视觉画面和文本中提取关键实体。
        2. [共存关系分析 (CRG)]：深度推理这些视觉实体与文本实体是否能在客观现实中合乎逻辑地共存。寻找张冠李戴、时间错位或地理矛盾的痕迹。
        3. [最终定性]：判定这是否是虚假信息或脱离语境的误导信息。
        
        请必须严格以纯 JSON 格式返回结果，不要包含 Markdown 代码块标记（如 ```json ）。
        JSON 格式结构如下：
        {
            "is_fake": true 或 false,
            "confidence": 0到100之间的浮点数 (表示置信度),
            "reasoning": "详细的中文分析过程，使用 \\n 进行换行"
        }
        """
        
        inputs = [prompt]
        if text:
            inputs.append(f"待测新闻文本内容：{text}")
            
        uploaded_video_file = None
            
        try:
            if image_path and os.path.exists(image_path):
                img = Image.open(image_path)
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img_byte_arr = io.BytesIO()
                img.save(img_byte_arr, format='JPEG')
                inputs.append({
                    "mime_type": "image/jpeg",
                    "data": img_byte_arr.getvalue()
                })
                
            elif video_path and os.path.exists(video_path):
                print("⏳ [CMIE Engine] 正在将视频流上传至云端...")
                uploaded_video_file = genai.upload_file(path=video_path)
                while uploaded_video_file.state.name == 'PROCESSING':
                    time.sleep(1)
                    uploaded_video_file = genai.get_file(uploaded_video_file.name)
                inputs.append(uploaded_video_file)

            # ==========================================================
            # 🔥 核心升级：指数退避重试机制 (抗 429 报错)
            # ==========================================================
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = self.model.generate_content(inputs)
                    break # 如果成功，跳出重试循环
                except Exception as api_err:
                    err_msg = str(api_err)
                    if "429" in err_msg or "Quota" in err_msg:
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt # 等待 1秒, 2秒, 4秒...
                            print(f"⚠️ [CMIE Engine] 触发云端 API 并发限制 (429)，等待 {wait_time} 秒后进行第 {attempt + 2} 次重试...")
                            time.sleep(wait_time)
                            continue
                    # 如果不是 429 错误，或者重试次数用尽，向上抛出异常
                    raise api_err
            # ==========================================================
            
            result_text = response.text.strip()
            if result_text.startswith("```json"):
                result_text = result_text[7:-3].strip()
            elif result_text.startswith("```"):
                result_text = result_text[3:-3].strip()
                
            result_data = json.loads(result_text)
            print("✅ [CMIE Engine] 云端推理完成！")
            
            return {
                "is_fake": bool(result_data.get("is_fake", False)),
                "confidence": float(result_data.get("confidence", 0.0)),
                "reasoning": str(result_data.get("reasoning", "未返回有效推理报告。"))
            }
            
        except Exception as e:
            print(f"❌ [CMIE Engine] API 调用最终失败: {e}")
            return {
                "is_fake": False,
                "confidence": 0.0,
                "reasoning": f"【SYSTEM ALERT】CMIE 云端引擎连接中断或解析异常。\n错误详情: {str(e)}\n请检查 API Key 额度配置或网络状态。"
            }
        finally:
            if uploaded_video_file:
                try:
                    genai.delete_file(uploaded_video_file.name)
                except:
                    pass