# backend/web_system/app.py
import os
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')
import sys
import uuid
import time
import random
import shutil
import csv
import json
import re
from typing import List, Optional
from datetime import datetime
import string
import base64
from io import BytesIO
from captcha.image import ImageCaptcha
from database import SystemConfig
from io import StringIO

# 👇 引入 FastAPI 依赖注入工具 Depends
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends , Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Optional

# 👇 引入数据库配置和模型
from database import get_db, User, DetectTask, ReviewMessage

# --------------------------------------------------------------------------
# 1. 📂 核心路径配置 (最关键的部分)
# --------------------------------------------------------------------------

# 获取当前文件的绝对路径: .../backend/web_system/app.py
current_file_path = os.path.abspath(__file__)

# 向上推导目录
web_system_dir = os.path.dirname(current_file_path) # .../backend/web_system
backend_dir = os.path.dirname(web_system_dir)       # .../backend
project_root = os.path.dirname(backend_dir)         # .../Project (根目录)

# 将 backend 目录加入 Python 搜索路径，确保能找到 src
sys.path.append(backend_dir)

# 🚀 导入自定义模块 (必须在 sys.path.append 之后)
from src.data_loader.processor import MultimodalProcessor
from src.models.detector import MFNDManager 
from src.models.cmie_engine import CMIEEngine

# --------------------------------------------------------------------------
# 🚀 初始化 APP
# --------------------------------------------------------------------------
app = FastAPI(title="Deepfake Detection API")
# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], 
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义全局内存变量来存储引擎状态
GLOBAL_ENGINE_STATUS = {
    "fast": True,
    "pro": False
}

# 定义数据目录 (在项目根目录下，与 backend 平级)
DATA_DIR = os.path.join(project_root, "data")
UPLOAD_DIR = os.path.join(DATA_DIR, "uploads")
PROCESSED_DIR = os.path.join(DATA_DIR, "processed")

# 定义内存字典
CAPTCHA_STORE = {}
REVIEW_PRESENCE = {}
PRESENCE_WINDOW_SECONDS = 15

# 自动创建文件夹
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

BATCH_MAX_ITEMS = 50
TEXT_COLUMN_HINTS = {
    "text", "content", "news", "body", "title", "headline", "article",
    "article_text", "news_text", "post", "post_text", "tweet", "tweet_text",
    "sentence", "statement", "description", "caption", "comment", "claim",
    "message", "summary", "context", "transcript"
}
NON_TEXT_COLUMN_HINTS = {
    "id", "label", "label_str", "path", "paths", "url", "urls", "image",
    "image_path", "video", "video_path", "file", "filename", "index", "idx",
    "source", "author", "date", "time", "split", "class", "target"
}

print(f"-------- 路径配置 --------")
print(f"✅ 项目根目录: {project_root}")
print(f"✅ 数据目录: {DATA_DIR}")
print(f"✅ 上传目录: {UPLOAD_DIR}")
print(f"------------------------")

# 🌍 挂载静态资源
app.mount("/static", StaticFiles(directory=DATA_DIR), name="static")

# 初始化处理器
processor = MultimodalProcessor(target_size=(224, 224))

print("📦 正在初始化多模态特征级融合引擎 (ViT + RoBERTa + Focal Loss)...")
mfnd_engine = MFNDManager()

print("🧠 正在初始化 MLLM 语义推理引擎 (CMIE) - [Pro Mode]...")
cmie_engine = CMIEEngine()

# ================= 数据校验模型 (Pydantic) =================
class LoginSchema(BaseModel):
    username: str
    password: str

class AuditSchema(BaseModel):
    task_id: int
    result: str # REAL / FAKE
    comment: str


class ReviewMessageSchema(BaseModel):
    sender_role: str
    sender_name: Optional[str] = None
    content: str


class ReviewPresenceSchema(BaseModel):
    role: str
    name: Optional[str] = None


class UserCreateSchema(BaseModel):
    username: str
    password: str
    role: str
    note: Optional[str] = None
    security_question: Optional[str] = None
    security_answer: Optional[str] = None

class RegisterSchema(BaseModel):
    username: str
    password: str
    security_question: str
    security_answer: str
    captcha_id: str   # 前端传回来的验证码发票号
    captcha_code: str # 用户肉眼看图填写的字符


class PasswordRecoveryQuestionSchema(BaseModel):
    username: str


class PasswordRecoveryResetSchema(BaseModel):
    username: str
    security_answer: str
    new_password: str

class EngineStatusSchema(BaseModel):
    engine: str
    status: bool

class UserStatusSchema(BaseModel):
    status: int


def normalize_security_answer(answer: Optional[str]) -> str:
    return (answer or "").strip().lower()


