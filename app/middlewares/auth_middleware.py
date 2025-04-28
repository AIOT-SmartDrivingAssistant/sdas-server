from utils.custom_logger import CustomLogger

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from services.auth_service import AuthService

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.whitelist = ["/auth/register", "/auth/login"]
        self.auth_service = AuthService()

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for whitelisted paths
        if request.url.path in self.whitelist:
            CustomLogger()._get_logger().info(f"Skip authentication for request [{request.url.path}]")
            return await call_next(request)
        
        elif request.method == "OPTIONS":
            CustomLogger()._get_logger().info(f"Accept preflight for request [{request.url.path}]")
            return await call_next(request)

        # Check for session token in cookies
        session_token = request.cookies.get("session_token")
        if not session_token:
            CustomLogger()._get_logger().warning(f"Missing session token for request [{request.url.path}]")
            return JSONResponse(
                content={"detail": "Unauthorized: Missing session token"},
                status_code=401
            )

        user_id = self.auth_service._validate_session(session_token)
        
        if not user_id:
            CustomLogger()._get_logger().warning(f"Invalid or expired session token for request [{request.url.path}]")
            return JSONResponse(
                content={"detail": "Unauthorized: Invalid or expired session token"},
                status_code=401
            )

        CustomLogger()._get_logger().info(f"Request [{request.url.path}] authenticated with session token \"{session_token}\" for user \"{user_id}\"")

        request.state.user_id = str(user_id)

        return await call_next(request)