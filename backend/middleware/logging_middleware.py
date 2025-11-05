"""Request/response logging middleware with correlation IDs."""

from __future__ import annotations

import time
import uuid
from typing import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from core.logger import bind_contextvars, clear_contextvars, get_logger


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that records inbound requests and outbound responses."""

    async def dispatch(  # type: ignore[override]
        self,
        request: Request,
        call_next: Callable[[Request], Response],
    ) -> Response:
        request_id = str(uuid.uuid4())
        bind_contextvars(request_id=request_id)
        access_logger = get_logger("access")
        start_time = time.perf_counter()

        access_logger.info(
            "request.started",
            method=request.method,
            path=str(request.url.path),
            client_ip=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)
        except Exception as exc:  # pragma: no cover - defensive logging
            duration_ms = (time.perf_counter() - start_time) * 1000
            access_logger.exception(
                "request.failed",
                method=request.method,
                path=str(request.url.path),
                duration_ms=duration_ms,
            )
            clear_contextvars()
            raise exc

        duration_ms = (time.perf_counter() - start_time) * 1000
        access_logger.info(
            "request.completed",
            method=request.method,
            path=str(request.url.path),
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )

        response.headers["X-Request-ID"] = request_id
        clear_contextvars()
        return response

