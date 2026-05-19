import os
import json
import time
import io
import base64
from PIL import Image
import cv2
import requests
from dotenv import load_dotenv

load_dotenv()

class CMIEEngine:
    def __init__(self):
        configured_provider = (
            os.environ.get("PRO_API_PROVIDER")
            or os.environ.get("CMIE_PROVIDER")
            or ""
        ).strip().lower()
        has_openai_compatible_config = bool(
            os.environ.get("PRO_API_KEY") and os.environ.get("PRO_API_BASE_URL")
        )
        self.provider = configured_provider or (
            "openai_compatible" if has_openai_compatible_config else "gemini"
        )
        self.model_name = (
            os.environ.get("PRO_MODEL_NAME")
            or os.environ.get("CMIE_MODEL_NAME")
            or ("gemini-2.5-flash" if self.provider == "gemini" else "")
        ).strip()
        self.timeout = int(os.environ.get("PRO_API_TIMEOUT", "90"))
        self.max_retries = max(int(os.environ.get("PRO_API_MAX_RETRIES", "3")), 1)
        self.temperature = float(os.environ.get("PRO_API_TEMPERATURE", "0.1"))
        self.max_tokens = int(os.environ.get("PRO_API_MAX_TOKENS", "1200"))
        self.video_max_frames = max(int(os.environ.get("PRO_VIDEO_MAX_FRAMES", "4")), 0)
        self.model = None
        self.genai = None

        if self.provider == "gemini":
            self.api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("PRO_API_KEY")
            self.available = bool(self.api_key)
            print("🧠 [CMIE Engine] 正在初始化云端 MLLM 客户端 | provider=gemini")
            if not self.api_key:
                print("⚠️ [警告] 未找到 GEMINI_API_KEY 或 PRO_API_KEY，Pro 引擎将不可用。")
                return

            self.genai = self._load_gemini_client()
            self.genai.configure(api_key=self.api_key)
            self.model = self.genai.GenerativeModel(self.model_name)
            return

        if self.provider in {"openai", "openai_compatible", "openai-compatible", "compatible"}:
            self.provider = "openai_compatible"
            self.api_key = os.environ.get("PRO_API_KEY") or os.environ.get("OPENAI_API_KEY")
            self.base_url = (
                os.environ.get("PRO_API_BASE_URL")
                or os.environ.get("OPENAI_BASE_URL")
                or ""
            ).strip().rstrip("/")
            self.available = bool(self.api_key and self.base_url and self.model_name)
            print(
                "🧠 [CMIE Engine] 正在初始化云端 MLLM 客户端"
                f" | provider=openai_compatible | model={self.model_name or '未配置'}"
            )
            if not self.available:
                print(
                    "⚠️ [警告] OpenAI 兼容 Pro 引擎配置不完整，"
                    "请配置 PRO_API_KEY、PRO_API_BASE_URL、PRO_MODEL_NAME。"
                )
            return

        self.available = False
        print(f"⚠️ [警告] 未支持的 PRO_API_PROVIDER: {self.provider}，Pro 引擎将不可用。")

    def _load_gemini_client(self):
        import google.generativeai as genai
        return genai

    def _build_prompt(self, text: str) -> str:
        prompt = """
        你是一个资深的“多模态假新闻”和“脱离语境(Out-of-Context)”检测专家。
        请仔细观察我提供的图片/视频关键帧和文本描述，执行以下分析步骤：

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
        if text:
            prompt += f"\n待测新闻文本内容：{text}"
        return prompt

    def _parse_result_json(self, raw_text: str) -> dict:
        result_text = (raw_text or "").strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:-3].strip()
        elif result_text.startswith("```"):
            result_text = result_text[3:-3].strip()

        try:
            return json.loads(result_text)
        except json.JSONDecodeError:
            start = result_text.find("{")
            end = result_text.rfind("}")
            if start >= 0 and end > start:
                return json.loads(result_text[start:end + 1])
            raise

    def _normalize_result(self, result_data: dict) -> dict:
        raw_is_fake = result_data.get("is_fake", False)
        if isinstance(raw_is_fake, str):
            is_fake = raw_is_fake.strip().lower() in {"true", "1", "yes", "fake", "虚假"}
        else:
            is_fake = bool(raw_is_fake)

        return {
            "is_fake": is_fake,
            "confidence": float(result_data.get("confidence", 0.0)),
            "reasoning": str(result_data.get("reasoning", "未返回有效推理报告。"))
        }

    def _image_path_to_data_uri(self, image_path: str) -> str:
        img = Image.open(image_path)
        if img.mode != "RGB":
            img = img.convert("RGB")
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format="JPEG", quality=88)
        encoded = base64.b64encode(img_byte_arr.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{encoded}"

    def _extract_video_frame_data_uris(self, video_path: str) -> list:
        if not video_path or not os.path.exists(video_path) or self.video_max_frames <= 0:
            return []

        cap = cv2.VideoCapture(video_path)
        try:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            if total_frames <= 0:
                return []

            if self.video_max_frames == 1:
                frame_indices = [total_frames // 2]
            else:
                frame_indices = [
                    int((total_frames - 1) * idx / (self.video_max_frames - 1))
                    for idx in range(self.video_max_frames)
                ]

            frame_data_uris = []
            for frame_index in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
                ok, frame = cap.read()
                if not ok:
                    continue
                ok, encoded = cv2.imencode(
                    ".jpg",
                    frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 85],
                )
                if not ok:
                    continue
                data = base64.b64encode(encoded.tobytes()).decode("utf-8")
                frame_data_uris.append(f"data:image/jpeg;base64,{data}")
            return frame_data_uris
        finally:
            cap.release()

    def _chat_completions_url(self) -> str:
        if self.base_url.endswith("/chat/completions"):
            return self.base_url
        if self.base_url.endswith("/v1"):
            return f"{self.base_url}/chat/completions"
        return f"{self.base_url}/v1/chat/completions"

    def _request_openai_compatible(self, payload: dict) -> dict:
        retry_status_codes = {429, 500, 502, 503, 504}
        last_error = None
        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self._chat_completions_url(),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json=payload,
                    timeout=self.timeout,
                )
                if response.status_code in retry_status_codes and attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(
                        "⚠️ [CMIE Engine] OpenAI 兼容接口暂不可用"
                        f"({response.status_code})，等待 {wait_time} 秒后重试..."
                    )
                    time.sleep(wait_time)
                    continue
                response.raise_for_status()
                return response.json()
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"⚠️ [CMIE Engine] OpenAI 兼容接口调用失败，等待 {wait_time} 秒后重试: {exc}")
                    time.sleep(wait_time)
                    continue
                raise
        raise last_error

    def _detect_openai_compatible(self, text: str, image_path: str, video_path: str) -> dict:
        content = [{"type": "text", "text": self._build_prompt(text)}]

        if image_path and os.path.exists(image_path):
            content.append({
                "type": "image_url",
                "image_url": {"url": self._image_path_to_data_uri(image_path)},
            })

        for frame_idx, data_uri in enumerate(self._extract_video_frame_data_uris(video_path), start=1):
            content.append({"type": "text", "text": f"视频关键帧 {frame_idx}："})
            content.append({
                "type": "image_url",
                "image_url": {"url": data_uri},
            })

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": content}],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        data = self._request_openai_compatible(payload)
        message_content = data["choices"][0]["message"]["content"]
        if isinstance(message_content, list):
            result_text = "".join(
                item.get("text", "") if isinstance(item, dict) else str(item)
                for item in message_content
            )
        else:
            result_text = str(message_content)
        return self._normalize_result(self._parse_result_json(result_text))

    def _detect_gemini(self, text: str, image_path: str, video_path: str) -> dict:
        inputs = [self._build_prompt(text)]
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
                uploaded_video_file = self.genai.upload_file(path=video_path)
                while uploaded_video_file.state.name == 'PROCESSING':
                    time.sleep(1)
                    uploaded_video_file = self.genai.get_file(uploaded_video_file.name)
                inputs.append(uploaded_video_file)

            response = None
            for attempt in range(self.max_retries):
                try:
                    response = self.model.generate_content(inputs)
                    break
                except Exception as api_err:
                    err_msg = str(api_err)
                    if ("429" in err_msg or "Quota" in err_msg) and attempt < self.max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"⚠️ [CMIE Engine] 触发云端 API 并发限制 (429)，等待 {wait_time} 秒后进行第 {attempt + 2} 次重试...")
                        time.sleep(wait_time)
                        continue
                    raise api_err

            result_data = self._parse_result_json(response.text)
            return self._normalize_result(result_data)
        finally:
            if uploaded_video_file:
                try:
                    self.genai.delete_file(uploaded_video_file.name)
                except:
                    pass

    def detect(self, text: str, image_path: str, video_path: str) -> dict:
        """
        通过 API 调用 MLLM，执行 CMIE 逻辑，内置抗 429 并发重试装甲。
        """
        print(f"🕵️‍♂️ [CMIE Engine] 正在向云端 MLLM 发送跨模态数据进行深度语义推理 | provider={self.provider}")

        try:
            if not self.available:
                raise RuntimeError("PRO 引擎 API 配置不完整或 provider 不受支持。")
            if self.provider == "gemini":
                result = self._detect_gemini(text, image_path, video_path)
            else:
                result = self._detect_openai_compatible(text, image_path, video_path)
            print("✅ [CMIE Engine] 云端推理完成！")
            return result
        except Exception as e:
            print(f"❌ [CMIE Engine] API 调用最终失败: {e}")
            return {
                "is_fake": False,
                "confidence": 0.0,
                "reasoning": f"【SYSTEM ALERT】CMIE 云端引擎连接中断或解析异常。\n错误详情: {str(e)}\n请检查 Pro API Key、额度配置或网络状态。"
            }
