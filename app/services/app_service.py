import asyncio
import json
from typing import Dict

from fastapi.responses import StreamingResponse
from utils.custom_logger import CustomLogger
from services.database import Database
from models.request import ActionHistoryRequest, SensorDataRequest
from models.mongo_doc import ServicesStatusDocument

class AppService:
    _instance = None

    FIELD_UID = "uid"
    FIELD_SENSOR_TYPE = "sensor_type"
    FIELD_TIMESTAMP = "timestamp"
    FIELD_VAL = "val"

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(AppService, cls).__new__(cls)
            cls._instance._init_instance()
        return cls._instance

    def _init_instance(self):
        self.client_queues: Dict[str, asyncio.Queue] = {}  # client_id -> Queue
        self._lock = asyncio.Lock()  # Protect queue creation/removal

    async def _add_notification(self, client_id: str, notification: dict):
        """Add a notification to the client's queue."""
        async with self._lock:
            if client_id not in self.client_queues:
                self.client_queues[client_id] = asyncio.Queue()
            await self.client_queues[client_id].put(notification)
            CustomLogger()._get_logger().info(f"Queued notification for client \"{client_id}\": {notification}")

    async def _get_notification_stream(self, client_id: str):
        """Stream notifications as SSE events."""
        async def event_generator():
            async with self._lock:
                if client_id not in self.client_queues:
                    self.client_queues[client_id] = asyncio.Queue()

            try:
                while True:
                    notification = await self.client_queues[client_id].get()
                    yield f"data: {json.dumps(notification)}\n\n"
                    CustomLogger()._get_logger().info(f"Sent notification to client \"{client_id}\": {notification}")
                    self.client_queues[client_id].task_done()

            except asyncio.CancelledError:
                async with self._lock:
                    if client_id in self.client_queues and self.client_queues[client_id].empty():
                        del self.client_queues[client_id]
                CustomLogger()._get_logger().info(f"Closed notification stream for client \"{client_id}\"")
                raise

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

    def _create_init_services_status_data(self, uid: str = None):
        init_services_status_data = {}

        init_services_status_data[ServicesStatusDocument.FIELD_UID] = uid if uid else ""

        for field in ServicesStatusDocument.ALL_SEVICE_FIELDS:
            init_services_status_data[field] = "off"

        for field in ServicesStatusDocument.ALL_VALUE_FIELDS:
            init_services_status_data[field] = 0

        return init_services_status_data

    def _get_newest_sensor_data(self, uid: str = None, sensor_type: str = None) -> dict:
        """Get the newest sensor data for a specific user and sensor type."""
        data = Database()._instance.get_env_sensor_collection().find_one(
            {
                self.FIELD_UID: uid,
                self.FIELD_SENSOR_TYPE: sensor_type
            },
            sort=[(self.FIELD_TIMESTAMP, -1)]  # Sort by timestamp in descending order
        )

        if data and data['_id']:
            data['_id'] = str(data['_id'])

        return data

    def _get_sensors_data(self, uid: str = None, request: SensorDataRequest = None) -> list:
        """Get the newest sensor data for multiple sensor types."""
        sensor_types = request.sensor_types

        data = []
        for sensor_type in sensor_types:
            newest_data = self._get_newest_sensor_data(uid, sensor_type)
            if newest_data:
                data.append(newest_data)

        return data
    
    def _get_services_status(self, uid: str = None):
        """Get services status from the database by user id."""
        services_status = Database()._instance.get_services_status_collection().find_one({'uid': uid})
        
        if not services_status:
            raise Exception("Service config not find")
        
        data = {}
        for key in ServicesStatusDocument.ALL_SEVICE_FIELDS:
            data[key] = services_status[key]

        for key in ServicesStatusDocument.ALL_VALUE_FIELDS:
            data[key] = services_status[key]

        return data
        
    def _get_action_history(self, request: ActionHistoryRequest = None, uid: str = None):
        service_type = request.service_type
        amt = request.amt

        action_history = Database()._instance.get_action_history_collection().find(
            {
                "uid": uid,
                "service_type": service_type
            },
            sort=[(self.FIELD_TIMESTAMP, -1)],  # Sort by timestamp in descending order
            limit=amt
        )

        data = []
        for action in action_history:
            data.append(action)

        return data