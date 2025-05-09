from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from typing import List

class NotFoundMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, routes: List[str]):
        super().__init__(app)
        self.routes = routes

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path not in self.routes:
            return JSONResponse(
                content={
                    "message": "Not Found",
                    "detail": "The requested resource was not found."
                },
                status_code=404
            )
        response = await call_next(request)
        return response