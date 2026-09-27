"""Security middleware: headers and CORS configuration."""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "0",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'",
    "Cache-Control": "no-store",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Injects standard security headers on every response.

    HSTS is only added when running behind TLS (production).
    """

    def __init__(self, app: object, *, enable_hsts: bool = False) -> None:
        super().__init__(app)  # type: ignore[arg-type]
        self._enable_hsts = enable_hsts

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value
        if self._enable_hsts:
            response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
        return response


class CORSConfig:
    """CORS configuration container passed to ``CORSMiddleware``."""

    def __init__(self, *, allow_origins: list[str] | None = None) -> None:
        self.allow_origins: list[str] = allow_origins or []
        self.allow_credentials: bool = True
        self.allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers: list[str] = ["Authorization", "Content-Type", "X-Request-ID"]
        self.expose_headers: list[str] = ["X-Request-ID"]


def cors_config(*, allow_origins: list[str] | None = None) -> CORSConfig:
    """Return a config object for ``CORSMiddleware``.

    Defaults to no origins allowed (API-only). Pass explicit origins for
    the frontend domain in production.
    """
    return CORSConfig(allow_origins=allow_origins)
