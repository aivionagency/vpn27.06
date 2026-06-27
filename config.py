from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    bot_token: str = "placeholder_token"
    database_url: str = "sqlite+aiosqlite:///vpnbot.db"
    bot_username: str = "your_vpn_bot"
    support_chat_id: int = 0
    admin_ids: List[int] = []
    tribute_topup_url: str = "https://tribute.example/placeholder"
    trial_days: int = 3
    referral_reward: int = 50
    referral_bonus: int = 30
    proxy_url: str = ""

    # Tribute payments
    tribute_api_key: str = ""  # also used as HMAC secret to verify trbt-signature
    webhook_host: str = "127.0.0.1"
    webhook_port: int = 8080
    webhook_path: str = "/webhook/tribute"
    topup_min_rub: int = 1
    topup_max_rub: int = 100000

    # Admin dashboard (served on the same host/port as the webhook)
    dashboard_token: str = "default_secure_token_change_me"  # MUST BE SET, /dashboard requires ?token=... to open

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

config = Settings()
