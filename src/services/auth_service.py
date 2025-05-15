import os
from typing import Optional, Tuple

from fastapi import Response
from passlib.context import CryptContext
import secrets
from pymongo.errors import PyMongoError
import redis

from services.database import Database
from services.app_service import AppService
from services.user_service import UserService

from models.request import UserRequest
from models.mongo_doc import UserDocument

class AuthService:
    _instance = None

    __pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

    FIELD_SESSION_TTL = 3600 # 1 hour
    FIELD_REFRESH_TTL = 604800 # 7 days

    def __new__(cls):
        if not cls._instance:
            cls._instance = super(AuthService, cls).__new__(cls)
            cls._instance.__init_instance()
        return cls._instance

    def __init_instance(self):
        if os.getenv("SECURE") == "False":
            self.SECURE_MODE = False
        else:
            self.SECURE_MODE = True

        self.SAMESITE_MODE = os.getenv("SAME_SITE")

        self.__redis = redis.Redis(
            host=os.getenv("REDIS_HOST"),
            port=os.getenv("REDIS_PORT"),
            decode_responses=True,
            username="default",
            password=os.getenv("REDIS_PASSWORD"),
        )
        
    def _hash_pw(self, password: str) -> str:
        if not password:
            return None
        else:
            return AuthService.__pwd_context.hash(password)
    
    def _verify_pw(self, hashed_pw: str, password: str) -> bool:
        if not hashed_pw or not password:
            return False
        else:
            return AuthService.__pwd_context.verify(password, hashed_pw)
    
    def _register(self, user_request: UserRequest) -> None:
        '''
        Register a new user in the database.

        Args:
            user_request (UserRequest): An instance of UserRequest containing the username and password.

        Returns:
            None

        Raises:
            Exception: If the username already exists.
            PyMongoError: If there is an error during the database transaction.
        '''

        if Database()._instance.get_user_collection().find_one({UserDocument.FIELD_USERNAME: user_request.username}):
            raise Exception("Username already exists")
        
        hashed_pw = self._hash_pw(user_request.password)
        
        init_user_data = UserService()._create_init_user_data(user_request.username, hashed_pw)

        session = Database()._instance.client.start_session()
        try:
            with session.start_transaction():
                user_result = Database()._instance.get_user_collection().insert_one(
                    init_user_data,
                    session=session
                )
                
                init_services_status_data = AppService()._create_init_services_status_data(str(user_result.inserted_id))

                Database()._instance.get_services_status_collection().insert_one(
                    init_services_status_data,
                    session=session
                )

        except PyMongoError as e:
            session.abort_transaction()
            raise e
    
    def _authenticate(self, user_request: UserRequest) -> Tuple[Optional[str], Tuple[Optional[str], Optional[str]]]:
        '''
        Authenticate a user using the provided UserRequest object.

        Args:
            user_request (UserRequest): An instance of UserRequest containing the username and password.

        Returns:
            Tuple[Optional[str], Tuple[Optional[str], Optional[str]]]: A tuple containing the user ID, session token, and refresh token.

        Raises:
            Exception: If the credentials are invalid or if the user_request object is not provided.
        '''

        user = Database()._instance.get_user_collection().find_one({
            UserDocument.FIELD_USERNAME: user_request.username
        })
        if not (user and self._verify_pw(user[UserDocument.FIELD_PASSWORD], user_request.password)):
            raise Exception("Invalid credentials")
        
        userId = str(user['_id'])
        session_token, refresh_token = self.__create_session(userId)
        return userId, (session_token, refresh_token)
    
    def __create_session(self, uid: str) -> Tuple[Optional[str], Optional[str]]:
        session_token = secrets.token_hex(16)
        refresh_token = secrets.token_hex(32)

        try:
            self.__redis.setex(f"session:{session_token}", self.FIELD_SESSION_TTL, uid)
            self.__redis.setex(f"refresh:{refresh_token}", self.FIELD_REFRESH_TTL, uid)

            return session_token, refresh_token
        except Exception as e:
            raise e

    def _validate_session(self, session_token: str) -> Optional[str]:
        """Validate the session token and return the user ID if valid.

        Args:
            session_token (str): cookie session token

        Returns:
            Optional[str]: user ID if the session is valid, None otherwise.
        """
        user_id = self.__redis.get(f"session:{session_token}")
        if user_id:
            self.__redis.expire(f"session:{session_token}", self.FIELD_SESSION_TTL)
            return str(user_id)
        
        return None
    
    def _refresh_session(self, response: Response, refresh_token: str) -> Tuple[Optional[str], Optional[str]]:
        """Refresh the session token using the refresh token.

        Args:
            response (Response): _description_
            refresh_token (str): _description_

        Returns:
            Optional[str]: _description_
        """
        user_id = self.__redis.get(f"refresh:{refresh_token}")
        if user_id:
            new_session_token = secrets.token_hex(16)
            self.__redis.setex(f"session:{new_session_token}", self.FIELD_SESSION_TTL, user_id)

            return user_id, new_session_token
        return None
    
    def _delete_session(self, session_token: str, refresh_token: str) -> bool:
        """
        Delete the session and refresh tokens from Redis.

        Args:
            session_token (str): _description_
            refresh_token (str): _description_

        Returns:
            bool: _description_
        """
        deleted = False
        if session_token:
            if self.__redis.delete(f"session:{session_token}"):
                deleted = True
        if refresh_token:
            if self.__redis.delete(f"refresh:{refresh_token}"):
                deleted = True
        return deleted
    
    def _add_session_to_cookie(self, response: Response, session_token: str, refresh_token: str) -> dict:
        """Set the session and refresh tokens in cookies of client.

        Args:
            response (Response): _description_
            session_token (str): _description_
            refresh_token (str): _description_

        Returns:
            dict: _description_
        """
        response.set_cookie(
            key="session_token",
            value=session_token,
            httponly=True,
            secure=self.SECURE_MODE,
            samesite=self.SAMESITE_MODE
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            httponly=True,
            secure=self.SECURE_MODE,
            samesite=self.SAMESITE_MODE
        )

        return response
    
    def _del_session_in_cookie(self, response: Response) -> dict:
        """
        Delete the session and refresh tokens in cookies of client.

        Args:
            response (Response): _description_

        Returns:
            dict: _description_
        """
        response.delete_cookie(
            key="session_token",
            httponly=True,
            secure=self.SECURE_MODE,
            samesite=self.SAMESITE_MODE
        )
        response.delete_cookie(
            key="refresh_token",
            httponly=True,
            secure=self.SECURE_MODE,
            samesite=self.SAMESITE_MODE
        )

        return response