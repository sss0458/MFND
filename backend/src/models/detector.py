import os
from typing import Dict, Optional

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("DISABLE_SAFETENSORS_CONVERSION", "1")

import cv2
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from PIL import Image
from transformers import (
    AutoImageProcessor,
    AutoModel,
    AutoModelForSequenceClassification,
    AutoTokenizer,
)


LEGACY_TEXT_MODEL_NAME = "IDEA-CCNL/Erlangshen-Roberta-110M-Sentiment"
VISION_MODEL_NAME = "google/vit-base-patch16-224-in21k"
DEFAULT_TEXT_COMPATIBLE_MODEL_NAME = "divyanshu-chauhan-7786/fake-news-roberta"
DEFAULT_TEXT_COMPATIBLE_INPUT_STYLE = "plain"
DEFAULT_TEXT_COMPATIBLE_FAKE_INDEX = 0
DEFAULT_TEXT_COMPATIBLE_REAL_INDEX = 1
DEFAULT_TEXT_ENSEMBLE_ENABLED = False
DEFAULT_TEXT_ENSEMBLE_SECONDARY_MODEL_NAME = "Arko007/fact-check1-v1"
DEFAULT_TEXT_ENSEMBLE_SECONDARY_INPUT_STYLE = "plain"
DEFAULT_TEXT_ENSEMBLE_SECONDARY_FAKE_INDEX = 1
DEFAULT_TEXT_ENSEMBLE_SECONDARY_REAL_INDEX = 0
DEFAULT_TEXT_ENSEMBLE_SECONDARY_TRUST_REMOTE_CODE = False
DEFAULT_TEXT_ENSEMBLE_PRIMARY_WEIGHT = 0.7
DEFAULT_TEXT_ENSEMBLE_FAKE_THRESHOLD = 0.7
DEFAULT_FAST_MODE = "text_compatible"
DEFAULT_TEXT_MAX_LENGTH = 256
DEFAULT_TEXT_SOFTMAX_TEMPERATURE = 2.5
DEFAULT_TEXT_CONFIDENCE_CEILING = 99.0


class MultimodalDetector(nn.Module):
    def __init__(self, feature_dim: int = 768):
        super().__init__()
        self.classifier = nn.Sequential(
            nn.Linear(feature_dim * 3, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 2),
        )

    def forward(self, text_features, img_features, video_features):
        combined_features = torch.cat((text_features, img_features, video_features), dim=1)
        return self.classifier(combined_features)


class FocalLoss(nn.Module):
    def __init__(self, alpha: int = 1, gamma: int = 2):
        super().__init__()
        self.alpha = alpha
        self.gamma = gamma

    def forward(self, inputs, targets):
        ce_loss = F.cross_entropy(inputs, targets, reduction="none")
        pt = torch.exp(-ce_loss)
        focal_loss = self.alpha * (1 - pt) ** self.gamma * ce_loss
        return focal_loss.mean()


