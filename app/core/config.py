import json
from typing import Annotated, Any, List
from pydantic import BeforeValidator
from pydantic_settings import BaseSettings, NoDecode

DEFAULT_CORS_ORIGINS: List[str] = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def _parse_cors_origins(value: Any) -> List[str]:
    if value is None:
        return DEFAULT_CORS_ORIGINS.copy()
    if isinstance(value, list):
        return [str(origin).strip() for origin in value if str(origin).strip()]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return DEFAULT_CORS_ORIGINS.copy()
        if raw.startswith("["):
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                raise ValueError("CORS_ORIGINS JSON must be an array")
            return [str(origin).strip() for origin in parsed if str(origin).strip()]
        return [part.strip() for part in raw.split(",") if part.strip()]
    raise ValueError(value)


CorsOrigins = Annotated[List[str], NoDecode, BeforeValidator(_parse_cors_origins)]


class Settings(BaseSettings):
    APP_NAME: str = "AI Technician Selection & Negotiation System"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    HOST: str = "0.0.0.0"
    PORT: int = 8000

    DATABASE_URL: str
    SUPABASE_URL: str | None = None
    SUPABASE_ANON_KEY: str | None = None
    SUPABASE_SERVICE_ROLE_KEY: str | None = None

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    GOOGLE_CLIENT_ID: str | None = None

    CORS_ORIGINS: CorsOrigins = DEFAULT_CORS_ORIGINS

    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024
    SUPABASE_STORAGE_BUCKET: str = "vero-uploads"

    REDIS_URL: str | None = None

    # ── Vector / Embedding settings ───────────────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    VECTOR_CACHE_TTL: int = 86400       # 24 h — technician/job embedding TTL
    SEARCH_CACHE_TTL: int = 300         # 5 min — ANN result cache TTL
    EMBEDDING_QUEUE_KEY: str = "embedding_rebuild_queue"
    VECTOR_TOP_K: int = 100             # default ANN candidates
    HNSW_EF_SEARCH: int = 64           # pgvector runtime ef_search

    ADMIN_EMAIL: str | None = None
    ADMIN_PASSWORD: str | None = None

    # ── Vapi (AI voice calling) ───────────────────────────────────────
    VAPI_API_KEY: str | None = None
    VAPI_ASSISTANT_ID: str | None = None     # Optional: pre-built assistant UUID from Vapi dashboard
    VAPI_PHONE_NUMBER_ID: str | None = None   # UUID from Vapi dashboard → Phone Numbers (NOT the raw number!)
    VAPI_WEBHOOK_SECRET: str | None = None    # Optional secret to verify webhook source
    PUBLIC_BASE_URL: str = "http://localhost:8000"  # Override with your deployed URL!
    TEST_PHONE_OVERRIDE: str | None = None    # DEV ONLY: route all calls to this number

    # ── Twilio (WhatsApp Messaging) ───────────────────────────────────
    TWILIO_ACCOUNT_SID: str | None = None
    TWILIO_AUTH_TOKEN: str | None = None
    TWILIO_WHATSAPP_NUMBER: str | None = None # e.g. "whatsapp:+14155238886" (Sandbox number)

    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
