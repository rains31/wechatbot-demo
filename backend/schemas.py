from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class WechatBindingResponse(BaseModel):
    id: int
    user_id: int
    status: str
    qr_url: Optional[str] = None
    account_id: Optional[str] = None
    wechat_user_id: Optional[str] = None
    wechat_nickname: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class WechatBindInitiateResponse(BaseModel):
    binding_id: int
    qr_url: str
    status: str

class WechatBindStatusResponse(BaseModel):
    binding_id: int
    status: str
    qr_url: Optional[str] = None
    wechat_nickname: Optional[str] = None
    has_context: bool = False

class WechatUnbindResponse(BaseModel):
    message: str = "微信解绑成功"

class WechatSendTestRequest(BaseModel):
    message: str = "这是一条来自 Wechatbot-Demo 的测试消息 🚀"

class WechatSendTestResponse(BaseModel):
    success: bool
    message: str
