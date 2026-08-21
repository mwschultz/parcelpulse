import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pythonjsonlogger.json import JsonFormatter
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.rate_limit import limiter
from app.routes.api import router as api_router

_handler = logging.StreamHandler()
_handler.setFormatter(JsonFormatter(
    fmt="%(asctime)s %(name)s %(levelname)s %(message)s"
))
_app_logger = logging.getLogger("app")
_app_logger.setLevel(logging.INFO)
_app_logger.addHandler(_handler)
_app_logger.propagate = False

logger = logging.getLogger(__name__)


class CatchUnhandledMiddleware(BaseHTTPMiddleware):
    """Turn unhandled exceptions into a JSON 500 that still carries CORS headers.

    Starlette's own ServerErrorMiddleware sits *outside* CORSMiddleware, so an
    exception reaching it produces a bare text/plain 500 with no
    Access-Control-Allow-Origin — which browsers then report as a CORS error
    rather than the server error it actually is. Catching here, inside CORS,
    means the response travels back out through CORSMiddleware and gets its
    headers. Registration order below is load-bearing.
    """

    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as e:
            logger.error(
                "Unhandled error on %s: %s", request.url.path, type(e).__name__
            )
            return JSONResponse(
                status_code=500, content={"detail": "Internal server error"}
            )


app = FastAPI(title="ParcelPulse API", version="0.1.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Added first, so it ends up *inside* CORSMiddleware. add_middleware prepends,
# making the last-added middleware outermost; CORS must stay outermost so it
# can attach headers to whatever CatchUnhandledMiddleware returns.
app.add_middleware(CatchUnhandledMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}