def ensure_engine_available(model_type: str, db: Session):
    engine_key = f"engine_{model_type.lower()}"
    engine_record = db.query(SystemConfig).filter(SystemConfig.config_key == engine_key).first()
    if engine_record and engine_record.config_value.lower() == "false":
        print(f"🛑 [SECURITY BLOCK] 拦截到对已关停引擎 {model_type.upper()} 的非法调用！")
        raise HTTPException(
            status_code=503,
            detail=f"【服务熔断】{model_type.upper()} 引擎目前处于维护/离线状态，拒绝执行推理。"
        )


def save_upload_file(upload_file: UploadFile, target_path: str):
    upload_file.file.seek(0)
    with open(target_path, "wb") as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    upload_file.file.seek(0)


def build_public_url(request: Request, relative_path: str) -> str:
    base_url = str(request.base_url).rstrip("/")
    normalized_path = relative_path if relative_path.startswith("/") else f"/{relative_path}"
    return f"{base_url}{normalized_path}"


def normalize_public_url(request: Request, raw_url: Optional[str]) -> str:
    if not raw_url:
        return ""
    if raw_url.startswith("/"):
        return build_public_url(request, raw_url)
    if raw_url.startswith("http://localhost:8000") or raw_url.startswith("http://127.0.0.1:8000"):
        path = raw_url.split("8000", 1)[-1] or ""
        return build_public_url(request, path)
    return raw_url


def normalize_url_list(request: Request, raw_urls) -> List[str]:
    if not raw_urls:
        return []
    urls = raw_urls if isinstance(raw_urls, list) else []
    return [normalize_public_url(request, url) for url in urls if url]


def serialize_task(task: DetectTask, request: Request) -> dict:
    media_urls = normalize_url_list(request, task.media_urls)
    saliency_urls = normalize_url_list(request, task.saliency_urls)
    return {
        "id": task.id,
        "task_no": task.task_no,
        "title": task.title,
        "content": task.content,
        "media_urls": media_urls,
        "url": media_urls[0] if media_urls else "",
        "ai_score": task.ai_score,
        "ai_reason": task.ai_reason,
        "saliency_urls": saliency_urls,
        "status": task.status,
        "create_time": task.create_time.isoformat() if task.create_time else None,
        "audit_result": task.audit_result,
        "audit_comment": task.audit_comment,
        "is_user_deleted": task.is_user_deleted,
    }


def serialize_review_message(message: ReviewMessage) -> dict:
    return {
        "id": message.id,
        "task_id": message.task_id,
        "sender_role": message.sender_role,
        "sender_name": message.sender_name or ("审核员" if message.sender_role == "auditor" else "用户"),
        "content": message.content,
        "create_time": message.create_time.isoformat() if message.create_time else None,
    }


def get_review_presence_snapshot(task_id: int) -> dict:
    now = time.time()
    snapshot = {}
    task_presence = REVIEW_PRESENCE.get(task_id, {})

    for role in ("user", "auditor"):
        entry = task_presence.get(role) or {}
        last_seen = float(entry.get("last_seen") or 0)
        is_online = now - last_seen <= PRESENCE_WINDOW_SECONDS
        snapshot[role] = {
            "online": is_online,
            "name": entry.get("name") or ("审核员" if role == "auditor" else "用户"),
            "last_seen": datetime.fromtimestamp(last_seen).isoformat() if last_seen else None,
        }

    return snapshot


def build_task_query(db: Session, role: str, status_filter: Optional[str]):
    query = db.query(DetectTask)

    if role == "user":
        query = query.filter(DetectTask.is_user_deleted == False)

    if role == "auditor" and status_filter:
        if status_filter == "PENDING":
            query = query.filter(DetectTask.status != "audited")
        elif status_filter == "AUDITED":
            query = query.filter(DetectTask.status == "audited")

    return query


def make_csv_response(filename: str, rows: List[dict], fieldnames: List[str]) -> StreamingResponse:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    buffer.seek(0)

    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv; charset=utf-8", headers=headers)


