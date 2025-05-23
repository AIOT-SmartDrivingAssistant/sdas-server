from utils.custom_logger import CustomLogger

import asyncio
from datetime import datetime
import uuid

from services.database import Database
from services.app_service import AppService

from models.request import IOTDataResponse, IOTNotification
from models.common import IotCommand, IotCommandResponse, IotNotification
from models.mongo_doc import ActionHistoryDocument, ServicesStatusDocument

from typing import Dict
from fastapi import WebSocket, WebSocketDisconnect

class IOTService:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(IOTService, cls).__new__(cls)
            cls._instance._init_instance()
        return cls._instance
    
    def _init_instance(self):
        self.connected_iot_systems: Dict[str, tuple[WebSocket, str]] = {} # device_id -> [websocket, system_state]
        self.pending_commands: Dict[str, Dict[str, asyncio.Event]] = {}   # device_id -> [command_id: Event]
        self.command_responses: Dict[str, Dict[str, any]] = {}            # device_id -> [command_id: response]

        self.device_locks: Dict[str, asyncio.Lock] = {}                   # device_id -> lock
        self.global_lock = asyncio.Lock()                                 # Lock for global state (device list)

    async def _add_connected_iot_system(self, device_id: str, websocket: WebSocket):
        async with self.global_lock:
            if device_id in self.connected_iot_systems:
                await websocket.close(code=1008, reason="Device already connected")
                return False

            self.device_locks[device_id] = asyncio.Lock()
            async with self.device_locks[device_id]:
                await websocket.accept()
                self.connected_iot_systems[device_id] = [websocket, "established"]
                self.pending_commands[device_id] = {}
                self.command_responses[device_id] = {}
            return True

    async def _establish_connection(self, device_id: str, websocket: WebSocket):
        if not await self._add_connected_iot_system(device_id, websocket):
            CustomLogger()._get_logger().warning(f"Websocket connect FAIL: {{ deviceId: \"{device_id}\" }} already connected")
            return

        CustomLogger()._get_logger().info(f"Websocket connect SUCCESS: {{ deviceId: \"{device_id}\" }}")
        try:
            while True:
                data = await websocket.receive_json()

                if not data or not isinstance(data, dict):
                    CustomLogger()._get_logger().warning(f"Websocket error: {{ deviceId: \"{device_id}\" }} invalid data received")
                    await websocket.send_json({"error": "Invalid data"})
                    continue

                if IotCommandResponse.FIELD_COMMAND_ID.value in data and IotCommandResponse.FIELD_STATUS.value in data:
                    # Data is a command's response
                    try:
                        iot_data = IOTDataResponse(**data)

                        if iot_data.device_id != device_id:
                            CustomLogger()._get_logger().warning(f"Websocket error: {{ deviceId: \"{device_id}\" }} deviceId mismatch")
                            await websocket.send_json({"error": "Device ID mismatch"})
                            continue
                        
                        command_id = data[IotCommandResponse.FIELD_COMMAND_ID.value]
                        
                        async with self.device_locks.get(device_id, asyncio.Lock()):
                            if device_id in self.pending_commands and command_id in self.pending_commands[device_id]:
                                # Store response and signal Event
                                self.command_responses[device_id][command_id] = data
                                self.pending_commands[device_id][command_id].set()

                                CustomLogger()._get_logger().info(f"Websocket command response: {{ deviceId: \"{device_id}\", command_id \"{command_id}\", status \"{iot_data.status}\" }}")

                            else:
                                CustomLogger()._get_logger().warning(f"Websocket error: {{ deviceId: \"{device_id}\" }} unknown command ID \"{command_id}\"")
                                await websocket.send_json({"error": "Unknown command ID"})

                    except Exception as e:
                        CustomLogger()._get_logger().error(f"Websocket error: {{ deviceId: \"{device_id}\" }} invalid response {e}")
                        await websocket.send_json({"error": "Invalid response"})

                elif IotNotification.FIELD_DESCRIPTION.value in data:
                    # Data is a notification
                    try:
                        iot_notification = IOTNotification(**data)

                        if iot_notification.device_id != device_id:
                            CustomLogger()._get_logger().warning(f"Websocket error: {{ deviceId: \"{device_id}\" }} deviceId mismatch")
                            await websocket.send_json({"error": "Device ID mismatch"})
                            continue

                        CustomLogger()._get_logger().info(f"Websocket notification: {{ deviceId: \"{device_id}\", service_type \"{iot_notification.service_type}\", notification \"{iot_notification.description}\" }}")

                        await AppService()._add_notification(
                            client_id=device_id,
                            notification={
                                IotNotification.FIELD_SERVICE_TYPE.value: iot_notification.service_type,
                                IotNotification.FIELD_DESCRIPTION.value: iot_notification.description,
                                IotNotification.FIELD_TIMESTAMP.value: iot_notification.timestamp,
                            }
                        )

                    except Exception as e:
                        CustomLogger()._get_logger().error(f"Websocket error: {{ deviceId: \"{device_id}\" }} invalid notification {e}")
                        await websocket.send_json({"error": "Invalid notification"})

        except WebSocketDisconnect:
            CustomLogger()._get_logger().info(f"Websocket disconnect: {{ deviceId: \"{device_id}\" }}")
            await AppService()._add_notification(
                client_id=device_id,
                notification={
                    IotNotification.FIELD_SERVICE_TYPE.value: "system",
                    IotNotification.FIELD_DESCRIPTION.value: "Device disconnected",
                    IotNotification.FIELD_TIMESTAMP.value: datetime.now().isoformat()
                }
            )
            session = Database()._instance.client.start_session()
            try:
                with session.start_transaction():
                    AppService()._toggle_all_service_status(device_id, False, session)
                    self.write_action_history(
                        uid=device_id,
                        service_type="system",
                        value="off",
                        session=session
                    )
            except Exception as e:
                session.abort_transaction()
                CustomLogger()._get_logger().error(f"Websocket error: {{ deviceId: \"{device_id}\" }} failed to update database {e}")
            finally:
                session.end_session()

        except Exception as e:
            CustomLogger()._get_logger().error(f"Websocket error: {{ deviceId: \"{device_id}\" }} {e}")

        finally:
            await self._cleanup_device(device_id)

    async def _cleanup_device(self, device_id: str):
        """Clean up device state on disconnect."""
        async with self.global_lock:
            if device_id in self.connected_iot_systems:
                async with self.device_locks.get(device_id, asyncio.Lock()):
                    del self.connected_iot_systems[device_id]
                    if device_id in self.pending_commands:
                        for event in self.pending_commands[device_id].values():
                            event.set()
                        del self.pending_commands[device_id]
                    if device_id in self.command_responses:
                        del self.command_responses[device_id]
                # Remove device-specific lock
                if device_id in self.device_locks:
                    del self.device_locks[device_id]

    async def _control_iot_system(self, device_id: str, target: str, value: str):
        async with self.global_lock:
            if device_id not in self.connected_iot_systems:
                CustomLogger()._get_logger().warning(f"Websocket error: {{ deviceId: \"{device_id}\" }} not connected")
                raise Exception("Device not connected")

        try:
            command_id = str(uuid.uuid4())
            data = {
                IotCommand.FIELD_COMMAND.value: {
                    IotCommand.FIELD_TARGET.value: target,
                    IotCommand.FIELD_VALUE.value: value
                },
                IotCommand.FIELD_COMMAND_ID.value: command_id
            }

            async with self.device_locks.get(device_id, asyncio.Lock()):
                self.pending_commands[device_id][command_id] = asyncio.Event()

            websocket = self.connected_iot_systems[device_id][0]
            await websocket.send_json(data)

            CustomLogger()._get_logger().info(f"Websocket command sent: {{ deviceId: \"{device_id}\", command_id \"{command_id}\", target \"{target}\", command \"{value}\" }}")

            try:
                await asyncio.wait_for(self.pending_commands[device_id][command_id].wait(), timeout=5.0)

            except asyncio.TimeoutError:
                CustomLogger()._get_logger().error(f"Websocket error: {{ deviceId: \"{device_id}\" }} command timeout")
                async with self.device_locks.get(device_id, asyncio.Lock()):
                    await self._cleanup_command(device_id, command_id)
                raise Exception("Timeout waiting for response")

            async with self.device_locks.get(device_id, asyncio.Lock()):
                if command_id in self.command_responses[device_id]:
                    response = self.command_responses[device_id][command_id]
                    await self._cleanup_command(device_id, command_id)

                    if response.get(IotCommandResponse.FIELD_STATUS.value) == "success":
                        if target == "system":
                            self.connected_iot_systems[device_id][1] = value
                            session = Database()._instance.client.start_session()
                            try:
                                with session.start_transaction():
                                    AppService()._toggle_all_service_status(device_id, value == "on", session)
                                    self.write_action_history(
                                        uid=device_id,
                                        service_type=target,
                                        value=value,
                                        session=session
                                    )
                            except Exception as e:
                                CustomLogger()._get_logger().error(f"Websocket error: {{ deviceId: \"{device_id}\" }} failed to update database {e}")
                            finally:
                                session.end_session()

                        else:
                            # TODO: update db
                            write_type = target
                            if (value not in ['on', 'off']):
                                if (target == ServicesStatusDocument.FIELD_AIR_COND_SERVICE.value):
                                    write_type = ServicesStatusDocument.FIELD_AIR_COND_TEMP.value

                                elif (target == ServicesStatusDocument.FIELD_HEADLIGHT_SERVICE.value):
                                    write_type = ServicesStatusDocument.FIELD_HEADLIGHT_BRIGHTNESS.value

                            session = Database()._instance.client.start_session()
                            try:
                                with session.start_transaction():
                                    self.update_services_status(
                                        uid=device_id,
                                        service_type=write_type,
                                        value=value,
                                        session=session
                                    )
                                    self.write_action_history(
                                        uid=device_id,
                                        service_type=write_type,
                                        value=value,
                                        session=session
                                    )
                            except Exception as e:
                                CustomLogger()._get_logger().error(f"Websocket error: {{ deviceId: \"{device_id}\" }} failed to update database {e}")
                            finally:
                                session.end_session()
                    
                    else:
                        raise Exception(response.get(IotCommandResponse.FIELD_MESSAGE.value))
                    
                else:
                    raise Exception("No response received")

        except Exception as e:
            CustomLogger()._get_logger().error(f"Websocket error: {{ deviceId: \"{device_id}\" }} fail to control iot system {e}")
            async with self.device_locks.get(device_id, asyncio.Lock()):
                await self._cleanup_command(device_id, command_id)
            raise e

    async def _cleanup_command(self, device_id: str, command_id: str):
        """Clean up command state."""
        if device_id in self.pending_commands and command_id in self.pending_commands[device_id]:
            del self.pending_commands[device_id][command_id]

        if device_id in self.command_responses and command_id in self.command_responses[device_id]:
            del self.command_responses[device_id][command_id]

    def update_services_status(self, uid: str, service_type: str, value: str, session):
        if (service_type in (ServicesStatusDocument.ALL_VALUE_FIELDS.value)):
            value = int(value)
                
        Database()._instance.get_services_status_collection().update_one(
            { ServicesStatusDocument.FIELD_UID.value: uid },
            {
                "$set": {
                    service_type: value
                }
            },
            session=session
        )

    def write_action_history(self, uid: str, service_type: str, value: str, session):
        action = {
            ActionHistoryDocument.FIELD_UID.value: uid,
            ActionHistoryDocument.FIELD_SERVICE_TYPE.value: service_type,
            ActionHistoryDocument.FIELD_DESCRIPTION.value: f"{service_type} set to {value}",
            ActionHistoryDocument.FIELD_TIMESTAMP.value: datetime.now().isoformat()
        }

        Database()._instance.get_action_history_collection().insert_one(
            document=action,
            session=session
        )