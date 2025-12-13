from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # Application
    app_name: str = "Reach"
    app_version: str = "0.2.0"
    app_host: str = "0.0.0.0"
    app_port: int = 8001

    # Database
    database_url: str

    # Data Collection
    data_update_interval_hours: int = 24
    max_retry_attempts: int = 3

    # Logging
    log_level: str = "INFO"

    # API Keys - Korean Market Only
    dart_api_key: str = ""  # DART (전자공시) API 키

    class Config:
        # 프로젝트 루트의 .env 파일 절대경로 지정
        env_file = str(Path(__file__).parent.parent / ".env")
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """설정 인스턴스 반환 (싱글톤)"""
    return Settings()