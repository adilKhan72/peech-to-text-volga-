from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str = "change-me"
    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "sqlite:///./storage/jobs.db"
    storage_dir: str = "./storage/audio"
    whisper_model_size: str = "base"
    whisper_device: str = "cpu"
    whisper_compute_type: str = "int8"
    long_audio_threshold_seconds: int = 600
    rate_limit: str = "20/minute"


settings = Settings()
