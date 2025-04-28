from utils.custom_logger import CustomLogger

from fastapi import APIRouter, Request, Response
from starlette.responses import JSONResponse

from pymongo.errors import PyMongoError

from services.auth_service import AuthService

from models.request import UserRequest

router = APIRouter()

@router.post("/register")
async def register(user: UserRequest):
    try:
        result = AuthService()._register(user)
        CustomLogger()._get_logger().info(f"Register successful for user \"{user.username}\"")

        return JSONResponse(
            content={"message": "User created successfully"},
            status_code=201
        )

    except Exception as e:
        CustomLogger()._get_logger().error(f"Failed to register user: {e.args[0]}")
        if e.__class__ == PyMongoError:
            return JSONResponse(
                content={"message": "Can not operate database transaction"},
                status_code=500
            )
        elif e.args[0] == "Username already exists":
            return JSONResponse(
                content={"message": "Failed to create user", "detail": e.args[0]},
                status_code=409
            )
        else:
            return JSONResponse(
                content={"message": "Internal server error ", "detail": e.args[0]},
                status_code=500
            )

@router.patch("/login")
async def login(user: UserRequest, response: Response):
    try:
        session_token, refresh_token = AuthService()._authenticate(user)
        CustomLogger()._get_logger().info(f"Login successful for user \"{user.username}\": session token \"{session_token}\" - refresh token \"{refresh_token}\"")

        response = JSONResponse(
            content={"message": "Login successful"},
            status_code=200
        )
        response = AuthService()._add_session_to_cookie(response, session_token, refresh_token)
        
        return response

    except Exception as e:
        CustomLogger()._get_logger().error(f"Failed to login for user \"{user.username}\": {e.args[0]}")
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
        
@router.patch("/refresh")
async def refresh(request: Request, response: Response):
    input_refresh_token = request.cookies.get("refresh_token")
    if not input_refresh_token:
        CustomLogger()._get_logger().warning(f"Missing refresh token for user \"{request.state.user_id}\"")
        return JSONResponse(
            content={"message": "Unauthorized: Missing refresh token"},
            status_code=401
        )

    try:
        new_session_token = AuthService()._refresh_session(response, input_refresh_token)

        if new_session_token:
            CustomLogger()._get_logger().info(f"Refresh successful for user \"{request.state.user_id}\": new session token \"{new_session_token}\"")
            response = JSONResponse(
                content={"message": "Refresh successful"},
                status_code=200
            )
            return response
        
        else:
            CustomLogger()._get_logger().error(f"Failed to refresh token for user \"{request.state.user_id}\"")
            return JSONResponse(
                content={"message": "Failed to refresh session"},
                status_code=500
            )
    
    except Exception as e:
        CustomLogger()._get_logger().error(f"Failed to refresh token for user \"{request.state.user_id}\": {e.args[0]}")
        return JSONResponse(
            content={"message": "Internal server error ", "detail": e.args[0]},
            status_code=500
        )

@router.patch("/logout")
async def logout(request: Request, response: Response):
    session_token = request.cookies.get("session_token")
    refresh_token = request.cookies.get("refresh_token")

    if not session_token and not refresh_token:
        CustomLogger()._get_logger().warning(f"Missing session token or refresh token for user \"{request.state.user_id}\"")
        return JSONResponse(
            content={"message": "Unauthorized: Missing session token or refresh token"},
            status_code=401
        )

    try:
        result = AuthService()._delete_session(session_token, refresh_token)
        if result:
            CustomLogger()._get_logger().info(f"Logout successful for user \"{request.state.user_id}\"")
            response = JSONResponse(
                content={"message": "Logout successful"},
                status_code=200
            )
            response = AuthService()._del_session_in_cookie(response)

            return response
        else:
            CustomLogger()._get_logger().error(f"Failed to logout user \"{request.state.user_id}\"")
            return JSONResponse(
                content={"message": "Failed to delete session"},
                status_code=500
            )
    
    except Exception as e:
        CustomLogger()._get_logger().error(f"Failed to logout user \"{request.state.user_id}\": {e.args[0]}")
        return JSONResponse(
            content={"message": "Internal server error ", "detail": e.args[0]},
            status_code=500
        )