def detect_single_news(
    request: Request,
    db: Session,
    model_type: str,
    text: Optional[str] = None,
    images: Optional[List[UploadFile]] = None,
    video: Optional[UploadFile] = None,
    title_prefix: Optional[str] = None
):
    valid_images = [img for img in (images or []) if img and img.filename]
    valid_video = video if video and video.filename else None

    if not text and not valid_images and not valid_video:
        raise HTTPException(status_code=400, detail="至少需要提供一种模态的数据")

    session_id = uuid.uuid4().hex
    final_image_paths = []
    final_video_path = None
    display_urls = []
    cleaned_text = processor.clean_text(text) if text else ""

    if valid_images:
        for idx, img in enumerate(valid_images):
            img_ext = os.path.splitext(img.filename)[1]
            img_name = f"{session_id}_img_{idx}{img_ext}"
            img_path = os.path.join(UPLOAD_DIR, img_name)
            save_upload_file(img, img_path)
            final_image_paths.append(img_path)
            display_urls.append(f"/static/uploads/{img_name}")

    if valid_video:
        vid_ext = os.path.splitext(valid_video.filename)[1]
        vid_name = f"{session_id}_vid{vid_ext}"
        final_video_path = os.path.join(UPLOAD_DIR, vid_name)
        save_upload_file(valid_video, final_video_path)
        display_urls.append(f"/static/uploads/{vid_name}")

    primary_image_path = final_image_paths[0] if final_image_paths else None
    modals_found = [m for m, v in [("文", text), (f"图({len(final_image_paths)})", final_image_paths), ("视", valid_video)] if v]
    saliency_urls_list = []

    if model_type == "pro":
        detect_res = cmie_engine.detect(
            text=cleaned_text,
            image_path=primary_image_path,
            video_path=final_video_path
        )
        is_fake = detect_res["is_fake"]
        predicted_confidence = detect_res["confidence"]
        reason = detect_res["reasoning"]
    else:
        detect_res = mfnd_engine.detect(
            text=cleaned_text,
            image_path=primary_image_path,
            video_path=final_video_path
        )
        is_fake = detect_res["is_fake"]
        predicted_confidence = detect_res.get("predicted_confidence", detect_res["confidence"])
        if mfnd_engine.is_text_compatible_mode():
            if cleaned_text:
                if mfnd_engine.is_text_ensemble_enabled():
                    reason = (
                        f"Fast {mfnd_engine.describe_mode()}分析完成。涉及模态: {'+'.join(modals_found)}。"
                        " 当前采用双模型概率加权与阈值融合，以新闻文本作为主判据，"
                        "图片/视频输入仅保留兼容接入。"
                    )
                else:
                    reason = (
                        f"Fast {mfnd_engine.describe_mode()}分析完成。涉及模态: {'+'.join(modals_found)}。"
                        " 当前以新闻文本作为主判据，图片/视频输入仅保留兼容接入。"
                    )
            else:
                reason = (
                    f"Fast {mfnd_engine.describe_mode()}已接收多模态输入，但当前未提供文本，"
                    "因此返回中性结果。"
                )
        else:
            reason = (
                f"Fast {mfnd_engine.describe_mode()}分析完成。涉及模态: {'+'.join(modals_found)}。"
                " 经过向量空间对齐与多层感知机(MLP)判定。"
            )

        if final_image_paths:
            print("🔍 [Fast Mode] 正在为图片调用 XAI 引擎...")
            for idx, img_path in enumerate(final_image_paths):
                try:
                    saliency_path = mfnd_engine.generate_saliency_map(
                        img_path, PROCESSED_DIR, f"{session_id}_{idx}"
                    )
                    if saliency_path:
                        saliency_filename = os.path.basename(saliency_path)
                        saliency_urls_list.append(f"/static/processed/{saliency_filename}")
                except Exception as e:
                    print(f"⚠️ 第 {idx + 1} 张伪影图生成报错跳过: {e}")

            if saliency_urls_list:
                if mfnd_engine.is_text_compatible_mode():
                    reason += f" 已生成 {len(saliency_urls_list)} 张视觉定位图，仅供人工参考。"
                else:
                    reason += f" 已提取 {len(saliency_urls_list)} 张高维特征注意力，并生成定位图。"

    fake_probability = detect_res.get(
        "fake_probability",
        predicted_confidence if is_fake else (100.0 - predicted_confidence),
    )
    real_probability = detect_res.get("real_probability", 100.0 - fake_probability)
    db_ai_score = fake_probability
    task_title = title_prefix or f"[{model_type.upper()}] 多模态检测_{session_id[:6]}"

    new_task = DetectTask(
        task_no=session_id,
        title=task_title,
        content=cleaned_text,
        media_urls=display_urls,
        ai_score=db_ai_score,
        ai_reason=reason,
        saliency_urls=saliency_urls_list,
        status="pending"
    )
    db.add(new_task)
    db.commit()
    db.refresh(new_task)

    public_media_urls = normalize_url_list(request, display_urls)
    public_saliency_urls = normalize_url_list(request, saliency_urls_list)

    return {
        "taskId": new_task.id,
        "taskNo": session_id,
        "title": new_task.title,
        "isFake": is_fake,
        "confidence": fake_probability,
        "fakeProbability": fake_probability,
        "realProbability": real_probability,
        "predictedConfidence": predicted_confidence,
        "features": reason,
        "url": public_media_urls[0] if public_media_urls else "",
        "mediaUrls": public_media_urls,
        "content": cleaned_text,
        "modals": modals_found,
        "saliencyUrls": public_saliency_urls,
        "modelUsed": model_type,
        "status": "pending"
    }


