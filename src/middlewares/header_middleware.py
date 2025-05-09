import os
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
        cors_headers = {
            "Access-Control-Allow-Origin": allowed_origins,
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Requested-With, Accept",
            "Access-Control-Expose-Headers": "Set-Cookie"
        }
        if request.method == "OPTIONS":
            # Preflight request: return headers immediately
            return Response(status_code=204, headers=cors_headers)
        
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        for k, v in cors_headers.items():
            response.headers[k] = v
        return response