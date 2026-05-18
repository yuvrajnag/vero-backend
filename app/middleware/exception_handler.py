from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import settings
from app.utils.logger import logger
import traceback


def _cors_headers_for_request(request: Request) -> dict[str, str]:
    """Ensure error responses still pass browser CORS checks."""
    origin = request.headers.get("origin")
    if not origin:
        return {}
    if settings.DEBUG or settings.ENVIRONMENT == "development":
        return {"Access-Control-Allow-Origin": origin, "Vary": "Origin"}
    if origin in settings.CORS_ORIGINS:
        return {"Access-Control-Allow-Origin": origin, "Vary": "Origin"}
    return {}


def add_exception_handlers(app: FastAPI):
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(f"HTTP error occurred: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=_cors_headers_for_request(request),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled exception: {exc}")
        logger.error(traceback.format_exc())
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
            headers=_cors_headers_for_request(request),
        )
