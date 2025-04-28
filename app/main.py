import sys
import os

# Add the root path to the sys.path to import the modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from dotenv import load_dotenv
load_dotenv()

from utils.custom_logger import CustomLogger

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from middlewares.auth_middleware import AuthMiddleware
from services.database import Database

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("ALLOWED_ORIGINS").split(','),  # First one is app client, second one is iot-server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)
app.add_middleware(AuthMiddleware)

from routes.auth_routes import router as auth_router
app.include_router(auth_router, prefix='/auth')

from routes.user_routes import router as user_router
app.include_router(user_router, prefix='/user')

from routes.iot_routes import router as iot_router
app.include_router(iot_router, prefix='/iot')

from routes.app_routes import router as app_router
app.include_router(app_router, prefix='/app')

# for route in app.routes:
#     CustomLogger().get_logger().info(route)

if __name__ == '__main__':
    CustomLogger()._get_logger().info("Starting backend server")

    db = Database()._instance
    import uvicorn
    uvicorn.run('main:app', host='127.0.0.1', port=8080, reload=True, reload_dirs=["server/app"])