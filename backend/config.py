import os

class Settings:
    APP_NAME: str = "WeChat Binding Demo"
    SECRET_KEY: str = "super_secret_key_for_wechatbot_demo"
    DATABASE_URL: str = "sqlite:///./wechat_demo.db"
    WECHAT_CREDENTIALS_DIR: str = "./wechat_creds"

settings = Settings()

# 确保凭证目录存在
os.makedirs(settings.WECHAT_CREDENTIALS_DIR, exist_ok=True)
