from utils.custom_logger import CustomLogger

from fastapi import APIRouter, Depends, Request, Response
from starlette.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from pymongo.errors import PyMongoError

from services.auth_service import AuthService

from models.request import UserRequest

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

@router.post("/register")
@limiter.limit("20/minute")
async def register(request: Request, user: UserRequest):
    try:
        AuthService()._register(user)
        CustomLogger()._get_logger().info(f"Register SUCCESS: {{ username: \"{user.username}\"}}")

        return JSONResponse(
            content={"message": "Register success"},
            status_code=201
        )

    except Exception as e:
        CustomLogger()._get_logger().warning(f"Register FAIL: {e.args[0]}")
        if e.__class__ == PyMongoError:
            return JSONResponse(
                content={"message": "Database error", "detail": e.args[0]},
                status_code=500
            )
        elif e.args[0] == "Username already exists":
            return JSONResponse(
                content={"message": "Register fail", "detail": e.args[0]},
                status_code=409
            )
        else:
            return JSONResponse(
                content={"message": "Internal server error ", "detail": e.args[0]},
                status_code=500
            )

@router.post("/login")
@limiter.limit("20/minute")
async def login(request: Request, response: Response, user: UserRequest):
    try:
        userId, (session_token, refresh_token) = AuthService()._authenticate(user)
        CustomLogger()._get_logger().info(f"Login SUCCESS: {{ userId: \"{userId}\" }}")

        response = JSONResponse(
            content={"message": "Login successful"},
            status_code=200
        )
        response = AuthService()._add_session_to_cookie(response, session_token, refresh_token)
        
        return response

    except Exception as e:
        CustomLogger()._get_logger().warning(f"Login FAIL: \"{user.username}\" {e.args[0]}")
        if e.args[0] == "Invalid credentials":
            return JSONResponse(
                content={"message": e.args[0], "detail": "Invalid username or password"},
                status_code=401
            )
        else:
            return JSONResponse(
                content={"message": "Internal server error ", "detail": e.args[0]},
                status_code=500
            )

def get_user_id(request: Request) -> str: 
    return request.state.user_id

@router.patch("/refresh")
@limiter.limit("20/minute")
async def refresh(request: Request, response: Response):
    input_refresh_token = request.cookies.get("refresh_token")
    if not input_refresh_token:
        CustomLogger()._get_logger().warning("Missing refresh token")
        return JSONResponse(
            content={"message": "Unauthorized", "detail": "Missing refresh token"},
            status_code=401
        )

    try:
        user_id, new_session_token = AuthService()._refresh_session(response, input_refresh_token)

        if new_session_token:
            CustomLogger()._get_logger().info(f"Refresh SUCCESS: {{ userId: \"{user_id}\" }}")
            
            response = JSONResponse(
                content={"message": "Refresh success"},
                status_code=200
            )
            response = AuthService()._add_session_to_cookie(response, new_session_token, input_refresh_token)
            return response
        
        else:
            CustomLogger()._get_logger().warning("Refresh FAIL: refresh token not found")
            return JSONResponse(
                content={"message": "Refresh fail"},
                status_code=500
            )
    
    except Exception as e:
        CustomLogger()._get_logger().warning(f"Refresh FAIL: {e.args[0]}")
        return JSONResponse(
            content={"message": "Internal server error ", "detail": e.args[0]},
            status_code=500
        )

@router.post("/logout")
@limiter.limit("20/minute")
async def logout(request: Request, response: Response, uid: str = Depends(get_user_id)):
    session_token = request.cookies.get("session_token")
    refresh_token = request.cookies.get("refresh_token")

    if  not refresh_token:
        CustomLogger()._get_logger().warning(f"Missing refresh token: {{ userId: \"{uid}\" }}")
        return JSONResponse(
            content={"message": "Bad request", "detail": "Missing refresh token"},
            status_code=422
        )

    try:
        result = AuthService()._delete_session(session_token, refresh_token)
        if result:
            CustomLogger()._get_logger().info(f"Logout SUCCESS: {{ userId: \"{uid}\" }}")
            response = JSONResponse(
                content={"message": "Logout success"},
                status_code=200
            )
            response = AuthService()._del_session_in_cookie(response)

            return response
        else:
            CustomLogger()._get_logger().warning(f"Logout FAIL: {{ userId: \"{uid}\" }} fail to delete token")
            return JSONResponse(
                content={"message": "Database error", "detail": "Fail to delete token"},
                status_code=500
            )
    
    except Exception as e:
        CustomLogger()._get_logger().warning(f"Logout FAIL: {{ userId: \"{uid}\" }} {e.args[0]}")
        return JSONResponse(
            content={"message": "Internal server error ", "detail": e.args[0]},
            status_code=500
        )

