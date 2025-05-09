from utils.custom_logger import CustomLogger

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

import time
from colorama import Fore

class LoggerMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.logger = CustomLogger()._get_logger()
        self.URL_WIDTH = 15
        self.METHOD_WIDTH = 5

    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Process the request and get response
        response = await call_next(request)
        
        # Calculate processing time
        process_time = (time.time() - start_time) * 1000
        
        # Get request details
        method = request.method
        url = request.url.path
        status_code = response.status_code
        client_ip = request.client.host if request.client else "unknown"

        # Color formatting for method
        method_color = (
            Fore.BLUE if method == "GET"
            else Fore.GREEN if method == "POST"
            else Fore.RED if method == "DELETE"
            else Fore.YELLOW if method == "PUT"
            else Fore.MAGENTA if method == "PATCH"
            else Fore.CYAN
        )
        colored_method = f"{method_color}{method:{self.METHOD_WIDTH}}{Fore.RESET}"

        # Color formatting for status code
        status_color = (
            Fore.GREEN if status_code < 300
            else Fore.YELLOW if status_code < 400
            else Fore.RED
        )
        colored_status = f"{status_color}{status_code}{Fore.RESET}"

        log_message = (
            f"{colored_status} {Fore.CYAN}| "
            f"{colored_method} {Fore.WHITE}{url:{self.URL_WIDTH}} {Fore.CYAN}| "
            f"{Fore.MAGENTA}{client_ip} {Fore.YELLOW}+{int(process_time)}ms{Fore.RESET}"
        )

        if status_code < 400:
            self.logger.info(log_message)
        elif status_code < 500:
            self.logger.warning(log_message)
        else:
            self.logger.error(log_message)
        
        return response