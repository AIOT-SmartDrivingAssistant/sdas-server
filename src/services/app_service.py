import asyncio
import json
from typing import Dict

import datetime

from fastapi.responses import StreamingResponse
from models.common import SensorTypes
from utils.custom_logger import CustomLogger
from services.database import Database

from models.request import SensorDataRequest
from models.mongo_doc import ActionHistoryDocument, EnvironmentSensorDocument, ServicesStatusDocument

class AppService:
    _instance = None

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
                    CustomLogger()._get_logger().info(f"Sent notification: {{ userId: \"{client_id}\", notification: {notification} }} ")
                    self.client_queues[client_id].task_done()

            except asyncio.CancelledError:
                async with self._lock:
                    if client_id in self.client_queues and self.client_queues[client_id].empty():
                        del self.client_queues[client_id]
                CustomLogger()._get_logger().info(f"Closed notification stream: {{ userId: \"{client_id}\" }}")
                raise

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

    def _create_init_services_status_data(self, uid: str = None):
        init_services_status_data = {}

        init_services_status_data[ServicesStatusDocument.FIELD_UID.value] = uid if uid else ""

        for field in ServicesStatusDocument.ALL_SERVICE_FIELDS.value:
            init_services_status_data[field] = "off"

        for field in ServicesStatusDocument.ALL_VALUE_FIELDS.value:
            if field == ServicesStatusDocument.FIELD_TEMPERATURE_THRESHOLD.value:
                init_services_status_data[field] = 40
            elif field == ServicesStatusDocument.FIELD_HUMIDITY_THRESHOLD.value:
                init_services_status_data[field] = 70
            elif field == ServicesStatusDocument.FIELD_DISTANCE_THRESHOLD.value:
                init_services_status_data[field] = 10
            elif field == ServicesStatusDocument.FIELD_LUX_THRESHOLD.value:
                init_services_status_data[field] = 20
            else:
                init_services_status_data[field] = 5

        return init_services_status_data

    def _get_newest_sensor_data(self, uid: str = None, sensor_type: str = None) -> dict:
        """Get the newest sensor data for a specific user and sensor type."""
        data = Database()._instance.get_env_sensor_collection().find_one(
            {
                EnvironmentSensorDocument.FIELD_UID.value: uid,
                EnvironmentSensorDocument.FIELD_SENSOR_TYPE.value: sensor_type
            },
            sort=[(EnvironmentSensorDocument.FIELD_TIMESTAMP.value, -1)]  # Sort by timestamp in descending order
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
                newest_data[EnvironmentSensorDocument.FIELD_TIMESTAMP.value] = newest_data[EnvironmentSensorDocument.FIELD_TIMESTAMP.value]
                data.append(newest_data)

        return data
    
    def _get_services_status(self, uid: str = None):
        """Get services status from the database by user id."""
        services_status = Database()._instance.get_services_status_collection().find_one({'uid': uid})
        
        if not services_status:
            raise Exception("Service config not find")
        
        data = {}
        for key in ServicesStatusDocument.ALL_SERVICE_FIELDS.value:
            data[key] = services_status[key]

        for key in ServicesStatusDocument.ALL_VALUE_FIELDS.value:
            data[key] = services_status[key]

        return data
    
    def _toggle_all_service_status(self, uid: str, is_turning_on: bool, session):
        data = {
            ServicesStatusDocument.FIELD_SYSTEM_STATUS.value: "on" if is_turning_on else "off",
            ServicesStatusDocument.FIELD_AIR_COND_SERVICE.value: "on" if is_turning_on else "off",
            ServicesStatusDocument.FIELD_DISTANCE_SERVICE.value: "on" if is_turning_on else "off",
            ServicesStatusDocument.FIELD_DROWSINESS_SERVICE.value: "on" if is_turning_on else "off",
            ServicesStatusDocument.FIELD_HEADLIGHT_SERVICE.value: "on" if is_turning_on else "off",
        }
        if (not is_turning_on):
            data[ServicesStatusDocument.FIELD_AIR_COND_TEMP.value] = 0
            data[ServicesStatusDocument.FIELD_HEADLIGHT_BRIGHTNESS.value] = 0
            

        Database()._instance.get_services_status_collection().update_one(
            { 'uid': uid },
            {
                "$set": {
                    ServicesStatusDocument.FIELD_SYSTEM_STATUS.value: "on" if is_turning_on else "off",
                    ServicesStatusDocument.FIELD_AIR_COND_SERVICE.value: "on" if is_turning_on else "off",
                    ServicesStatusDocument.FIELD_DISTANCE_SERVICE.value: "on" if is_turning_on else "off",
                    ServicesStatusDocument.FIELD_DROWSINESS_SERVICE.value: "on" if is_turning_on else "off",
                    ServicesStatusDocument.FIELD_HEADLIGHT_SERVICE.value: "on" if is_turning_on else "off",
                }
            },
            session=session
        )
    
    def _get_all_action_history(self, uid: str = None):
        action_history = Database()._instance.get_action_history_collection().find(
            {
                ActionHistoryDocument.FIELD_UID.value: uid
            },
            sort=[(ActionHistoryDocument.FIELD_TIMESTAMP.value, -1)],  # Sort by timestamp in descending order
            limit=15
        )

        data = []
        for action in action_history:
            action['_id'] = str(action['_id'])
            action[ActionHistoryDocument.FIELD_TIMESTAMP.value] = action[ActionHistoryDocument.FIELD_TIMESTAMP.value]
            action.pop(ActionHistoryDocument.FIELD_UID.value, None)
            action.pop('_id', None)
            data.append(action)

        return data
    
    def _get_all_sensor_data(self, uid: str = None) -> dict:
        """Get 20 newest data for each sensor type: temp, humid, dis, lux."""
        result = {}
        min_interval = datetime.timedelta(seconds=10)

        for sensor_type in SensorTypes:
            cursor = Database()._instance.get_env_sensor_collection().find(
                {
                    EnvironmentSensorDocument.FIELD_UID.value: uid,
                    EnvironmentSensorDocument.FIELD_SENSOR_TYPE.value: sensor_type.value
                },
                sort=[(EnvironmentSensorDocument.FIELD_TIMESTAMP.value, -1)],
                limit=100
            )
            data = []
            last_timestamp = None
            for doc in cursor:
                doc.pop('_id', None)
                doc.pop('uid', None)
                if EnvironmentSensorDocument.FIELD_TIMESTAMP.value in doc:
                    ts = doc[EnvironmentSensorDocument.FIELD_TIMESTAMP.value]
                    # Convert to datetime if needed
                    if isinstance(ts, str):
                        ts = datetime.datetime.fromisoformat(ts)
                    if last_timestamp is None or (last_timestamp - ts) >= min_interval:
                        doc[EnvironmentSensorDocument.FIELD_TIMESTAMP.value] = ts.isoformat()
                        data.append(doc)
                        last_timestamp = ts
                if len(data) >= 20:
                    break
            result[sensor_type.value] = data

        return result
    