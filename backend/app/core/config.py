

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Vuno Trader API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    app_allowed_origins: str = Field(default="http://localhost:3000", alias="APP_ALLOWED_ORIGINS")
    app_trusted_hosts: str = Field(
        default="localhost,127.0.0.1,vunotrader-api.onrender.com,.onrender.com",
        alias="APP_TRUSTED_HOSTS"
    )

    supabase_url: str = Field(alias="SUPABASE_URL")
    supabase_anon_key: str = Field(alias="SUPABASE_ANON_KEY")
    supabase_service_role_key: str = Field(alias="SUPABASE_SERVICE_ROLE_KEY")

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.app_allowed_origins.split(",") if origin.strip()]

    @property
    def trusted_hosts(self) -> list[str]:
        return [host.strip() for host in self.app_trusted_hosts.split(",") if host.strip()]


def get_settings() -> Settings:
    return Settings()