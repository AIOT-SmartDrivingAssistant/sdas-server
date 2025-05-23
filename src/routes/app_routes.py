from utils.custom_logger import CustomLogger

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from services.app_service import AppService
from models.request import SensorDataRequest

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

def get_user_id(request: Request) -> str: 
    return request.state.user_id

@router.get("/events")
@limiter.limit("20/minute")
async def notification_stream(request: Request, uid: str = Depends(get_user_id)):
    """Stream notifications to the client via SSE."""
    CustomLogger()._get_logger().info(f"SSE connect SUCCESS: {{ userId: \"{uid}\" }}")
    try:
        return await AppService()._get_notification_stream(uid)
    except Exception as e:
        CustomLogger()._get_logger().warning(f"SSE connect FAIL: {{ userId: \"{uid}\" }} {e.args[0]}")
        return JSONResponse(
            content={"message": "Internal server error ", "detail": str(e.args[0])},
            status_code=500
        )

@router.get('/sensor_data')
async def get_sensor_data(
    request: Request,
    sensor_types: str,  # Receive as comma-separated string
    uid: str = Depends(get_user_id)
):
    if not sensor_types:
        CustomLogger()._get_logger().warning(f"Get sensor_data FAIL: {{ userId: \"{uid}\"}} sensor_types is empty")
        return JSONResponse(
            content={"message": "Bad request", "detail": "sensor_types is empty"},
            status_code=422
        )
    
    try:
        # Split the comma-separated string and create the request object
        sensor_types_list = [s.strip() for s in sensor_types.split(',')]
        request = SensorDataRequest(sensor_types=sensor_types_list)
        
        data = AppService()._get_sensors_data(uid, request)

        sensor_types_str = ', '.join(request.sensor_types)
        CustomLogger()._get_logger().info(f"Get sensor_data SUCCESS: {{ userId: \"{uid}\", sensor_types: \"{sensor_types_str}\" }}")

        return JSONResponse(
            content=data,
            status_code=200
        )
    except Exception as e:
        CustomLogger()._get_logger().warning(f"Get sensor_data FAIL: {{ userId: \"{uid}\"}} {e.args[0]}")
        return JSONResponse(
            content={"message": "Internal server error ", "detail": str(e.args[0])},
            status_code=500
        )

@router.get("/services_status")
@limiter.limit("20/minute")
async def get_services_status(request: Request, uid = Depends(get_user_id)):
    """
    Endpoint to get all services config information includes status and value.
    """
    try:
        service_config_data = AppService()._get_services_status(uid)
        CustomLogger()._get_logger().info(f"Get services_status SUCCESS: {{ userId: \"{uid}\", result: {service_config_data} }}")

        return JSONResponse(
            content=service_config_data,
            status_code=200,
            media_type="application/json"
        )
        
    except Exception as e:
        CustomLogger()._get_logger().warning(f"Get services_status FAIL: {{ userId: \"{uid}\" }} {e.args[0]}")
        if e.args[0] == "Service config not find":
            return JSONResponse(
                content={"message": e.args[0], "detail": "Can not find any document with the uid that extracted from cookie's session"},
                status_code=404
            )
        else:
            return JSONResponse(
                content={"message": "Internal server error ", "detail": e.args[0]},
                status_code=500
            )
    
@router.get("/action_history")
@limiter.limit("20/minute")
async def get_all_action_history(request: Request, uid = Depends(get_user_id)):
    try:
        data = AppService()._get_all_action_history(uid)
        CustomLogger()._get_logger().info(f"Get all action_history SUCCESS: {{ userId: \"{uid}\" }}")

        return JSONResponse(
            content=data,
            status_code=200
        )
    
    except Exception as e:
        CustomLogger()._get_logger().warning(f"Get all action_history FAIL: {{ userId: \"{uid}\" }} {e.args[0]}")
        return JSONResponse(
            content={"message": "Internal server error ", "detail": e.args[0]},
            status_code=500
        )
    
@router.post("/mock_notification")
async def send_mock_notification(uid = Depends(get_user_id)):
    try:
        await AppService()._add_notification(uid, {
            "service_type": "mock_service",
            "notification": "Mock notification",
            "timestamp": "2025-05-07 22:15:22"
        })
        CustomLogger()._get_logger().info(f"Send mock notification SUCCESS: {{ userId: \"{uid}\" }}")
    except Exception as e:
        CustomLogger()._get_logger().warning(f"Send mock notification FAIL: {{ userId: \"{uid}\" }} {e.args[0]}")

@router.get("/all_sensor_data")
@limiter.limit("20/minute")
async def get_all_sensor_data(request: Request, uid: str = Depends(get_user_id)):
    """
    Endpoint to get all sensor data for a specific user.
    """
    try:
        data = AppService()._get_all_sensor_data(uid)
        CustomLogger()._get_logger().info(f"Get all sensor_data SUCCESS: {{ userId: \"{uid}\" }}")
        return JSONResponse(
            content=data,
            status_code=200
        )
    except Exception as e:
        CustomLogger()._get_logger().warning(f"Get all sensor_data FAIL: {{ userId: \"{uid}\" }} {e.args[0]}")
        return JSONResponse(
            content={"message": "Internal server error", "detail": str(e.args[0])},
            status_code=500
        )