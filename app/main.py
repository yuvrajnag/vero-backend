from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.database import init_db
from app.routes import (
    auth_routes,
    technician_routes,
    company_routes,
    portfolio_routes,
    job_routes,
    availability_routes,
    review_routes,
    notification_routes,
    payment_routes,
    admin_routes,
    analytics_routes,
    upload_routes,
)
from app.routes import ai_routes, negotiation_routes, explain_routes
from app.routes import vector_routes
from app.routes import auto_assign_routes
from app.middleware.exception_handler import add_exception_handlers
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.admin_seed import seed_admin_user
from sqlmodel import Session

from app.core.database import engine
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up application...")
    init_db()
    logger.info("Database initialized.")

    if settings.GOOGLE_CLIENT_ID:
        logger.info("Google OAuth configured (client id set).")
    else:
        logger.warning(
            "GOOGLE_CLIENT_ID is not set — POST /auth/google will return 503 until configured."
        )

    with Session(engine) as session:
        seed_admin_user(session)

    # ── Start embedding queue background worker ────────────────────────
    from app.services.vector.embedding_queue import start_worker
    start_worker()
    logger.info("Embedding queue worker started.")

    yield
    logger.info("Shutting down application...")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS (added last so it wraps all responses, including errors) ───────
_dev_mode = settings.DEBUG or settings.ENVIRONMENT == "development"
if _dev_mode:
    # Permissive dev CORS — auth uses Bearer headers, not cookies
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    _cors_allow_all = "*" in settings.CORS_ORIGINS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if _cors_allow_all else settings.CORS_ORIGINS,
        allow_credentials=not _cors_allow_all,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# ── Rate limiting ─────────────────────────────────────────────────────
app.add_middleware(RateLimitMiddleware)

# ── Exception Handlers ────────────────────────────────────────────────
add_exception_handlers(app)

# ── Routers ───────────────────────────────────────────────────────────
app.include_router(auth_routes.router)
app.include_router(technician_routes.router)
app.include_router(company_routes.router)
app.include_router(portfolio_routes.router)
app.include_router(job_routes.router)
app.include_router(availability_routes.router)
app.include_router(review_routes.router)
app.include_router(notification_routes.router)
app.include_router(payment_routes.router)
app.include_router(negotiation_routes.router)
app.include_router(ai_routes.router)
app.include_router(explain_routes.router)
app.include_router(admin_routes.router)
app.include_router(analytics_routes.router)
app.include_router(vector_routes.router)
app.include_router(auto_assign_routes.router)
app.include_router(upload_routes.router)

# ── Local uploads (GET only — POST uses /api/uploads) ─────────────────
_upload_root = Path(settings.UPLOAD_DIR)
_upload_root.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(_upload_root)), name="uploads")


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint"""
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
