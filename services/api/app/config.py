from pydantic_settings import BaseSettings, SettingsConfigDict


def resolve_ai_provider(*, provider: str, api_key: str, openai_api_key: str = "") -> str:
    if not (api_key or openai_api_key or "").strip():
        return "heuristic"
    name = (provider or "").strip().lower()
    if name in {"", "heuristic"}:
        return "openai"
    return name


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env", "../../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite+aiosqlite:///./orqelis.db"
    redis_url: str = ""
    environment: str = "development"
    auto_migrate: bool = True

    jwt_secret: str = "change-me-to-a-long-random-string"
    jwt_expire_minutes: int = 60 * 24 * 7
    encryption_key: str = ""
    cookie_secure: bool = False

    api_host: str = "127.0.0.1"
    api_port: int = 8000
    cors_origins: str = "http://localhost:3000,http://localhost:3001"
    app_base_url: str = "http://localhost:3000"
    admin_base_url: str = "http://localhost:3001"
    public_api_url: str = ""
    next_public_api_url: str = ""

    rate_limit_per_minute: int = 120
    auth_rate_limit_per_minute: int = 20

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = "Orqelis <noreply@localhost>"
    email_backend: str = "log"

    ai_provider: str = "heuristic"
    ai_api_key: str = ""
    ai_base_url: str = ""
    ai_model: str = ""
    openai_api_key: str = ""

    founder_email: str = ""
    founder_password: str = ""

    @property
    def is_development(self) -> bool:
        return self.environment.lower() in {"development", "dev", "local", "test"}

    @property
    def resolved_cookie_secure(self) -> bool:
        if self.cookie_secure:
            return True
        if not self.is_development:
            return True
        return (self.app_base_url or "").startswith("https://")

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [item.strip() for item in self.cors_origins.split(",") if item.strip()]
        extra = [(self.app_base_url or "").rstrip("/"), (self.admin_base_url or "").rstrip("/")]
        for item in extra:
            if item and item not in origins:
                origins.append(item)
        return origins

    @property
    def resolved_public_api_url(self) -> str:
        return (
            (self.public_api_url or "").strip()
            or (self.next_public_api_url or "").strip()
            or f"http://{self.api_host}:{self.api_port}"
        )

    @property
    def resolved_ai_key(self) -> str:
        return (self.ai_api_key or self.openai_api_key or "").strip()

    @property
    def resolved_ai_provider(self) -> str:
        return resolve_ai_provider(
            provider=self.ai_provider,
            api_key=self.ai_api_key,
            openai_api_key=self.openai_api_key,
        )


settings = Settings()
