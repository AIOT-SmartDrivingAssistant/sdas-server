from utils.custom_logger import CustomLogger

import os
from pymongo import MongoClient
from datetime import datetime
import gridfs

class Database:
    FIELD_MONGO_URL = "mongo_url"
    FIELD_DB_NAME = "db_name"
    
    FIELD_USER_COLLECTION = "user"
    FIELD_USER_CONFIG_COLLECTION = "user_config"
    FIELD_ENV_SENSOR_COLLECTION = "environment_sensor"
    FIELD_SERVICES_STATUS_COLLECTION = "services_status"
    FIELD_ACTION_HISTORY_COLLECTION = "action_history"

    _instance = None
    _cache_data = {}

    def __new__(cls, config: dict=None, test_mode: bool=False):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance._init_database(config, test_mode)
        return cls._instance

    def _init_database(self, config: dict=None, test_mode: bool=False):
        if config == None or not config.contains(self.FIELD_MONGO_URL) or not config.contains(self.FIELD_DB_NAME):
            config = {
                self.FIELD_MONGO_URL: os.getenv("MONGODB_URL"),
                self.FIELD_DB_NAME: os.getenv("MONGODB_DB_NAME")
            }
            CustomLogger()._get_logger().info("Use env configuration to initialize database")
        try:
            self.client = MongoClient(config[self.FIELD_MONGO_URL])
            self.db = self.client[config[self.FIELD_DB_NAME]]
            self.fs = gridfs.GridFS(self.db, os.getenv("MONGOBD_AVATAR_COL"))

            CustomLogger()._get_logger().info(f"Connected with database {self.db}.")
        except Exception as e:
            CustomLogger()._get_logger().error(f"Failed to connect with database: {e}")
            self._instance = None

# User region
    def get_user_collection(self):
        return self.db.get_collection(self.FIELD_USER_COLLECTION)
    
    def get_user_config_collection(self):
        return self.db.get_collection(self.FIELD_USER_CONFIG_COLLECTION)
# End user region
    
# IOT region
    def get_env_sensor_collection(self):
        return self.db.get_collection(self.FIELD_ENV_SENSOR_COLLECTION)
    
    def get_services_status_collection(self):
        return self.db.get_collection(self.FIELD_SERVICES_STATUS_COLLECTION)
    
    def get_action_history_collection(self):
        return self.db.get_collection(self.FIELD_ACTION_HISTORY_COLLECTION)
# End IOT region