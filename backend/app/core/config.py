from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Admin 管理后台"
    debug: bool = True

    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440

    # 开发用 SQLite，生产通过环境变量 / .env 切换为 MySQL 等
    database_url: str = "sqlite:///./admin.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
