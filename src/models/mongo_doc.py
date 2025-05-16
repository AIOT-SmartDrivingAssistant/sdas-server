from enum import Enum

class UserDocument(Enum):
    FIELD_USERNAME = 'username'
    FIELD_PASSWORD = 'password'

    FIELD_NAME = 'name'
    FIELD_EMAIL = 'email'
    FIELD_PHONE = 'phone'
    FIELD_ADDRESS = 'address'
    FIELD_DOB = 'date_of_birth'
    FIELD_AVATAR = 'avatar'

    ALL_BASIC_FIELDS = [FIELD_NAME, FIELD_EMAIL, FIELD_PHONE, FIELD_ADDRESS, FIELD_DOB]

class ServicesStatusDocument(Enum):
    FIELD_UID = 'uid'

    FIELD_SYSTEM_STATUS = 'system_status'
    FIELD_AIR_COND_SERVICE = 'air_cond_service'
    FIELD_HEADLIGHT_SERVICE = 'headlight_service'
    FIELD_DROWSINESS_SERVICE = 'drowsiness_service'
    FIELD_DISTANCE_SERVICE = 'distance_service'

    ALL_SERVICE_FIELDS = [FIELD_SYSTEM_STATUS, FIELD_AIR_COND_SERVICE, FIELD_HEADLIGHT_SERVICE, FIELD_DROWSINESS_SERVICE, FIELD_DISTANCE_SERVICE]

    FIELD_AIR_COND_TEMP = 'air_cond_temp'
    FIELD_HEADLIGHT_BRIGHTNESS = 'headlight_brightness'
    FIELD_DROWSINESS_THRESHOLD = 'drowsiness_threshold'

    ALL_VALUE_FIELDS = [FIELD_AIR_COND_TEMP, FIELD_HEADLIGHT_BRIGHTNESS, FIELD_DROWSINESS_THRESHOLD]

class ActionHistoryDocument(Enum):
    FIELD_UID = 'uid'

    FIELD_SERVICE_TYPE = 'service_type'
    FIELD_DESCRIPTION = 'description'
    FIELD_TIMESTAMP = 'timestamp'

    ALL_BASIC_FIELDS = [FIELD_SERVICE_TYPE, FIELD_DESCRIPTION, FIELD_TIMESTAMP]

class EnvironmentSensorDocument(Enum):
    FIELD_UID = 'uid'

    FIELD_SENSOR_TYPE = "sensor_type"
    FIELD_VALUE = "value"
    FIELD_TIMESTAMP = "timestamp"