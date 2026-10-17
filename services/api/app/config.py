from pydantic_settings import BaseSettings, SettingsConfigDict


def resolve_ai_provider(
    *,
    provider: str,
    api_key: str,
    openai_api_key: str = "",
    gemini_api_key: str = "",
    openrouter_api_key: str = "",
    nvidia_api_key: str = "",
) -> str:
    if not any(
        (key or "").strip()
        for key in (api_key, openai_api_key, gemini_api_key, openrouter_api_key, nvidia_api_key)
    ):
        return "heuristic"
    name = (provider or "").strip().lower()
    if name in {"", "heuristic"}:
        if (nvidia_api_key or "").strip():
            return "nvidia"
        if (openai_api_key or "").strip() or (api_key or "").strip():
            return "openai"
        if (openrouter_api_key or "").strip():
            return "openrouter"
        return "gemini"
    return name


def resolve_ai_key(
    *,
    provider: str,
    api_key: str,
    openai_api_key: str = "",
    gemini_api_key: str = "",
    openrouter_api_key: str = "",
    nvidia_api_key: str = "",
) -> str:
    configured_key = (api_key or "").strip()
    openai_key = (openai_api_key or "").strip()
    provider_name = (provider or "").strip().lower()
    if provider_name == "openai" and openai_key:
        return openai_key
    if provider_name == "gemini" and (gemini_api_key or "").strip():
        return gemini_api_key.strip()
    if provider_name == "nvidia":
        return (nvidia_api_key or "").strip() or configured_key
    if provider_name == "openrouter":
        return (openrouter_api_key or "").strip()
    return configured_key or openai_key


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
    ai_model_light: str = ""
    ai_model_heavy: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    openrouter_api_key: str = ""
    nvidia_api_key: str = ""

    scanner_docker_image: str = "orqelis-scanner:latest"
    scanner_mode: str = "local"  # local (Option A) | remote (Option B) | mock | docker
    scanner_service_url: str = ""
    scanner_internal_token: str = ""
    scanner_enable_ffuf: bool = False
    scanner_enable_wapiti: bool = False
    scan_timeout_total_s: int = 600
    # Free allowance for orgs without an active plan; paid tiers are in app/quotas.py
    scan_quota_per_org_monthly: int = 3
    web_asset_quota_free: int = 1
    # Mock scanner only: seconds per simulated tool step so progress is observable
    scanner_mock_step_delay_s: float = 0.0
    dns_verify_rate_limit_seconds: int = 30
    # When true (tests / local), verify accepts matching token without live DNS
    dns_verify_stub: bool = False

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    next_public_supabase_url: str = ""
    next_public_supabase_anon_key: str = ""

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
        configured_url = (self.public_api_url or "").strip() or (self.next_public_api_url or "").strip()
        if configured_url:
            return configured_url
        if not self.is_development:
            return "https://orqelis-api-production.up.railway.app"
        return f"http://{self.api_host}:{self.api_port}"

    @property
    def resolved_ai_key(self) -> str:
        return resolve_ai_key(
            provider=self.resolved_ai_provider,
            api_key=self.ai_api_key,
            openai_api_key=self.openai_api_key,
            gemini_api_key=self.gemini_api_key,
            openrouter_api_key=self.openrouter_api_key,
            nvidia_api_key=self.nvidia_api_key,
        )

    @property
    def resolved_ai_provider(self) -> str:
        return resolve_ai_provider(
            provider=self.ai_provider,
            api_key=self.ai_api_key,
            openai_api_key=self.openai_api_key,
            gemini_api_key=self.gemini_api_key,
            openrouter_api_key=self.openrouter_api_key,
            nvidia_api_key=self.nvidia_api_key,
        )

    @property
    def resolved_ai_fallback_provider(self) -> str:
        if self.resolved_ai_provider == "nvidia":
            if self.openrouter_api_key.strip():
                return "openrouter"
            if self.openai_api_key.strip():
                return "openai"
            if self.gemini_api_key.strip():
                return "gemini"
        if self.resolved_ai_provider == "openai" and self.gemini_api_key.strip():
            return "gemini"
        if self.resolved_ai_provider == "openai" and self.openrouter_api_key.strip():
            return "openrouter"
        if self.resolved_ai_provider == "gemini" and self.openai_api_key.strip():
            return "openai"
        if self.resolved_ai_provider == "openrouter":
            if self.openai_api_key.strip():
                return "openai"
            if self.gemini_api_key.strip():
                return "gemini"
        return ""

    @property
    def resolved_ai_fallback_key(self) -> str:
        if self.resolved_ai_fallback_provider == "openrouter":
            return self.openrouter_api_key.strip()
        if self.resolved_ai_fallback_provider == "nvidia":
            return self.nvidia_api_key.strip()
        if self.resolved_ai_fallback_provider == "gemini":
            return self.gemini_api_key.strip()
        if self.resolved_ai_fallback_provider == "openai":
            return self.openai_api_key.strip()
        if self.resolved_ai_fallback_provider == "openrouter":
            return self.openrouter_api_key.strip()
        return ""


settings = Settings()
