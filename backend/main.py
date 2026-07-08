from typing import Optional
from fastapi import FastAPI, APIRouter, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from backend.database import get_db, engine, Base
from backend.models import WechatBinding, WechatBindingStatus
from backend.schemas import (
    WechatBindInitiateResponse,
    WechatBindStatusResponse,
    WechatBindingResponse,
    WechatUnbindResponse,
    WechatSendTestRequest,
    WechatSendTestResponse,
)
from backend.services import WechatService

# 初始化 SQLite 表结构
Base.metadata.create_all(bind=engine)

app = FastAPI(title="WeChat Binding Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi import Header

class MockUser:
    def __init__(self, user_id: int):
        self.id = user_id
        self.username = f"user_{user_id}"

def get_current_user(x_user_id: int = Header(default=1)) -> MockUser:
    return MockUser(user_id=x_user_id)

def get_wechat_service(db: Session = Depends(get_db)) -> WechatService:
    return WechatService(db)

router = APIRouter(prefix="/api/wechat", tags=["wechat"])

@router.post("/bind", response_model=WechatBindInitiateResponse)
async def initiate_bind(
    current_user: MockUser = Depends(get_current_user),
    service: WechatService = Depends(get_wechat_service),
):
    """发起绑定，返回 mock 的绑定二维码"""
    try:
        return service.initiate_binding(current_user.id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发起绑定失败: {str(e)}",
        )

@router.get("/bind/{binding_id}/status", response_model=WechatBindStatusResponse)
async def get_bind_status(
    binding_id: int,
    current_user: MockUser = Depends(get_current_user),
    service: WechatService = Depends(get_wechat_service),
):
    """轮询指定绑定流程的状态"""
    result = await service.get_binding_status(binding_id, current_user.id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="绑定记录不存在",
        )
    return result

@router.get("/bind/status", response_model=Optional[WechatBindingResponse])
def get_current_bind_status(
    current_user: MockUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取当前用户的微信绑定状态"""
    binding = (
        db.query(WechatBinding)
        .filter(
            WechatBinding.user_id == current_user.id,
            WechatBinding.status == WechatBindingStatus.BOUND,
        )
        .order_by(WechatBinding.created_at.desc())
        .first()
    )
    if not binding:
        return None
    return binding

@router.delete("/bind", response_model=WechatUnbindResponse)
async def unbind(
    current_user: MockUser = Depends(get_current_user),
    service: WechatService = Depends(get_wechat_service),
):
    """解绑微信"""
    service.unbind(current_user.id)
    return WechatUnbindResponse(message="微信解绑成功")

@router.post("/send-test", response_model=WechatSendTestResponse)
async def send_test(
    req: WechatSendTestRequest,
    current_user: MockUser = Depends(get_current_user),
    service: WechatService = Depends(get_wechat_service),
):
    """发送测试微信消息"""
    try:
        result = await service.async_send_notification(current_user.id, req.message)
        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result.get("message", "发送失败"),
            )
        return WechatSendTestResponse(success=True, message=result.get("message", "发送成功"))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"发送失败: {str(e)}",
        )

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
