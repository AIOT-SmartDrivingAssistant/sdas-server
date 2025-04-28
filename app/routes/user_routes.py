from utils.custom_logger import CustomLogger

from fastapi import APIRouter, Request, Depends, File, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse

from services.user_service import UserService

from models.request import UserInfoRequest

router = APIRouter()

def get_user_id(request: Request) -> str: 
    return request.state.user_id

@router.get("/")
async def get_user_info(uid = Depends(get_user_id)):
    try:
        user_data = UserService()._get_user_info(uid)

        CustomLogger()._get_logger().info(f"Retrieve successfully user info: {user_data}")

        return JSONResponse(
            content=user_data,
            status_code=200,
            media_type="application/json"
        )
            
        
    except Exception as e:
        CustomLogger()._get_logger().error(f"Failed to get user info: {e.args[0]}")
        if e.args[0] == "User not find":
            return JSONResponse(
                content={"message": e.args[0], "detail": "Can not find any document with the uid that extracted from cookie's session"},
                status_code=404
            )
        elif e.args[0] == "Invalid string to ObjectId conversion":
            return JSONResponse(
                content={"message":  e.args[0], "detail": "Can not extract uid from request's cookie's session"},
                status_code=500
            )
        else:
            return JSONResponse(
                content={"message":  "Internal server error ", "detail": e.args[0]},
                status_code=500
            )
    
@router.patch("/")
async def update_user_info(user_info_request: UserInfoRequest, uid = Depends(get_user_id)):
    try:
        UserService()._update_user_info(uid, user_info_request)
        CustomLogger()._get_logger().info(f"Update successfully user info with request: {user_info_request}")

        return JSONResponse(
            content={"message": "User info updated successfully"},
            status_code=200,
            media_type="application/json"
        )
    
    except Exception as e:
        CustomLogger()._get_logger().error(f"Failed to update user info: {e.args[0]}")
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
                content={"message":  "Internal server error ", "detail": e.args[0]},
                status_code=500
            )
    
@router.delete("/")
async def delete_user_info(uid = Depends(get_user_id)):
    try:
        UserService()._delete_user_account(uid)
        CustomLogger()._get_logger().info(f"Delete successfully user info with uid: \"{uid}\"")
        
        response = JSONResponse(
            content={},
            status_code=204
        )
        response.delete_cookie("session_id")
        return response
    
    except Exception as e:
        CustomLogger()._get_logger().error(f"Failed to delete user info: {e.args[0]}")
        return JSONResponse(
            content={"message": "Internal server error ", "detail": e.args[0]},
            status_code=500
        )
        
@router.get("/avatar")
async def get_user_avatar(uid = Depends(get_user_id)):
    try:
        file = UserService()._get_avatar(uid)
        CustomLogger()._get_logger().info(f"Retrieve successfully user avatar: {file}")
        return StreamingResponse(file, media_type=file.content_type)

    except Exception as e:
        CustomLogger()._get_logger().error(f"Failed to get user avatar: {e.args[0]}")
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
async def update_user_avatar(file: UploadFile = File(...), uid = Depends(get_user_id)):
    try:
        result = await UserService()._update_avatar(uid, file)
        CustomLogger()._get_logger().info(f"Update successfully user avatar: {result}")
        
        return JSONResponse(
            content={"message": "User avatar updated successfully"},
            status_code=200,
            media_type="application/json"
        )

    except Exception as e:
        CustomLogger()._get_logger().error(f"Failed to update user avatar: {e.args[0]}")
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
async def delete_user_avatar(uid = Depends(get_user_id)):
    try:
        UserService()._delete_avatar(uid)
        CustomLogger()._get_logger().info(f"Delete successfully user avatar: {uid}")

        return JSONResponse(
            content={"message": "User avatar deleted successfully"},
            status_code=200,
            media_type="application/json"
        )

    except Exception as e:
        CustomLogger()._get_logger().error(f"Failed to delete user avatar: {e.args[0]}")
        if e.args[0] == "User not find":
            return JSONResponse(
                content={"message": e.args[0], "detail": "Can not find any document with the uid that extracted from cookie's session"},
                status_code=404
            )
        return JSONResponse(
            content={"message": "Internal server error ", "detail": e.args[0]},
            status_code=500
        )
