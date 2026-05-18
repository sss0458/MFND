# backend/src/data_loader/processor.py

import cv2
import numpy as np
import os
import uuid
import re
import emoji

class MultimodalProcessor:
    def __init__(self, target_size=(224, 224)):
        """
        多模态数据预处理框架
        :param target_size: 模型输入尺寸 (224, 224)
        """
        self.target_size = target_size
        
        # 预编译正则模式 (提升清洗速度)
        self.url_pattern = re.compile(r'https?://\S+|www\.\S+')
        self.user_pattern = re.compile(r'@\w+')
        
        # 加载人脸检测器 (用于辅助图像清洗)
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )

    # --- 1. 文本处理模块 ---
    def clean_text(self, text: str) -> str:
        """
        论文点：支持文本中表情符号的去除、超链接的去除
        """
        if not text: return ""
        
        # 1. 去除超链接
        text = self.url_pattern.sub('', text)
        # 2. 去除 @用户
        text = self.user_pattern.sub('', text)
        # 3. 去除表情符号 (将表情替换为空)
        text = emoji.replace_emoji(text, replace='')
        # 4. 去除多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text

    # --- 2. 图像处理模块 ---
    def process_image(self, image_path, output_dir):
        """
        图片去边框操作和调整分辨率和大小到预定格式
        """
        img = cv2.imread(image_path)
        if img is None: return [], "读取失败"

        # 策略 A: 优先尝试检测人脸并裁剪
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.1, 5)
        
        processed_paths = []
        
        targets = []
        if len(faces) > 0:
            # 如果有人脸，裁剪人脸
            for (x, y, w, h) in faces:
                targets.append(img[y:y+h, x:x+w])
            msg = f"检测到 {len(faces)} 个人脸"
        else:
            # 策略 B: 如果没有人脸，自动去黑边 + 缩放全图
            cropped = self._remove_borders(img)
            targets.append(cropped)
            msg = "未检测到人脸，已执行去黑边与缩放"

        # 统一标准化 (Resize + Pad)
        for sub_img in targets:
            final_img = self._resize_pad(sub_img)
            
            # 保存
            filename = f"proc_{uuid.uuid4().hex[:8]}.jpg"
            save_path = os.path.join(output_dir, filename)
            cv2.imwrite(save_path, final_img)
            processed_paths.append(f"/static/processed/{filename}")

        return processed_paths, msg

    # --- 3. 视频处理模块 ---
    def process_video(self, video_path, output_dir, interval=30):
        """
        论文点：视频关键帧的截取
        :param interval: 每多少帧截取一张 (关键帧策略)
        """
        cap = cv2.VideoCapture(video_path)
        frames_paths = []
        frame_count = 0
        
        while True:
            ret, frame = cap.read()
            if not ret: break
            
            # 关键帧提取逻辑
            if frame_count % interval == 0:
                # 对每一帧执行图像标准化处理
                # 这里我们简单做去黑边+缩放，不强制人脸检测以提高速度
                processed_frame = self._resize_pad(self._remove_borders(frame))
                
                filename = f"frame_{frame_count}_{uuid.uuid4().hex[:6]}.jpg"
                save_path = os.path.join(output_dir, filename)
                cv2.imwrite(save_path, processed_frame)
                
                frames_paths.append(f"/static/processed/{filename}")
            
            frame_count += 1
            if len(frames_paths) >= 10: break # 演示用：最多截10张，防止太慢

        cap.release()
        return frames_paths

    # --- 内部工具函数 ---
    def _remove_borders(self, img):
        """自动去除黑边 (基于阈值轮廓)"""
        try:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 10, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                c = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(c)
                # 稍微放宽一点裁剪范围
                return img[y:y+h, x:x+w]
        except Exception:
            pass
        return img # 失败则返回原图

    def _resize_pad(self, img):
        """Letterbox Resize: 保持比例缩放，不足补黑边"""
        h, w = img.shape[:2]
        sh, sw = self.target_size
        scale = min(sw/w, sh/h)
        new_w, new_h = int(w * scale), int(h * scale)
        resized = cv2.resize(img, (new_w, new_h))
        
        final_img = np.zeros((sh, sw, 3), dtype=np.uint8)
        x_off = (sw - new_w) // 2
        y_off = (sh - new_h) // 2
        final_img[y_off:y_off+new_h, x_off:x_off+new_w] = resized
        return final_img