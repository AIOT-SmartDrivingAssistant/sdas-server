from enum import Enum

class IotCommand(Enum):
    FIELD_DEVICE_ID = "device_id"
    FIELD_COMMAND_ID = "command_id"
    FIELD_COMMAND = "command"
    FIELD_TARGET = "target"
    FIELD_VALUE = "value"

class IotCommandResponse(Enum):
    FIELD_DEVICE_ID = "device_id"
    FIELD_COMMAND_ID = "command_id"
    FIELD_STATUS = "status"
    FIELD_MESSAGE = "message"

class IotNotification(Enum):
    FIELD_DEVICE_ID = "device_id"
    FIELD_SERVICE_TYPE = "service_type"
    FIELD_DESCRIPTION = "description"
    FIELD_TIMESTAMP = "timestamp"

class SensorTypes(Enum):
    FIELD_TEMP = "temp"
    FIELD_DIS = "dis"
    FIELD_HUMID = "humid"
    FIELD_LUX = "lux"

    ALL_FIELD = [FIELD_TEMP, FIELD_DIS, FIELD_HUMID, FIELD_LUX]