from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Palabre"
    database_url: str = "postgresql+asyncpg://palabre:palabre@localhost:5432/palabre"
    valkey_url: str = "redis://localhost:6379/0"
    secret_key: str = "must-be-set-locally"
    debug: bool = False
    app_base_url: str = "http://localhost:8000"
    magic_link_ttl_seconds: int = 900
    smtp_host: str = "localhost"
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "palabre@localhost"
    session_cookie_name: str = "palabre_session"
    github_client_id: str = ""
    github_client_secret: str = ""


settings = Settings()
