import os
import json
import asyncio
import logging
from typing import Optional
from sqlalchemy.orm import Session
from cryptography.fernet import Fernet

from backend.config import settings
from backend.models import WechatBinding, WechatBindingStatus
from backend.schemas import WechatBindInitiateResponse, WechatBindStatusResponse

logger = logging.getLogger(__name__)

# 使用共享的内存字典模拟 Redis 存储 context_token
# key: f"wechat:ctx:{account_id}:{wechat_user_id}" -> value: token
_redis_mock_db: dict[str, str] = {}

_active_bots: dict[int, tuple] = {}

# ── Fernet 加解密 ──────────────────────────────────────────
_fernet_key = Fernet.generate_key()
_fernet = Fernet(_fernet_key)

def _encrypt_token(token: str) -> str:
    return _fernet.encrypt(token.encode("utf-8")).decode("utf-8")

def _decrypt_token(encrypted: str) -> str:
    return _fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")

def _ctx_redis_key(account_id: str, wechat_user_id: str) -> str:
    return f"wechat:ctx:{account_id}:{wechat_user_id}"

# 真正的 wechatbot 微信端机器人连接
from wechatbot import WeChatBot



class WechatService:
    def __init__(self, db: Session):
        self.db = db

    def initiate_binding(self, user_id: int) -> WechatBindInitiateResponse:
        # 清理旧的未完成的绑定
        old_bindings = (
            self.db.query(WechatBinding)
            .filter(
                WechatBinding.user_id == user_id,
                WechatBinding.status.in_([WechatBindingStatus.PENDING, WechatBindingStatus.SCANNED])
            )
            .all()
        )
        for ob in old_bindings:
            ob.status = WechatBindingStatus.FAILED
        self.db.commit()

        binding = WechatBinding(
            user_id=user_id,
            status=WechatBindingStatus.PENDING,
        )
        self.db.add(binding)
        self.db.commit()
        self.db.refresh(binding)

        asyncio.create_task(self._qr_login_loop(binding.id, user_id))

        return WechatBindInitiateResponse(
            binding_id=binding.id,
            qr_url="",
            status=binding.status.value,
        )

    async def get_binding_status(self, binding_id: int, user_id: int) -> Optional[WechatBindStatusResponse]:
        binding = (
            self.db.query(WechatBinding)
            .filter(WechatBinding.id == binding_id, WechatBinding.user_id == user_id)
            .first()
        )
        if not binding:
            return None

        has_context = False
        if binding.status == WechatBindingStatus.BOUND and binding.account_id and binding.wechat_user_id:
            key = _ctx_redis_key(binding.account_id, binding.wechat_user_id)
            if key in _redis_mock_db:
                has_context = True

        return WechatBindStatusResponse(
            binding_id=binding.id,
            status=binding.status.value,
            qr_url=binding.qr_url,
            wechat_nickname=binding.wechat_nickname,
            has_context=has_context,
        )

    def unbind(self, user_id: int) -> bool:
        binding = self.get_user_binding(user_id)
        if not binding:
            return False

        # 清除内存 mock redis 的 token
        if binding.account_id and binding.wechat_user_id:
            key = _ctx_redis_key(binding.account_id, binding.wechat_user_id)
            _redis_mock_db.pop(key, None)

        # 停止常驻 Bot
        entry = _active_bots.pop(user_id, None)
        if entry:
            bot, task = entry
            try:
                bot.stop()
            except Exception:
                pass
            if task and not task.done():
                task.cancel()

        binding.status = WechatBindingStatus.UNBOUND
        binding.encrypted_token = None
        binding.base_url = None
        binding.account_id = None
        binding.wechat_user_id = None
        binding.wechat_nickname = None
        self.db.commit()
        return True

    def get_user_binding(self, user_id: int) -> Optional[WechatBinding]:
        return (
            self.db.query(WechatBinding)
            .filter(
                WechatBinding.user_id == user_id,
                WechatBinding.status == WechatBindingStatus.BOUND,
            )
            .first()
        )

    async def async_send_notification(self, user_id: int, message: str) -> dict:
        binding = self.get_user_binding(user_id)
        if not binding:
            raise ValueError("用户未绑定微信或凭证不完整")

        target_user_id = binding.wechat_user_id
        if not target_user_id:
            raise ValueError("绑定记录缺少目标用户 ID")

        # 检查是否给 Bot 确认打过招呼
        key = _ctx_redis_key(binding.account_id, binding.wechat_user_id)
        if key not in _redis_mock_db:
            return {
                "success": False,
                "message": '请先给机器人发送一条消息（如"你好"），之后即可接收通知',
            }

        # 获取活跃 Bot 实例并发送
        entry = _active_bots.get(user_id)
        if entry:
            bot, _ = entry
            if bot:
                await bot.send(target_user_id, message)
                return {"success": True, "message": "消息发送成功"}

        return {"success": False, "message": "Bot 服务未在线"}

    async def _qr_login_loop(self, binding_id: int, user_id: int):
        db = None
        try:
            from backend.database import SessionLocal
            db = SessionLocal()

            cred_dir = os.path.join(settings.WECHAT_CREDENTIALS_DIR, f"user_{user_id}")
            os.makedirs(cred_dir, exist_ok=True)
            cred_path = os.path.join(cred_dir, "credentials.json")

            def on_qr_url(url: str):
                binding = db.query(WechatBinding).filter(WechatBinding.id == binding_id).first()
                if binding:
                    binding.qr_url = url
                    binding.status = WechatBindingStatus.PENDING
                    db.commit()

            def on_scanned():
                binding = db.query(WechatBinding).filter(WechatBinding.id == binding_id).first()
                if binding:
                    binding.status = WechatBindingStatus.SCANNED
                    db.commit()

            # 使用真实的 WeChatBot，并挂载相关回调
            bot = WeChatBot(
                cred_path=cred_path,
                on_qr_url=on_qr_url,
                on_scanned=on_scanned,
            )

            creds = await bot.login()
            encrypted = _encrypt_token(creds.token)

            binding = db.query(WechatBinding).filter(WechatBinding.id == binding_id).first()
            if binding:
                binding.status = WechatBindingStatus.BOUND
                binding.encrypted_token = encrypted
                binding.base_url = creds.base_url
                binding.account_id = creds.account_id
                binding.wechat_user_id = creds.user_id
                binding.wechat_nickname = "微信已绑定"
                binding.qr_url = None
                db.commit()

            # 注册消息监听器来保存 context_token
            @bot.on_message
            async def on_msg(msg):
                if msg._context_token:
                    key = _ctx_redis_key(creds.account_id, msg.user_id)
                    _redis_mock_db[key] = msg._context_token
                    logger.info(f"User {user_id} message received. Context stored.")

            # 启动长连接 bot 常驻任务
            task = asyncio.create_task(bot.start())
            _active_bots[user_id] = (bot, task)

        except Exception as e:
            logger.exception(f"Login failed: {e}")
            if db:
                binding = db.query(WechatBinding).filter(WechatBinding.id == binding_id).first()
                if binding:
                    binding.status = WechatBindingStatus.FAILED
                    db.commit()
        finally:
            if db:
                db.close()
