import logging
import os
from datetime import datetime
from rich.console import Console
from rich.logging import RichHandler
from logging.handlers import RotatingFileHandler

class CustomLogger:
    _instance = None
    LOG_FORMAT = "%(message)s"
    DATE_FORMAT = "[%Y-%m-%d %H:%M:%S]"
    LOG_DIR = "server/logs"
    LOG_FILE = "backend"
    MAX_BYTES = 10 * 1024 * 1024  # 10MB
    BACKUP_COUNT = 5

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._init_logger()
        return cls._instance

    def _init_logger(self):
        if not hasattr(self, 'log'):
            self.console = Console()

            # Create logs directory if it doesn't exist
            if not os.path.exists(self.LOG_DIR):
                os.makedirs(self.LOG_DIR)

            # Create file handler with rotation
            file_handler = RotatingFileHandler(
                os.path.join(self.LOG_DIR, self.LOG_FILE + "_[" + datetime.now().strftime("%Y-%m-%d") + "].log"),
                maxBytes=self.MAX_BYTES,
                backupCount=self.BACKUP_COUNT
            )

            class FileFormatter(logging.Formatter):
                def format(self, record):
                    record.timestamp = datetime.now().strftime(CustomLogger.DATE_FORMAT)
                    if record.pathname and record.lineno:
                        path_name = '/'.join(record.pathname.split(os.sep)[record.pathname.split(os.sep).index("server") + 1:])
                        record.location = f"[{path_name}:{record.lineno}]"
                    else:
                        record.location = ""
                    return f"{record.timestamp} [{record.levelname}] {record.location} {record.getMessage()}"

            class ConsoleFormatter(logging.Formatter):
                def format(self, record):
                    return f"{record.getMessage()}"

            # Set formatters
            file_handler.setFormatter(FileFormatter())
            console_handler = RichHandler(rich_tracebacks=True)
            console_handler.setFormatter(ConsoleFormatter())


            # Configure root logger
            logging.basicConfig(
                level=logging.DEBUG,
                format=self.LOG_FORMAT,
                handlers=[console_handler, file_handler]
            )

            # Set other loggers to WARNING level
            all_loggers = logging.Logger.manager.loggerDict.keys()
            for logger in all_loggers:
                logging.getLogger(logger).setLevel(logging.WARNING)

            self.log = logging.getLogger()

    def _get_logger(self):
        return CustomLogger()._instance.log