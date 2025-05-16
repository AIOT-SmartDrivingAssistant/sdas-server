import sys
import os

# Add the root path to the sys.path to import the modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from utils.custom_logger import CustomLogger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from middlewares.auth_middleware import AuthMiddleware
from middlewares.header_middleware import SecurityHeadersMiddleware
from middlewares.notfound_middleware import NotFoundMiddleware
from middlewares.logger_middleware import LoggerMiddleware

from routes.auth_routes import router as auth_router
from routes.user_routes import router as user_router
from routes.iot_routes import router as iot_router
from routes.app_routes import router as app_router

from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Collect all route paths from routers
route_prefixes = ['/auth', '/user', '/iot', '/app']
route_paths = set()
for router, prefix in [
    (auth_router, '/auth'),
    (user_router, '/user'),
    (iot_router, '/iot'),
    (app_router, '/app'),
]:
    for route in router.routes:
        if hasattr(route, 'path'):
            route_paths.add(prefix + route.path if not route.path.startswith('/') else prefix + route.path)
route_paths.add('/')

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("ALLOWED_ORIGINS", "*")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(AuthMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(NotFoundMiddleware, routes=list(route_paths))
app.add_middleware(LoggerMiddleware)

app.include_router(auth_router, prefix='/auth')
app.include_router(user_router, prefix='/user')
app.include_router(iot_router, prefix='/iot')
app.include_router(app_router, prefix='/app')

if __name__ == '__main__':
    CustomLogger()._get_logger().info("Starting backend server")

    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=12798, reload=True, reload_dirs=["src"])