class MFNDManager:
    def __init__(self, mode: Optional[str] = None):
        self.device = self._resolve_device()
        self.mode = (mode or os.environ.get("FAST_ENGINE_MODE", DEFAULT_FAST_MODE)).strip().lower()
        self.hf_local_only = self._read_bool_env("FAST_HF_LOCAL_ONLY", False)
        self.text_compatible_model_name = os.environ.get(
            "FAST_TEXT_MODEL_NAME",
            DEFAULT_TEXT_COMPATIBLE_MODEL_NAME,
        ).strip()
        self.text_compatible_input_style = os.environ.get(
            "FAST_TEXT_INPUT_STYLE",
            DEFAULT_TEXT_COMPATIBLE_INPUT_STYLE,
        ).strip()
        self.text_compatible_trust_remote_code = (
            os.environ.get("FAST_TEXT_TRUST_REMOTE_CODE", "false").strip().lower() == "true"
        )
        self.text_compatible_fake_index = int(
            os.environ.get("FAST_TEXT_FAKE_INDEX", str(DEFAULT_TEXT_COMPATIBLE_FAKE_INDEX))
        )
        self.text_compatible_real_index = int(
            os.environ.get("FAST_TEXT_REAL_INDEX", str(DEFAULT_TEXT_COMPATIBLE_REAL_INDEX))
        )
        self.text_ensemble_enabled = self._read_bool_env(
            "FAST_TEXT_ENSEMBLE_ENABLED",
            DEFAULT_TEXT_ENSEMBLE_ENABLED,
        )
        self.text_ensemble_secondary_model_name = os.environ.get(
            "FAST_TEXT_ENSEMBLE_SECONDARY_MODEL_NAME",
            DEFAULT_TEXT_ENSEMBLE_SECONDARY_MODEL_NAME,
        ).strip()
        self.text_ensemble_secondary_input_style = os.environ.get(
            "FAST_TEXT_ENSEMBLE_SECONDARY_INPUT_STYLE",
            DEFAULT_TEXT_ENSEMBLE_SECONDARY_INPUT_STYLE,
        ).strip()
        self.text_ensemble_secondary_trust_remote_code = self._read_bool_env(
            "FAST_TEXT_ENSEMBLE_SECONDARY_TRUST_REMOTE_CODE",
            DEFAULT_TEXT_ENSEMBLE_SECONDARY_TRUST_REMOTE_CODE,
        )
        self.text_ensemble_secondary_fake_index = int(
            os.environ.get(
                "FAST_TEXT_ENSEMBLE_SECONDARY_FAKE_INDEX",
                str(DEFAULT_TEXT_ENSEMBLE_SECONDARY_FAKE_INDEX),
            )
        )
        self.text_ensemble_secondary_real_index = int(
            os.environ.get(
                "FAST_TEXT_ENSEMBLE_SECONDARY_REAL_INDEX",
                str(DEFAULT_TEXT_ENSEMBLE_SECONDARY_REAL_INDEX),
            )
        )
        self.text_ensemble_primary_weight = float(
            os.environ.get(
                "FAST_TEXT_ENSEMBLE_PRIMARY_WEIGHT",
                str(DEFAULT_TEXT_ENSEMBLE_PRIMARY_WEIGHT),
            )
        )
        self.text_ensemble_fake_threshold = float(
            os.environ.get(
                "FAST_TEXT_ENSEMBLE_FAKE_THRESHOLD",
                str(DEFAULT_TEXT_ENSEMBLE_FAKE_THRESHOLD),
            )
        )
        self.text_max_length = int(
            os.environ.get("FAST_TEXT_MAX_LENGTH", str(DEFAULT_TEXT_MAX_LENGTH))
        )
        self.text_softmax_temperature = max(
            float(
                os.environ.get(
                    "FAST_TEXT_SOFTMAX_TEMPERATURE",
                    str(DEFAULT_TEXT_SOFTMAX_TEMPERATURE),
                )
            ),
            1e-6,
        )
        self.text_confidence_ceiling = float(
            os.environ.get(
                "FAST_TEXT_CONFIDENCE_CEILING",
                str(DEFAULT_TEXT_CONFIDENCE_CEILING),
            )
        )
        self.allow_unsafe_pickle_weights = self._read_bool_env(
            "FAST_ALLOW_UNSAFE_PICKLE_WEIGHTS",
            False,
        )

        self.text_model = None
        self.img_model = None
        self.tokenizer = None
        self.img_processor = None
        self.fusion_model = None

        self.text_classifier = None
        self.text_classifier_tokenizer = None
        self.secondary_text_classifier = None
        self.secondary_text_classifier_tokenizer = None
        self.visual_backbone_error = None
        self.initialization_error = None

        print(f"📦 FAST 引擎初始化中 | 模式: {self.mode} | 设备: {self.device}")
        self._initialize_mode()

    def _resolve_device(self) -> torch.device:
        if torch.cuda.is_available():
            return torch.device("cuda")
        if torch.backends.mps.is_available():
            return torch.device("mps")
        return torch.device("cpu")

    def _read_bool_env(self, name: str, default: bool) -> bool:
        raw = os.environ.get(name)
        if raw is None:
            return default
        return raw.strip().lower() == "true"

    def _initialize_mode(self) -> None:
        if self.mode == "legacy_fusion":
            try:
                self._initialize_legacy_mode()
            except Exception as exc:
                self._initialize_degraded_mode(exc)
            return

        if self.mode == "text_compatible":
            try:
                self._initialize_text_compatible_mode()
                return
            except Exception as exc:
                print(f"⚠️ 文本兼容模式初始化失败，转入安全降级模式: {exc}")
                self._initialize_degraded_mode(exc)
                return

        raise ValueError(f"Unsupported FAST engine mode: {self.mode}")

    def _initialize_degraded_mode(self, exc: Exception) -> None:
        self.mode = "degraded"
        self.initialization_error = str(exc)
        self.text_model = None
        self.img_model = None
        self.tokenizer = None
        self.img_processor = None
        self.fusion_model = None
        self.text_classifier = None
        self.text_classifier_tokenizer = None
        self.secondary_text_classifier = None
        self.secondary_text_classifier_tokenizer = None
        self.visual_backbone_error = self.initialization_error
        print(f"⚠️ FAST 引擎初始化失败，已进入安全降级模式: {exc}")

    def _load_pretrained_with_fallback(self, loader, model_name: str, **kwargs):
        errors = []

        try:
            return loader(model_name, local_files_only=True, **kwargs)
        except Exception as exc:
            errors.append(f"local cache miss/error: {exc}")
            print(f"ℹ️ 本地缓存未命中，尝试在线加载模型 {model_name}: {exc}")

        if self.hf_local_only:
            raise RuntimeError(
                f"FAST_HF_LOCAL_ONLY=true，且本地未找到模型 {model_name}。"
            )

        try:
            return loader(model_name, **kwargs)
        except Exception as exc:
            errors.append(f"remote load failed: {exc}")
            raise RuntimeError(
                f"模型加载失败: {model_name} | {' | '.join(errors)}"
            ) from exc

    def _initialize_legacy_mode(self) -> None:
        print("📦 正在初始化多模态特征提取引擎...")
        self.text_model = self._load_pretrained_with_fallback(
            AutoModel.from_pretrained,
            LEGACY_TEXT_MODEL_NAME,
            use_safetensors=self._should_use_safetensors(LEGACY_TEXT_MODEL_NAME),
        ).to(self.device)
        self.text_model.eval()
        self.tokenizer = self._load_pretrained_with_fallback(
            AutoTokenizer.from_pretrained,
            LEGACY_TEXT_MODEL_NAME,
        )

        self._ensure_visual_backbone()

        self.fusion_model = MultimodalDetector().to(self.device)
        self.fusion_model.eval()

    def _initialize_text_compatible_mode(self) -> None:
        print(
            "📰 正在初始化 FAST 文本优先兼容模式..."
            f" | 模型: {self.text_compatible_model_name}"
        )
        (
            self.text_classifier_tokenizer,
            self.text_classifier,
        ) = self._load_sequence_classifier(
            self.text_compatible_model_name,
            self.text_compatible_trust_remote_code,
        )

        if not self.text_ensemble_enabled:
            return

        if self.text_ensemble_secondary_model_name == self.text_compatible_model_name:
            print("⚠️ 文本融合次模型与主模型相同，将禁用双模型融合。")
            self.text_ensemble_enabled = False
            return

        print(
            "🧪 正在加载 FAST 双模型融合次模型..."
            f" | 模型: {self.text_ensemble_secondary_model_name}"
        )
        try:
            (
                self.secondary_text_classifier_tokenizer,
                self.secondary_text_classifier,
            ) = self._load_sequence_classifier(
                self.text_ensemble_secondary_model_name,
                self.text_ensemble_secondary_trust_remote_code,
            )
        except Exception as exc:
            print(f"⚠️ 双模型融合次模型加载失败，将回退为单模型文本模式: {exc}")
            self.text_ensemble_enabled = False
            self.secondary_text_classifier_tokenizer = None
            self.secondary_text_classifier = None

    def _load_sequence_classifier(self, model_name: str, trust_remote_code: bool):
        tokenizer = self._load_pretrained_with_fallback(
            AutoTokenizer.from_pretrained,
            model_name,
            trust_remote_code=trust_remote_code,
        )
        model = self._load_pretrained_with_fallback(
            AutoModelForSequenceClassification.from_pretrained,
            model_name,
            trust_remote_code=trust_remote_code,
            use_safetensors=self._should_use_safetensors(model_name),
        ).to(self.device)
        model.eval()
        return tokenizer, model

    def _should_use_safetensors(self, model_name: str) -> bool:
        if self.allow_unsafe_pickle_weights:
            return False
        return True

    def _prepare_text_input_by_style(self, text: str, input_style: str) -> str:
        normalized = " ".join(str(text).split())
        if input_style == "title_content_prompt":
            parts = normalized.split(". ", 1)
            title = parts[0][:140]
            content = parts[1] if len(parts) > 1 else normalized
            return f"<title>{title}<content>{content}<end>"
        return normalized

    def _prepare_text_compatible_input(self, text: str) -> str:
        return self._prepare_text_input_by_style(text, self.text_compatible_input_style)

    def _prepare_secondary_text_input(self, text: str) -> str:
        return self._prepare_text_input_by_style(text, self.text_ensemble_secondary_input_style)

    def _ensure_visual_backbone(self) -> bool:
        if self.img_model is not None and self.img_processor is not None:
            return True
        if self.mode == "degraded":
            return False

        try:
            self.img_model = self._load_pretrained_with_fallback(
                AutoModel.from_pretrained,
                VISION_MODEL_NAME,
                attn_implementation="eager",
                use_safetensors=self._should_use_safetensors(VISION_MODEL_NAME),
            ).to(self.device)
            self.img_model.eval()
            self.img_processor = self._load_pretrained_with_fallback(
                AutoImageProcessor.from_pretrained,
                VISION_MODEL_NAME,
            )
            self.visual_backbone_error = None
            return True
        except Exception as exc:
            self.img_model = None
            self.img_processor = None
            self.visual_backbone_error = str(exc)
            print(f"⚠️ 视觉骨干加载失败，将跳过图片/视频特征与 saliency: {exc}")
            return False

    def is_text_compatible_mode(self) -> bool:
        return self.mode == "text_compatible"

    def is_text_ensemble_enabled(self) -> bool:
        return self.is_text_compatible_mode() and self.text_ensemble_enabled and self.secondary_text_classifier is not None

    def describe_mode(self) -> str:
        if self.mode == "degraded":
            return "安全降级模式"
        if self.is_text_compatible_mode():
            if self.is_text_ensemble_enabled():
                return "双模型阈值融合模式"
            return "文本优先兼容模式"
        return "特征级融合模式"

    def _predict_text_probabilities(
        self,
        text: str,
        tokenizer,
        model,
        input_style: str,
        fake_index: int,
        real_index: int,
    ):
        inputs = tokenizer(
            self._prepare_text_input_by_style(text, input_style),
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=self.text_max_length,
        ).to(self.device)

        with torch.no_grad():
            outputs = model(**inputs)
            probs = F.softmax(outputs.logits / self.text_softmax_temperature, dim=1)

        return probs[0][fake_index].item(), probs[0][real_index].item()

    def _extract_video_features(self, video_path: Optional[str], num_frames: int = 8):
        if not self._ensure_visual_backbone():
            return torch.zeros((1, 768), device=self.device)

        if not video_path or not os.path.exists(video_path):
            return torch.zeros((1, 768), device=self.device)

        try:
            cap = cv2.VideoCapture(video_path)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            if total_frames <= 0:
                cap.release()
                return torch.zeros((1, 768), device=self.device)

            indices = np.linspace(0, total_frames - 1, num=num_frames, dtype=int)
            frame_features = []

            for idx in indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if not ret:
                    continue

                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_img = Image.fromarray(frame_rgb)
                inputs = self.img_processor(images=pil_img, return_tensors="pt").to(self.device)
                with torch.no_grad():
                    outputs = self.img_model(**inputs)
                    frame_features.append(outputs.last_hidden_state[:, 0, :])

            cap.release()

            if not frame_features:
                return torch.zeros((1, 768), device=self.device)

            return torch.mean(torch.stack(frame_features), dim=0)
        except Exception as exc:
            print(f"❌ 视频处理失败: {exc}")
            return torch.zeros((1, 768), device=self.device)

    def _legacy_detect(self, text=None, image_path=None, video_path=None) -> Dict[str, object]:
        if text:
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=128,
            ).to(self.device)
            with torch.no_grad():
                text_vec = self.text_model(**inputs).last_hidden_state[:, 0, :]
        else:
            text_vec = torch.zeros((1, 768), device=self.device)

        if image_path:
            if self._ensure_visual_backbone():
                img = Image.open(image_path).convert("RGB")
                inputs = self.img_processor(images=img, return_tensors="pt").to(self.device)
                with torch.no_grad():
                    img_vec = self.img_model(**inputs).last_hidden_state[:, 0, :]
            else:
                img_vec = torch.zeros((1, 768), device=self.device)
        else:
            img_vec = torch.zeros((1, 768), device=self.device)

        video_vec = self._extract_video_features(video_path)

        with torch.no_grad():
            logits = self.fusion_model(text_vec, img_vec, video_vec)
            probs = F.softmax(logits, dim=1)
            fake_prob = probs[0][1].item()

        is_fake = fake_prob > 0.5
        return {
            "is_fake": is_fake,
            "confidence": round(fake_prob * 100 if is_fake else (1 - fake_prob) * 100, 2),
            "details": {
                "engine_mode": self.mode,
                "text_score": round(fake_prob if text else 0.0, 4),
                "img_score": round(fake_prob if image_path else 0.0, 4),
                "video_score": round(fake_prob if video_path else 0.0, 4),
            },
        }

    def _text_compatible_detect(self, text=None, image_path=None, video_path=None) -> Dict[str, object]:
        if not text:
            note = f"当前 FAST 为{self.describe_mode()}，未提供文本时只返回中性结果。"
            return {
                "is_fake": False,
                "confidence": 50.0,
                "details": {
                    "engine_mode": self.mode,
                    "text_score": 0.0,
                    "img_score": 0.0,
                    "video_score": 0.0,
                    "note": note,
                },
            }

        primary_fake_prob, primary_real_prob = self._predict_text_probabilities(
            text,
            self.text_classifier_tokenizer,
            self.text_classifier,
            self.text_compatible_input_style,
            self.text_compatible_fake_index,
            self.text_compatible_real_index,
        )

        fused_fake_prob = primary_fake_prob
        fused_real_prob = primary_real_prob
        details = {
            "engine_mode": self.mode,
            "fusion_strategy": "single_model",
            "text_model_name": self.text_compatible_model_name,
            "text_score": round(primary_fake_prob, 4),
            "text_real_score": round(primary_real_prob, 4),
            "img_score": 0.0,
            "video_score": 0.0,
        }

        if self.is_text_ensemble_enabled():
            secondary_fake_prob, secondary_real_prob = self._predict_text_probabilities(
                text,
                self.secondary_text_classifier_tokenizer,
                self.secondary_text_classifier,
                self.text_ensemble_secondary_input_style,
                self.text_ensemble_secondary_fake_index,
                self.text_ensemble_secondary_real_index,
            )
            fused_fake_prob = (
                self.text_ensemble_primary_weight * primary_fake_prob
                + (1 - self.text_ensemble_primary_weight) * secondary_fake_prob
            )
            fused_real_prob = 1 - fused_fake_prob
            details.update(
                {
                    "fusion_strategy": "weighted_threshold",
                    "text_model_name": (
                        f"{self.text_compatible_model_name} + "
                        f"{self.text_ensemble_secondary_model_name}"
                    ),
                    "primary_text_model_name": self.text_compatible_model_name,
                    "primary_text_score": round(primary_fake_prob, 4),
                    "primary_text_real_score": round(primary_real_prob, 4),
                    "secondary_text_model_name": self.text_ensemble_secondary_model_name,
                    "secondary_text_score": round(secondary_fake_prob, 4),
                    "secondary_text_real_score": round(secondary_real_prob, 4),
                    "ensemble_primary_weight": round(self.text_ensemble_primary_weight, 4),
                    "ensemble_secondary_weight": round(1 - self.text_ensemble_primary_weight, 4),
                    "ensemble_fake_threshold": round(self.text_ensemble_fake_threshold, 4),
                    "text_score": round(fused_fake_prob, 4),
                    "text_real_score": round(fused_real_prob, 4),
                }
            )

        if self.is_text_ensemble_enabled():
            is_fake = fused_fake_prob >= self.text_ensemble_fake_threshold
        else:
            is_fake = primary_fake_prob >= primary_real_prob
        confidence = fused_fake_prob if is_fake else fused_real_prob
        confidence_percent = min(round(confidence * 100, 2), self.text_confidence_ceiling)

        if image_path or video_path:
            details["note"] = (
                f"图片/视频输入已接收，但{self.describe_mode()}当前仍以新闻文本作为主判据。"
            )
        details["text_max_length"] = self.text_max_length
        details["text_softmax_temperature"] = round(self.text_softmax_temperature, 4)
        details["text_confidence_ceiling"] = round(self.text_confidence_ceiling, 2)

        return {
            "is_fake": is_fake,
            "confidence": confidence_percent,
            "details": details,
        }

    def detect(self, text=None, image_path=None, video_path=None):
        if self.mode == "degraded":
            note = (
                "FAST 引擎当前处于安全降级模式，原因: "
                f"{self.initialization_error or '模型未能完成初始化'}"
            )
            return {
                "is_fake": False,
                "confidence": 50.0,
                "details": {
                    "engine_mode": self.mode,
                    "text_score": 0.0,
                    "img_score": 0.0,
                    "video_score": 0.0,
                    "note": note,
                },
            }
        if self.is_text_compatible_mode():
            return self._text_compatible_detect(text=text, image_path=image_path, video_path=video_path)
        return self._legacy_detect(text=text, image_path=image_path, video_path=video_path)

    def generate_saliency_map(self, image_path: str, output_dir: str, prefix: str) -> Optional[str]:
        print(f"🔍 [XAI Engine] 正在对图像进行伪影分析: {image_path}")
        if not self._ensure_visual_backbone():
            return None

        original_img = cv2.imread(image_path)
        if original_img is None:
            raise Exception(f"Failed to read image at {image_path}")

        h, w, _ = original_img.shape

        try:
            pil_img = Image.fromarray(cv2.cvtColor(original_img, cv2.COLOR_BGR2RGB))
            inputs = self.img_processor(images=pil_img, return_tensors="pt")
            input_tensor = inputs["pixel_values"].to(self.device)
        except Exception as exc:
            print(f"❌ [预处理崩溃] 图像预处理失败: {exc}")
            return None

        try:
            with torch.no_grad():
                outputs = self.img_model(input_tensor, output_attentions=True)
                last_layer_attn = outputs.attentions[-1][0]
                mean_attn = last_layer_attn.mean(dim=0)
                cls_attn = mean_attn[0, 1:]
                attn_map = cls_attn.reshape(14, 14).cpu().numpy()
        except Exception as exc:
            print(f"❌ [核心引擎崩溃] 抓取模型注意力权重失败: {exc}")
            return None

        try:
            norm_attn = cv2.normalize(
                attn_map,
                None,
                alpha=0,
                beta=255,
                norm_type=cv2.NORM_MINMAX,
                dtype=cv2.CV_8U,
            )
            heatmap_resized = cv2.resize(norm_attn, (224, 224), interpolation=cv2.INTER_CUBIC)
            heatmap_color = cv2.applyColorMap(heatmap_resized, cv2.COLORMAP_JET)
            heatmap_original_size = cv2.resize(heatmap_color, (w, h))
            saliency_img = cv2.addWeighted(original_img, 0.6, heatmap_original_size, 0.4, 0)
        except Exception as exc:
            print(f"❌ 绘制热力图失败: {exc}")
            return None

        save_name = f"{prefix}_saliency.jpg"
        save_path = os.path.join(output_dir, save_name)
        print(f"✅ 生成伪影显微镜图并保存到: {save_path}")
        cv2.imwrite(save_path, saliency_img)
        return save_path
