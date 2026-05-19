# database.py 
import os
import datetime
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON , Boolean, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "change_me_db_password")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "zhixin_future")
DB_UNIX_SOCKET = os.getenv("DB_UNIX_SOCKET", "").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
DB_ECHO = os.getenv("DB_ECHO", "false").strip().lower() == "true"


def build_database_url() -> str:
    if DATABASE_URL:
        return DATABASE_URL

    escaped_password = urllib.parse.quote_plus(DB_PASSWORD)
    if DB_UNIX_SOCKET:
        escaped_socket = urllib.parse.quote_plus(DB_UNIX_SOCKET)
        return (
            f"mysql+pymysql://{DB_USER}:{escaped_password}@localhost/{DB_NAME}"
            f"?unix_socket={escaped_socket}&charset=utf8mb4"
        )

    return (
        f"mysql+pymysql://{DB_USER}:{escaped_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
        "?charset=utf8mb4"
    )


SQLALCHEMY_DATABASE_URL = build_database_url()

engine = create_engine(SQLALCHEMY_DATABASE_URL, echo=DB_ECHO, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ================= 数据库表结构定义 =================

# 1. 用户信息表
class User(Base):
    __tablename__ = "sys_user"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, comment="登录账号")
    password = Column(String(255), nullable=False, comment="登录密码")
    role = Column(String(20), default="user", comment="角色权限: admin/auditor/user")
    status = Column(Integer, default=1, comment="状态: 1正常, 0停用")
    note = Column(String(255), nullable=True, comment="备注")
    create_time = Column(DateTime, default=datetime.datetime.now, comment="注册时间")
    nickname = Column(String(50), nullable=True, comment="昵称")
    email = Column(String(100), nullable=True, comment = "邮箱")
    gender = Column(Integer, default=0, comment = "性别")
    age = Column(Integer, nullable=True , comment = "年龄")
    security_question = Column(String(255), nullable=True, comment="密保问题")
    security_answer = Column(String(255), nullable=True, comment="密保答案")

# 2. 多模态新闻检测任务表
class DetectTask(Base):
    __tablename__ = "detect_task"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_no = Column(String(64), nullable=False, comment="任务流水号")
    title = Column(String(128), nullable=False, comment="任务标题")
    content = Column(Text, nullable=True, comment="文本模态内容")
    media_urls = Column(JSON, nullable=True, comment="多媒体文件路径集合(数组)")
    ai_score = Column(Float, default=0.0, comment="AI伪造概率得分")
    ai_reason = Column(Text, nullable=True, comment="AI判定理由")
    saliency_urls = Column(JSON, nullable=True, comment="伪影显著性图URLs")
    status = Column(String(20), default="pending", comment="状态: pending待审/audited已审")
    create_time = Column(DateTime, default=datetime.datetime.now, comment="任务提交时间")
    audit_result = Column(String(50), nullable=True)     # 或者你用的 String 长度
    audit_comment = Column(String(255), nullable=True)   # 审查员的备注
    is_user_deleted = Column(Boolean, default=False)


# 3. 审核沟通消息表
class ReviewMessage(Base):
    __tablename__ = "review_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("detect_task.id"), nullable=False, index=True, comment="关联检测任务")
    sender_role = Column(String(20), nullable=False, comment="发送方角色: user/auditor")
    sender_name = Column(String(50), nullable=True, comment="发送方显示名")
    content = Column(Text, nullable=False, comment="消息内容")
    create_time = Column(DateTime, default=datetime.datetime.now, comment="发送时间")


# 3. 多模态引擎信息表
class SystemConfig(Base):
    __tablename__ = "system_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(50), unique=True, index=True, nullable=False) # 例如 'engine_fast', 'engine_pro'
    config_value = Column(String(255), nullable=False)                       # 例如 'true', 'false'
    description = Column(String(255), nullable=True)

# ================= 魔法时刻 =================
# 自动在数据库中建表（如果表不存在的话）
Base.metadata.create_all(bind=engine)


def ensure_user_security_columns():
    inspector = inspect(engine)
    existing_columns = {column["name"] for column in inspector.get_columns("sys_user")}
    alter_statements = {
        "security_question": """
            ALTER TABLE sys_user
            ADD COLUMN security_question VARCHAR(255) NULL COMMENT '密保问题'
        """,
        "security_answer": """
            ALTER TABLE sys_user
            ADD COLUMN security_answer VARCHAR(255) NULL COMMENT '密保答案'
        """
    }

    with engine.begin() as connection:
        for column_name, ddl in alter_statements.items():
            if column_name not in existing_columns:
                connection.execute(text(ddl))


ensure_user_security_columns()

# 依赖注入：供 FastAPI 的路由使用
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