def parse_batch_texts(raw_text: Optional[str], file_content: Optional[str], filename: Optional[str]) -> List[str]:
    items = []
    parsed_from_file = []

    def append_lines(lines):
        for line in lines:
            cleaned = (line or "").strip()
            if cleaned:
                items.append(cleaned)

    def append_file_lines(lines):
        for line in lines:
            cleaned = (line or "").strip()
            if cleaned:
                parsed_from_file.append(cleaned)

    def normalize_header(header: Optional[str]) -> str:
        if header is None:
            return ""
        return re.sub(r"[\s\-]+", "_", str(header).strip().lower())

    def looks_like_path_or_url(value: str) -> bool:
        lowered = value.strip().lower()
        return (
            lowered.startswith(("http://", "https://", "/", "./", "../")) or
            "\\" in lowered or
            bool(re.search(r"\.(jpg|jpeg|png|gif|bmp|mp4|avi|mov|webm|csv|json|txt)$", lowered))
        )

    def looks_like_text(value: Optional[str]) -> bool:
        if value is None:
            return False
        candidate = str(value).strip()
        if len(candidate) < 8:
            return False
        if looks_like_path_or_url(candidate):
            return False
        if candidate.replace(".", "", 1).isdigit():
            return False
        return bool(re.search(r"[\u4e00-\u9fffA-Za-z]", candidate))

    def serialize_row_mapping(mapping: dict) -> str:
        parts = []
        for raw_key, raw_value in mapping.items():
            key = normalize_header(raw_key)
            value = str(raw_value or "").strip()
            if not key or not value:
                continue
            if looks_like_path_or_url(value):
                continue
            if key in NON_TEXT_COLUMN_HINTS and not looks_like_text(value):
                continue
            parts.append(f"{key}: {value}")
        return "; ".join(parts)

    def parse_csv_texts(content: str) -> List[str]:
        sample = content[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        except csv.Error:
            dialect = csv.excel

        lines = content.splitlines()
        if not lines:
            return []

        parsed_items = []
        dict_reader = csv.DictReader(lines, dialect=dialect)
        fieldnames = [normalize_header(name) for name in (dict_reader.fieldnames or [])]
        has_meaningful_header = any(fieldnames)

        if has_meaningful_header:
            for row in dict_reader:
                if not row:
                    continue

                preferred_values = []
                fallback_values = []
                serialized_row = serialize_row_mapping(row)
                for raw_key, raw_value in row.items():
                    value = str(raw_value or "").strip()
                    if not value:
                        continue

                    key = normalize_header(raw_key)
                    if key in TEXT_COLUMN_HINTS or any(hint in key for hint in TEXT_COLUMN_HINTS):
                        if looks_like_text(value):
                            preferred_values.append(value)
                        continue

                    if key in NON_TEXT_COLUMN_HINTS or any(hint in key for hint in NON_TEXT_COLUMN_HINTS):
                        continue

                    if looks_like_text(value):
                        fallback_values.append(value)

                if preferred_values:
                    parsed_items.append(" ".join(preferred_values[:2]))
                elif serialized_row:
                    parsed_items.append(serialized_row)
                elif fallback_values:
                    parsed_items.append(max(fallback_values, key=len))

            if parsed_items:
                return parsed_items

        reader = csv.reader(lines, dialect=dialect)
        for row in reader:
            normalized_cells = [str(cell).strip() for cell in row if str(cell).strip()]
            if normalized_cells:
                parsed_items.append("; ".join(normalized_cells))
        return parsed_items

    if raw_text:
        append_lines(raw_text.splitlines())

    if file_content:
        suffix = os.path.splitext(filename or "")[1].lower()
        if suffix == ".json":
            data = json.loads(file_content)
            if isinstance(data, dict):
                data = data.get("items") or data.get("texts") or data.get("data") or []
            if not isinstance(data, list):
                raise HTTPException(status_code=400, detail="JSON 批量文件格式错误，应为数组或包含 items/texts/data 的对象")
            for item in data:
                if isinstance(item, str):
                    append_file_lines([item])
                elif isinstance(item, dict):
                    values = [
                        item.get("text"), item.get("content"), item.get("news"),
                        item.get("body"), item.get("title"), item.get("headline")
                    ]
                    preferred_value = next((value for value in values if looks_like_text(value)), "")
                    append_file_lines([preferred_value or serialize_row_mapping(item)])
        elif suffix == ".csv":
            append_file_lines(parse_csv_texts(file_content))
        else:
            append_file_lines(file_content.splitlines())

    append_lines(parsed_from_file)

    if file_content and not parsed_from_file:
        raise HTTPException(
            status_code=400,
            detail="上传的数据集文件中未解析出可检测文本，请检查 CSV/JSON/TXT 的文本列或内容"
        )

    deduped_items = [item for item in items if item]
    if len(deduped_items) > BATCH_MAX_ITEMS:
        raise HTTPException(status_code=400, detail=f"批量任务单次最多提交 {BATCH_MAX_ITEMS} 条新闻")

    return deduped_items


async def read_batch_file(batch_file: Optional[UploadFile]) -> Optional[str]:
    if not batch_file or not batch_file.filename:
        return None

    raw_bytes = await batch_file.read()
    for encoding in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise HTTPException(status_code=400, detail="批量文件编码无法识别，请使用 UTF-8/GBK")

# =========================================================================
# API 路由实现 (全面接入 MySQL 数据库)
# =========================================================================

# 1. 上传与检测接口 (核心双引擎分发入口)
@app.post("/upload_detect")
async def upload_detect(
    request: Request,
    text: Optional[str] = Form(None),
    model_type: str = Form("fast"), # 决定走哪个模型
    images: List[UploadFile] = File([]),
    video: Optional[UploadFile] = File(None),
    db: Session = Depends(get_db) 
):
    valid_images = [img for img in images if img.filename] if images else []
    ensure_engine_available(model_type, db)
    print(f"📡 收到多模态请求 | 模型: [{model_type.upper()}] | 文本: {bool(text)} | 图片: {len(valid_images)}张 | 视频: {bool(video and video.filename)}")
    try:
        return detect_single_news(
            request=request,
            db=db,
            model_type=model_type,
            text=text,
            images=valid_images,
            video=video
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ 推理系统崩溃: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="服务器模型计算失败")


@app.post("/upload_detect_batch")
async def upload_detect_batch(
    request: Request,
    texts: Optional[str] = Form(None),
    model_type: str = Form("fast"),
    batch_file: Optional[UploadFile] = File(None),
    images: List[UploadFile] = File([]),
    db: Session = Depends(get_db)
):
    ensure_engine_available(model_type, db)

    try:
        file_content = await read_batch_file(batch_file)
        text_items = parse_batch_texts(texts, file_content, batch_file.filename if batch_file else None)
        valid_images = [img for img in images if img and img.filename] if images else []

        if not text_items:
            raise HTTPException(status_code=400, detail="批量模式至少需要提供一条新闻文本")
        if len(valid_images) > len(text_items):
            raise HTTPException(status_code=400, detail="图片数量不能多于文本条数")

        print(f"📚 收到批量检测请求 | 模型: [{model_type.upper()}] | 文本条数: {len(text_items)} | 图片数: {len(valid_images)}")

        results = []
        fake_count = 0
        for idx, item_text in enumerate(text_items, start=1):
            item_title = f"[{model_type.upper()}] 批量新闻_{idx:02d}_{uuid.uuid4().hex[:6]}"
            paired_images = [valid_images[idx - 1]] if idx - 1 < len(valid_images) else None
            result = detect_single_news(
                request=request,
                db=db,
                model_type=model_type,
                text=item_text,
                images=paired_images,
                title_prefix=item_title
            )
            results.append(result)
            if result["isFake"]:
                fake_count += 1

        return {
            "total": len(results),
            "fakeCount": fake_count,
            "realCount": len(results) - fake_count,
            "parsedPreview": text_items[:5],
            "items": results,
            "modelUsed": model_type
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        print(f"❌ 批量推理系统崩溃: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail="服务器批量计算失败")

# 2. 登陆接口
@app.post("/login")
async def login(data: LoginSchema, db: Session = Depends(get_db)):
    # 🔥 从 MySQL 查询真实用户
    user = db.query(User).filter(User.username == data.username).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    if user.password != data.password:
        raise HTTPException(status_code=401, detail="密码错误")
    if user.status == 0:
        raise HTTPException(status_code=403, detail="该账号已被禁用，请联系管理员")

    return {
        "msg": "登录成功",
        "data": {
            "token": f"fake-jwt-{user.username}",
            "role": user.role,
            "username": user.username
        }
    }

# 3. 获取待审核任务 (审核员用)
@app.get("/tasks")
async def get_tasks(
    request: Request,
    role: str = Query("user"),           # 'user' 或 'auditor'
    page: int = Query(1, ge=1),          # 当前页码
    size: int = Query(10, ge=1, le=50),  # 每页数量
    status_filter: Optional[str] = None, # 用于审核员筛选 'PENDING' 或 'AUDITED'
    db: Session = Depends(get_db)
):
    query = build_task_query(db, role, status_filter)

    total_count = query.count()
    tasks = query.order_by(DetectTask.id.desc()).offset((page - 1) * size).limit(size).all()
    serialized_tasks = [serialize_task(task, request) for task in tasks]

    return {
        "code": 200,
        "data": {
            "total": total_count,
            "items": serialized_tasks
        }
    }


@app.get("/export/tasks")
async def export_tasks_csv(
    request: Request,
    role: str = Query("admin"),
    status_filter: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = build_task_query(db, role, status_filter)
    tasks = query.order_by(DetectTask.id.desc()).all()
    rows = []

    for task in tasks:
        serialized = serialize_task(task, request)
        rows.append(
            {
                "id": serialized["id"],
                "task_no": serialized["task_no"],
                "title": serialized["title"],
                "content": serialized["content"] or "",
                "media_urls": " | ".join(serialized["media_urls"]),
                "ai_score": serialized["ai_score"],
                "ai_reason": serialized["ai_reason"] or "",
                "saliency_urls": " | ".join(serialized["saliency_urls"]),
                "status": serialized["status"],
                "audit_result": serialized["audit_result"] or "",
                "audit_comment": serialized["audit_comment"] or "",
                "create_time": serialized["create_time"] or "",
            }
        )

    filename = f"tasks_{role.lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return make_csv_response(
        filename,
        rows,
        [
            "id",
            "task_no",
            "title",
            "content",
            "media_urls",
            "ai_score",
            "ai_reason",
            "saliency_urls",
            "status",
            "audit_result",
            "audit_comment",
            "create_time",
        ],
    )


@app.get("/export/users")
async def export_users_csv(db: Session = Depends(get_db)):
    users = db.query(User).order_by(User.id.desc()).all()
    rows = []
    for user in users:
        rows.append(
            {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "status": user.status,
                "nickname": user.nickname or "",
                "email": user.email or "",
                "gender": user.gender,
                "age": user.age or "",
                "note": user.note or "",
                "create_time": user.create_time.isoformat() if user.create_time else "",
            }
        )

    filename = f"users_admin_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return make_csv_response(
        filename,
        rows,
        ["id", "username", "role", "status", "nickname", "email", "gender", "age", "note", "create_time"],
    )

# B. 新增：用户专用的软删除 API
@app.put("/tasks/{task_id}/hide")
async def hide_task(task_id: int, db: Session = Depends(get_db)):
    task = db.query(DetectTask).filter(DetectTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.is_user_deleted = True # 打上物理不可见标记
    db.commit()

    return {"code": 200, "message": "Record soft deleted successfully"}

# 4. 提交人工审核结果 (Human-in-the-Loop)
@app.post("/audit_task")
async def audit_task(audit: AuditSchema, db: Session = Depends(get_db)):
    # 🔥 在 MySQL 中更新审核状态
    task = db.query(DetectTask).filter(DetectTask.id == audit.task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    task.status = 'audited'
    task.audit_result = audit.result
    task.audit_comment = audit.comment
    db.commit()
    return {"msg": "审核已提交，数据已进入训练集"}


@app.get("/tasks/{task_id}/messages")
async def get_review_messages(task_id: int, db: Session = Depends(get_db)):
    task = db.query(DetectTask).filter(DetectTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    messages = (
        db.query(ReviewMessage)
        .filter(ReviewMessage.task_id == task_id)
        .order_by(ReviewMessage.create_time.asc(), ReviewMessage.id.asc())
        .all()
    )

    return {
        "code": 200,
        "data": [serialize_review_message(message) for message in messages],
    }


@app.post("/tasks/{task_id}/messages")
async def create_review_message(
    task_id: int,
    payload: ReviewMessageSchema,
    db: Session = Depends(get_db),
):
    task = db.query(DetectTask).filter(DetectTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    sender_role = (payload.sender_role or "").strip().lower()
    if sender_role not in {"user", "auditor"}:
        raise HTTPException(status_code=400, detail="发送方角色错误")

    content = (payload.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="消息内容不能为空")
    if len(content) > 1000:
        raise HTTPException(status_code=400, detail="消息内容最多 1000 字")

    sender_name = (payload.sender_name or "").strip()[:50] or ("审核员" if sender_role == "auditor" else "用户")
    message = ReviewMessage(
        task_id=task_id,
        sender_role=sender_role,
        sender_name=sender_name,
        content=content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return {
        "code": 200,
        "data": serialize_review_message(message),
    }


@app.put("/tasks/{task_id}/presence")
async def update_review_presence(
    task_id: int,
    payload: ReviewPresenceSchema,
    db: Session = Depends(get_db),
):
    task = db.query(DetectTask).filter(DetectTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    role = (payload.role or "").strip().lower()
    if role not in {"user", "auditor"}:
        raise HTTPException(status_code=400, detail="在线角色错误")

    role_presence = REVIEW_PRESENCE.setdefault(task_id, {})
    role_presence[role] = {
        "name": (payload.name or "").strip()[:50] or ("审核员" if role == "auditor" else "用户"),
        "last_seen": time.time(),
    }

    return {
        "code": 200,
        "data": get_review_presence_snapshot(task_id),
    }


@app.get("/tasks/{task_id}/presence")
async def get_review_presence(task_id: int, db: Session = Depends(get_db)):
    task = db.query(DetectTask).filter(DetectTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "code": 200,
        "data": get_review_presence_snapshot(task_id),
    }


# 5. 系统监控数据 (管理员用)
@app.get("/monitor_stats")
async def get_stats(db: Session = Depends(get_db)):
    # 🔥 从 MySQL 获取真实的统计数据
    user_count = db.query(User).count()
    task_count = db.query(DetectTask).count()
    
    return {
        "gflops": round(10 + random.random() * 5, 1),
        "vram": round(4 + random.random() * 8, 1),
        "latency": int(30 + random.random() * 20),
        "user_count": user_count,
        "task_count": task_count
    }

# ================= 用户管理 CRUD 接口 (真实数据库操作) =================

# A. 获取所有用户列表
@app.get("/users")
async def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    res = []
    for u in users:
        res.append({
            "id": u.id,
            "username": u.username,
            "role": u.role,
            "status": u.status,
            "createTime": u.create_time.strftime("%Y-%m-%d %H:%M:%S") if getattr(u, 'create_time', None) else "",
            "note": u.note,
            "nickname": getattr(u, 'nickname', ''),
            "email": getattr(u, 'email', ''),
            "gender": getattr(u, 'gender', 0),
            "age": getattr(u, 'age', None)
        })
    return res

# B. 新增用户
@app.post("/users")
async def create_user(user: UserCreateSchema, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == user.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="用户名已存在")
    
    new_user = User(
        username=user.username,
        password=user.password, # 注意：工业级项目应存密文
        role=user.role,
        note=user.note,
        status=1,
        security_question=user.security_question,
        security_answer=normalize_security_answer(user.security_answer) if user.security_answer else None
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {"msg": "创建成功", "user": {"id": new_user.id, "username": new_user.username}}

# C. 修改用户状态 (封禁/解封)
@app.put("/users/{user_id}/status")
async def update_user_status(user_id: int, status_data: UserStatusSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户未找到")
    
    user.status = status_data.status
    db.commit()
    return {"msg": "状态已更新"}

# D. 删除用户
@app.delete("/users/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户未找到")
    
    db.delete(user)
    db.commit()
    return {"msg": "删除成功"}

# ================= 开放注册与验证码 API =================

# A. 获取验证码图片接口
@app.get("/captcha")
async def get_captcha():
    # 1. 生成 4 位随机字符 (大写字母+数字)
    text = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    print(f"🤫 [系统后门] 当前正确的验证码是: >>> {text} <<<")
    # 2. 给这个验证码发一个唯一的 ID (发票号)
    captcha_id = uuid.uuid4().hex
    CAPTCHA_STORE[captcha_id] = text # 后端悄悄记住
    
    # 3. 画成扭曲的图片并转成 Base64 编码，方便前端直接显示
    image = ImageCaptcha(width=120, height=40)
    data = image.generate(text)
    base64_img = base64.b64encode(data.getvalue()).decode("utf-8")
    
    return {
        "code": 200, 
        "data": {
            "captcha_id": captcha_id, 
            "image_base64": f"data:image/png;base64,{base64_img}"
        }
    }

# B. 开放注册接口
@app.post("/register")
async def register(data: RegisterSchema, db: Session = Depends(get_db)):
    # 1. 拦截防御：校验验证码
    correct_code = CAPTCHA_STORE.get(data.captcha_id)
    if not correct_code or correct_code.lower() != data.captcha_code.lower():
        raise HTTPException(status_code=400, detail="ACCESS DENIED / 验证码错误或已失效")
    
    # 校验通过后，立刻销毁这个验证码，防止被重复利用 (防暴刷)
    del CAPTCHA_STORE[data.captcha_id]

    # 2. 查重：检查用户名是否被抢注
    existing_user = db.query(User).filter(User.username == data.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="ID ALREADY TAKEN / 该用户名已被注册")
    
    # 3. 注册入库 (强制锁定 role 为普通 user)
    new_user = User(
        username=data.username,
        password=data.password, 
        role="user", 
        status=1,
        note="通过前端页面开放注册",
        security_question=data.security_question.strip(),
        security_answer=normalize_security_answer(data.security_answer)
    )
    db.add(new_user)
    db.commit()
    
    return {"code": 200, "message": "WELCOME TO THE MATRIX / 注册成功，请登录"}


@app.post("/password-recovery/question")
async def get_password_recovery_question(
    data: PasswordRecoveryQuestionSchema,
    db: Session = Depends(get_db)
):
    username = data.username.strip()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.status == 0:
        raise HTTPException(status_code=403, detail="该账号已被禁用，请联系管理员")
    if not user.security_question or not user.security_answer:
        raise HTTPException(status_code=400, detail="该账号未设置密保问题，无法找回密码")

    return {
        "code": 200,
        "data": {
            "username": user.username,
            "security_question": user.security_question
        }
    }


@app.post("/password-recovery/reset")
async def reset_password_by_security_question(
    data: PasswordRecoveryResetSchema,
    db: Session = Depends(get_db)
):
    username = data.username.strip()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.status == 0:
        raise HTTPException(status_code=403, detail="该账号已被禁用，请联系管理员")
    if not user.security_question or not user.security_answer:
        raise HTTPException(status_code=400, detail="该账号未设置密保问题，无法找回密码")
    if normalize_security_answer(data.security_answer) != normalize_security_answer(user.security_answer):
        raise HTTPException(status_code=400, detail="密保答案错误")
    if len(data.new_password.strip()) < 3:
        raise HTTPException(status_code=400, detail="新密码至少需要 3 位")

    user.password = data.new_password.strip()
    db.commit()

    return {"code": 200, "message": "密码重置成功，请使用新密码登录"}


class UserProfileSchema(BaseModel):
    username: str # 目前你的系统使用 username 作为身份标识，我们暂时用它来定位用户
    nickname: Optional[str] = None
    email: Optional[str] = None
    gender: Optional[int] = None
    age: Optional[int] = None

# ================= 个人信息 (Profile) 接口 =================

# A. 获取个人信息 (供前端回显)
@app.get("/user/profile")
async def get_user_profile(username: str, db: Session = Depends(get_db)):
    # 真实场景应该从 Token 提取，由于目前你的 token 是 fake-jwt-{username}，我们通过传参获取
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(status_code=404, detail="USER NOT FOUND / 用户不存在")
    
    return {
        "code": 200,
        "data": {
            "username": user.username,
            "role": user.role,
            "nickname": getattr(user, 'nickname', ''),
            "email": getattr(user, 'email', ''),
            "gender": getattr(user, 'gender', 0),
            "age": getattr(user, 'age', None),
        }
    }

# B. 修改个人信息
@app.put("/user/profile")
async def update_user_profile(profile_data: UserProfileSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == profile_data.username).first()
    if not user:
        raise HTTPException(status_code=404, detail="USER NOT FOUND / 用户不存在")
    
    # 动态更新有值的字段
    if profile_data.nickname is not None:
        user.nickname = profile_data.nickname
    if profile_data.email is not None:
        user.email = profile_data.email
    if profile_data.gender is not None:
        user.gender = profile_data.gender
    if profile_data.age is not None:
        user.age = profile_data.age
        
    db.commit()
    
    return {"code": 200, "message": "PROFILE UPDATED / 个人信息更新成功"}

# ================= 核心引擎状态管理 API =================

@app.get("/system/engine_status")
async def get_engine_status(db: Session = Depends(get_db)):
    """获取引警状态，如果数据库没有记录则初始化默认值"""
    # 查找 FAST 状态
    fast_record = db.query(SystemConfig).filter(SystemConfig.config_key == "engine_fast").first()
    if not fast_record:
        fast_record = SystemConfig(config_key="engine_fast", config_value="true", description="FAST 引擎开关")
        db.add(fast_record)
        
    # 查找 PRO 状态
    pro_record = db.query(SystemConfig).filter(SystemConfig.config_key == "engine_pro").first()
    if not pro_record:
        pro_record = SystemConfig(config_key="engine_pro", config_value="true", description="PRO(CMIE) 引擎开关")
        db.add(pro_record)
        
    db.commit() # 如果有新建记录，提交保存

    return {
        "code": 200,
        "data": {
            "fast": fast_record.config_value.lower() == "true",
            "pro": pro_record.config_value.lower() == "true"
        }
    }


@app.put("/system/engine_status")
async def update_engine_status(payload: EngineStatusSchema, db: Session = Depends(get_db)):
    """Admin 控制台更新引擎状态，直接落库"""
    if payload.engine not in ["fast", "pro"]:
        raise HTTPException(status_code=400, detail="未知的引擎类型 / UNKNOWN ENGINE")
    
    config_key = f"engine_{payload.engine}"
    record = db.query(SystemConfig).filter(SystemConfig.config_key == config_key).first()
    
    # 更新落库
    new_value = "true" if payload.status else "false"
    if record:
        record.config_value = new_value
    else:
        # 理论上走不到这里，以防万一
        new_record = SystemConfig(config_key=config_key, config_value=new_value)
        db.add(new_record)
        
    db.commit()
    
    status_text = "ONLINE" if payload.status else "OFFLINE"
    print(f"⚠️ [SYSTEM OVERRIDE] {payload.engine.upper()} 引擎已被 Admin 固化为: {status_text}")
    
    return {
        "code": 200, 
        "message": f"{payload.engine.upper()} 引擎状态已固化为 {status_text}"
    }

if __name__ == "__main__":
    import uvicorn
    # 启动服务，端口 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
