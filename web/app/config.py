from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:////app/data/nmapctf.db"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "changeme-in-production"
    scanner_api_token: str = "changeme"
    access_token_expire_minutes: int = 60

    model_config = {"env_file": ".env"}


settings = Settings()
