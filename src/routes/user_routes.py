from utils.custom_logger import CustomLogger

from fastapi import APIRouter, Request, Depends, File, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.user_service import UserService

from models.request import UserInfoRequest

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

def get_user_id(request: Request) -> str: 
    return request.state.user_id

@router.get("/")
@limiter.limit("20/minute")
async def get_user_info(request: Request, uid: str = Depends(get_user_id)):
    try:
        user_data = UserService()._get_user_info(uid)
        CustomLogger()._get_logger().info(f"Get user_data SUCCESS: {{ userId: \"{uid}\" }}")

        return JSONResponse(
            content=user_data,
            status_code=200,
            media_type="application/json"
        )
            
        
    except Exception as e:
        CustomLogger()._get_logger().warning(f"Get user_data FAIL: {{ userId: \"{uid}\" }} {e.args[0]}")
        if e.args[0] == "User not found":
            return JSONResponse(
                content={"message": e.args[0], "detail": "Can not find any with current session"},
                status_code=404
            )
        elif e.args[0] == "Invalid string to ObjectId conversion":
            return JSONResponse(
                content={"message": e.args[0], "detail": "Can not extract uid from request's cookie's session"},
                status_code=500
            )
        else:
            return JSONResponse(
                content={"message": "Internal server error ", "detail": e.args[0]},
                status_code=500
            )
    
@router.patch("/")
@limiter.limit("20/minute")
async def update_user_info(request: Request, user_info_request: UserInfoRequest, uid: str = Depends(get_user_id)):
    try:
        UserService()._update_user_info(uid, user_info_request)
        CustomLogger()._get_logger().info(f"Update user_data SUCCESS: {{ userId: \"{uid}\", data: {user_info_request} }}")

        return JSONResponse(
            content={"message": "Update user_data success"},
            status_code=200,
            media_type="application/json"
        )
    
    except Exception as e:
        CustomLogger()._get_logger().warning(f"Update user_data FAIL: {{ userId: \"{uid}\"}} {e.args[0]}")
        if e.args[0] == "No data to update":
            return JSONResponse(
                content={"message": e.args[0], "detail": "Request contain no data to update"},
                status_code=422
            )
        elif e.args[0] == "No user info updated":
            return JSONResponse(
                content={"message": e.args[0], "detail": "Can not find any document with the uid that extracted from cookie's session"},
                status_code=404
            )
        else:
            return JSONResponse(
                content={"message": "Internal server error ", "detail": e.args[0]},
                status_code=500
            )
    
@router.delete("/")
@limiter.limit("20/minute")
async def delete_user_info(request: Request, uid: str = Depends(get_user_id)):
    try:
        UserService()._delete_user_account(uid)
        CustomLogger()._get_logger().info(f"Delete user SUCCESS: {{ userId: \"{uid}\" }}")
        
        response = JSONResponse(
            content={},
            status_code=204
        )
        response.delete_cookie("session_id")
        return response
    
    except Exception as e:
        CustomLogger()._get_logger().warning(f"Delete user FAIL: {{ userId: \"{uid}\" }} {e.args[0]}")
        return JSONResponse(
            content={"message": "Internal server error ", "detail": e.args[0]},
            status_code=500
        )
        
@router.get("/avatar")
@limiter.limit("20/minute")
async def get_user_avatar(request: Request, uid: str = Depends(get_user_id)):
    try:
        file = UserService()._get_avatar(uid)
        CustomLogger()._get_logger().info(f"Get user_avatar SUCCESS: {{ userId: \"{uid}\", data: {file}}}")

        return StreamingResponse(file, media_type=file.content_type)

    except Exception as e:
        CustomLogger()._get_logger().warning(f"Get user_avatar FAIL: {{ userId: \"{uid}\"}} {e.args[0]}")
        if e.args[0] == "User not find":
            return JSONResponse(
                content={"message": e.args[0], "detail": "Can not find any document with the uid that extracted from cookie's session"},
                status_code=404
            )
        elif e.args[0] == "No avatar found":
            return JSONResponse(
                content={"message": e.args[0], "detail": "Can not find any document with the uid that extracted from cookie's session"},
                status_code=404
            )
        return JSONResponse(
            content={"message": "Internal server error ", "detail": e.args[0]},
            status_code=500
        )

@router.put("/avatar")
@limiter.limit("20/minute")
async def update_user_avatar(request: Request, file: UploadFile = File(...), uid: str = Depends(get_user_id)):
    try:
        result = await UserService()._update_avatar(uid, file)
        CustomLogger()._get_logger().info(f"Update user_avatar SUCCESS: {{ userId: \"{uid}\", result: {result}}}")
        
        return JSONResponse(
            content={"message": "Update user_avatar success"},
            status_code=200,
            media_type="application/json"
        )

    except Exception as e:
        CustomLogger()._get_logger().warning(f"Update user_avatar FAIL: {{ userId: \"{uid}\"}} {e.args[0]}")
        if e.args[0] == "User not find":
            return JSONResponse(
                content={"message": e.args[0], "detail": "Can not find any document with the uid that extracted from cookie's session"},
                status_code=404
            )
        return JSONResponse(
            content={"message": "Internal server error ", "detail": e.args[0]},
            status_code=500
        )

@router.delete("/avatar")
@limiter.limit("20/minute")
async def delete_user_avatar(request: Request, uid: str = Depends(get_user_id)):
    try:
        UserService()._delete_avatar(uid)
        CustomLogger()._get_logger().info(f"Delete user_avatar SUCCESS: {{ userId: \"{uid}\" }}")

        return JSONResponse(
            content={"message": "Delete user_avatar success"},
            status_code=200,
            media_type="application/json"
        )

    except Exception as e:
        CustomLogger()._get_logger().warning(f"Delete user_avatar FAIL: {{ userId: \"{uid}\" }} {e.args[0]}")
        if e.args[0] == "User not find":
            return JSONResponse(
                content={"message": e.args[0], "detail": "Can not find any document with the uid that extracted from cookie's session"},
                status_code=404
            )
        return JSONResponse(
            content={"message": "Internal server error ", "detail": e.args[0]},
            status_code=500
        )
