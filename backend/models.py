from sqlalchemy import Column, Integer, String, DateTime, Text, Enum
from sqlalchemy.sql import func
import enum
from backend.database import Base

class WechatBindingStatus(str, enum.Enum):
    PENDING = "pending"          # 等待扫码
    SCANNED = "scanned"          # 已扫码，等待确认
    BOUND = "bound"              # 绑定成功
    EXPIRED = "expired"          # QR 过期
    FAILED = "failed"            # 绑定失败
    UNBOUND = "unbound"          # 已解绑

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)

class WechatBinding(Base):
    __tablename__ = "wechat_bindings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    status = Column(Enum(WechatBindingStatus), default=WechatBindingStatus.PENDING)

    # 二维码信息
    qr_url = Column(Text, nullable=True)

    # 微信绑定后的参数（加解密暂且用明文或简单 Fernet 简化）
    encrypted_token = Column(Text, nullable=True)
    base_url = Column(String(255), nullable=True)
    account_id = Column(String(100), nullable=True)
    wechat_user_id = Column(String(100), nullable=True)
    wechat_nickname = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
