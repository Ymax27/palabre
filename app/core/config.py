from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Palabre"
    database_url: str = "postgresql+asyncpg://palabre:palabre@localhost:5432/palabre"
    valkey_url: str = "redis://localhost:6379/0"
    secret_key: str = "must-be-set-locally"
    debug: bool = False


settings = Settings()
