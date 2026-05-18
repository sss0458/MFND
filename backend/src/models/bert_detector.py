# backend/src/model/bert_detector.py

import torch
import torch.nn.functional as F
from transformers import BertTokenizer, BertForSequenceClassification

class TextFakeDetector:
    def __init__(self, model_name='bert-base-chinese'):
        """
        初始化 BERT 模型 (专门处理中文)
        """
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"🔥 BERT 模型加载中 ({self.device})... 这可能需要一点时间下载...")

        try:
            # 1. 加载分词器 (Tokenizer)
            self.tokenizer = BertTokenizer.from_pretrained(model_name)
            
            # 2. 加载模型 (SequenceClassification 用于二分类)
            # num_labels=2 表示分类为 [真, 假]
            self.model = BertForSequenceClassification.from_pretrained(model_name, num_labels=2)
            
            self.model.to(self.device)
            self.model.eval() # 开启评估模式
            print("✅ BERT 模型加载完成")
        except Exception as e:
            print(f"❌ BERT 加载失败: {e}")
            self.model = None

    def predict(self, text):
        """
        对文本进行真伪推理
        :return: (is_fake: bool, confidence: float, label: str)
        """
        if not self.model or not text:
            return False, 0.0, "模型未就绪"

        try:
            # 1. 文本预处理 (Tokenize + Pad + Truncate)
            # max_length=128 对推文/评论足够了
            inputs = self.tokenizer(
                text, 
                return_tensors="pt", 
                padding=True, 
                truncation=True, 
                max_length=128
            )
            
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # 2. 推理
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = F.softmax(logits, dim=1)

            # 3. 解析结果
            # 假设 index 0 = 真实 (Real), index 1 = 虚假 (Fake)
            # 注意：未微调的模型输出可能随机，但逻辑是通的
            fake_prob = probs[0][1].item()
            
            is_fake = fake_prob > 0.5
            confidence = fake_prob * 100
            
            return is_fake, round(confidence, 2), "高风险" if is_fake else "正常"

        except Exception as e:
            print(f"⚠️ BERT 推理出错: {e}")
            return False, 0.0, "错误"