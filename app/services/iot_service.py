import asyncio
import uuid

from models.request import IOTDataResponse, IOTNotification
from services.app_service import AppService
from utils.custom_logger import CustomLogger

from typing import Dict
from fastapi import WebSocket, WebSocketDisconnect

class IOTService:
    _instance = None

    FIELD_TARGET = "target"
    FIELD_VALUE = "value"

    FIELD_COMMAND = "command"
    FIELD_COMMAND_ID = "command_id"
    FIELD_STATUS = "status"
    FIELD_MESSAGE = "message"
    
    FIELD_SERVICE_TYPE = "service_type"
    FIELD_NOTIFICATION = "notification"

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
                CustomLogger()._get_logger().warning(f"Device \"{device_id}\" is already connected")
                return False

            self.device_locks[device_id] = asyncio.Lock()
            async with self.device_locks[device_id]:
                await websocket.accept()
                self.connected_iot_systems[device_id] = [websocket, "established"]
                self.pending_commands[device_id] = {}
                self.command_responses[device_id] = {}
                CustomLogger()._get_logger().info(f"Successfully connect to device \"{device_id}\"")
            return True

    async def _establish_connection(self, device_id: str, websocket: WebSocket):
        if not await self._add_connected_iot_system(device_id, websocket):
            return

        try:
            while True:
                data = await websocket.receive_json()

                if not data or not isinstance(data, dict):
                    CustomLogger()._get_logger().error(f"Invalid data from device \"{device_id}\"")
                    await websocket.send_json({"error": "Invalid data"})
                    continue

                if self.FIELD_COMMAND_ID in data and self.FIELD_STATUS in data:
                    # Data is a command's response
                    try:
                        iot_data = IOTDataResponse(**data)

                        if iot_data.device_id != device_id:
                            CustomLogger()._get_logger().error(f"Device ID mismatch: {iot_data.device_id}")
                            await websocket.send_json({"error": "Device ID mismatch"})
                            continue
                        
                        command_id = data[self.FIELD_COMMAND_ID]
                        
                        async with self.device_locks.get(device_id, asyncio.Lock()):
                            if device_id in self.pending_commands and command_id in self.pending_commands[device_id]:
                                # Store response and signal Event
                                self.command_responses[device_id][command_id] = data
                                self.pending_commands[device_id][command_id].set()

                                CustomLogger()._get_logger().info(f"Receive response for command \"{command_id}\" from device \"{device_id}\": {data}")

                            else:
                                CustomLogger()._get_logger().warning(f"Unknown command_id \"{command_id}\" for device \"{device_id}\"")
                                await websocket.send_json({"error": "Unknown command ID"})

                    except Exception as e:
                        CustomLogger()._get_logger().error(f"Invalid command's response from device \"{device_id}\": {e}")
                        await websocket.send_json({"error": "Invalid response"})

                elif self.FIELD_NOTIFICATION in data:
                    # Data is a notification
                    try:
                        iot_notification = IOTNotification(**data)

                        if iot_notification.device_id != device_id:
                            CustomLogger()._get_logger().error(f"Device ID mismatch: {iot_notification.device_id}")
                            await websocket.send_json({"error": "Device ID mismatch"})
                            continue

                        CustomLogger()._get_logger().info(f"Receive notification \"{iot_notification.notification}\" from device \"{device_id}\"")

                        await AppService()._add_notification(
                            client_id=device_id,
                            notification={
                                "service_type": iot_notification.service_type,
                                "notification": iot_notification.notification
                            }
                        )

                    except Exception as e:
                        CustomLogger()._get_logger().error(f"Invalid notification from device \"{device_id}\": {e}")
                        await websocket.send_json({"error": "Invalid notification"})

        except WebSocketDisconnect:
            CustomLogger()._get_logger().info(f"Device \"{device_id}\" disconnected")

        except Exception as e:
            CustomLogger()._get_logger().error(f"Websocket error with device \"{device_id}\": {e}")

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

    async def _control_iot_system(self, device_id: str, target: str, command: str):
        async with self.global_lock:
            if device_id not in self.connected_iot_systems:
                CustomLogger()._get_logger().error(f"Device \"{device_id}\" is not connected")
                raise Exception("Device not connected")

        try:
            command_id = str(uuid.uuid4())
            data = {
                self.FIELD_COMMAND: {
                    self.FIELD_TARGET: target,
                    self.FIELD_VALUE: command
                },
                self.FIELD_COMMAND_ID: command_id
            }

            async with self.device_locks.get(device_id, asyncio.Lock()):
                self.pending_commands[device_id][command_id] = asyncio.Event()

            websocket = self.connected_iot_systems[device_id][0]
            await websocket.send_json(data)

            CustomLogger()._get_logger().info(f"Sent command \"{command}\" to device \"{device_id}\" with command_id \"{command_id}\"")

            try:
                await asyncio.wait_for(self.pending_commands[device_id][command_id].wait(), timeout=5.0)

            except asyncio.TimeoutError:
                CustomLogger()._get_logger().error(f"Timeout waiting for response from device \"{device_id}\"")
                async with self.device_locks.get(device_id, asyncio.Lock()):
                    await self._cleanup_command(device_id, command_id)
                raise Exception("Timeout waiting for response")

            async with self.device_locks.get(device_id, asyncio.Lock()):
                if command_id in self.command_responses[device_id]:
                    response = self.command_responses[device_id][command_id]
                    await self._cleanup_command(device_id, command_id)

                    if response.get(self.FIELD_STATUS) == "success":
                        CustomLogger()._get_logger().info(f"Device \"{device_id}\" confirmed command \"{command_id}\"")
                        if target == "system":
                            self.connected_iot_systems[device_id][1] = response.get(self.FIELD_VALUE)
                    
                    else:
                        CustomLogger()._get_logger().error(f"Device \"{device_id}\" response FAIL for command \"{command_id}\": {response.get(self.FIELD_MESSAGE)}")
                        raise Exception(response.get(self.FIELD_MESSAGE))
                    
                else:
                    CustomLogger()._get_logger().error(f"No response received for command \"{command_id}\"")
                    raise Exception("No response received")

        except Exception as e:
            CustomLogger()._get_logger().error(f"Failed to control system {device_id}: {e}")
            async with self.device_locks.get(device_id, asyncio.Lock()):
                await self._cleanup_command(device_id, command_id)
            raise e

    async def _cleanup_command(self, device_id: str, command_id: str):
        """Clean up command state."""
        if device_id in self.pending_commands and command_id in self.pending_commands[device_id]:
            del self.pending_commands[device_id][command_id]

        if device_id in self.command_responses and command_id in self.command_responses[device_id]:
            del self.command_responses[device_id][command_id]