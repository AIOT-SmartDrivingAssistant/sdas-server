from utils.custom_logger import CustomLogger

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from services.app_service import AppService
from models.request import ActionHistoryRequest, SensorDataRequest

router = APIRouter()

def get_user_id(request: Request) -> str: 
    return request.state.user_id

@router.get("/events")
async def notification_stream(uid: str = Depends(get_user_id)):
    """Stream notifications to the client via SSE."""
    CustomLogger()._get_logger().info(f"Client \"{uid}\" connected to SSE stream")
    try:
        return await AppService()._get_notification_stream(uid)
    except Exception as e:
        CustomLogger()._get_logger().error(f"Failed to get notification stream: {e.args[0]}")
        return JSONResponse(
            content={"message": "Internal server error ", "detail": str(e.args[0])},
            status_code=500
        )

@router.get('/sensor_data')
async def get_sensor_data(
    sensor_types: str,  # Receive as comma-separated string
    uid: str = Depends(get_user_id)
):
    if not sensor_types:
        CustomLogger()._get_logger().info("No sensor types provided")
        return JSONResponse(content=[], status_code=200)
    
    try:
        # Split the comma-separated string and create the request object
        sensor_types_list = [s.strip() for s in sensor_types.split(',')]
        request = SensorDataRequest(sensor_types=sensor_types_list)
        
        data = AppService()._get_sensors_data(uid, request)

        for sensor_data in data:
            if 'timestamp' in sensor_data:
                sensor_data['timestamp'] = sensor_data['timestamp'].isoformat()

        sensor_types_str = ', '.join(request.sensor_types)
        CustomLogger()._get_logger().info(f"Retrieved data for {sensor_types_str} types.")

        return JSONResponse(
            content=data,
            status_code=200
        )
    except Exception as e:
        CustomLogger()._get_logger().error(f"Failed to get sensor data: {e.args[0]}")
        return JSONResponse(
            content={"message": "Internal server error ", "detail": str(e.args[0])},
            status_code=500
        )

@router.get("/services_status")
async def get_services_status(uid = Depends(get_user_id)):
    """
    Endpoint to get all services config information includes mode and value.
    """
    try:
        service_config_data = AppService()._get_services_status(uid)
        CustomLogger()._get_logger().info(f"Retrieve successfully services status: {service_config_data}")

        return JSONResponse(
            content=service_config_data,
            status_code=200,
            media_type="application/json"
        )
        
    except Exception as e:
        CustomLogger()._get_logger().error(f"Failed to get services status: {e.args[0]}")
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
async def get_action_history(request: ActionHistoryRequest, uid = Depends(get_user_id)):
    try:
        data = AppService()._get_action_history(uid, request)
        CustomLogger()._get_logger().info(f"Retrieved successfully action history for \"{request.service_type}\" of user \"{uid}\"")

        return JSONResponse(
            content=data,
            status_code=200
        )
    
    except Exception as e:
        CustomLogger()._get_logger().error(f"Failed to get action history: {e.args[0]}")
        return JSONResponse(
            content={"message": "Internal server error ", "detail": e.args[0]},
            status_code=500
        )