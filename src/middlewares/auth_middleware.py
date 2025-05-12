from utils.custom_logger import CustomLogger

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from services.auth_service import AuthService

class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.whitelist = ["/auth/register", "/auth/login", "/auth/refresh"]
        self.auth_service = AuthService()

    async def dispatch(self, request: Request, call_next):
        # Skip authentication for whitelisted paths
        if request.url.path in self.whitelist:
            return await call_next(request)
        
        elif request.url.path == "/":
            return JSONResponse(
                content={"message": "Welcome to the SDAS API!"},
                status_code=200
            )

        # Check for session token in cookies
        session_token = request.cookies.get("session_token")
        if not session_token:
            CustomLogger()._get_logger().warning(f"Missing session token: [{request.url.path}]")
            return JSONResponse(
                content={"message": "Unauthorized", "detail": "Missing session token"},
                status_code=401
            )

        user_id = self.auth_service._validate_session(session_token)
        
        if not user_id:
            CustomLogger()._get_logger().warning(f"Invalid/expired session token: [{request.url.path}]")
            return JSONResponse(
                content={"message": "Unauthorized", "detail": "Invalid or expired session token"},
                status_code=401
            )

        # CustomLogger()._get_logger().info(f"Request: {{url: [{request.url.path}], session: \"{session_token}\", userId: \"{user_id}\"}}")

        request.state.user_id = str(user_id)

        return await call_next(request)