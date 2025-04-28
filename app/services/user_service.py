from bson import ObjectId

from services.database import Database

from models.request import UserInfoRequest
from models.mongo_doc import UserDocument
from gridfs import GridOut

class UserService:
    def _get_object_id(self, uid: str = None) -> ObjectId:
        '''
            Convert a user id string into an ObjectId for querying the database.
        '''
        try:
            return ObjectId(uid)
        except Exception as e:
            raise Exception("Invalid string to ObjectId conversion") from e
        
    def _create_init_user_data(self, username: str = None, hashed_password: str = None):
        '''
            Create 2 dict for initial user's data and user config data for register operation.
        '''
        init_user_data = {}
        for field in UserDocument.ALL_BASIC_FIELDS:
            init_user_data[field] = ""

        init_user_data[UserDocument.FIELD_USERNAME] = username
        init_user_data[UserDocument.FIELD_PASSWORD] = hashed_password
        init_user_data[UserDocument.FIELD_AVATAR] = ""

        return init_user_data
    
    def _check_user_exist(self, uid: str = None) -> bool:
        '''
            Check if a user exists in the database by user id string.
        '''
        return Database()._instance.get_user_collection().find_one({'_id': self._get_object_id(uid)})

    def _get_user_info(self, uid: str = None) -> dict:
        '''
            Get user info from the database by user id string.

            Args:
                uid: The user id string.

            Returns:
                A dictionary containing the user's basic info.
        '''
        user = Database()._instance.get_user_collection().find_one({'_id': self._get_object_id(uid)})

        if not user:
            raise Exception("User not find")

        data = {}
        for key in UserDocument.ALL_BASIC_FIELDS:
            if key in user:
                data[key] = user[key]

        return data
    
    def _update_user_info(self, uid: str = None, user_info_request: UserInfoRequest = None):
        '''
            Update user info in the database by user id string and UserInfoRequest object.
        '''
        update_data = user_info_request.dict(exclude_unset=True)
        
        if update_data == {}:
            raise Exception("No data to update")
        
        print(f"update_data: {update_data}")
        
        result = Database()._instance.get_user_collection().update_one(
            {'_id': self._get_object_id(uid)},
            {'$set': update_data}
        )
        if result.modified_count == 0:
            raise Exception("No user info updated")

    def _get_user_info_by_session_token(self, session_token: str = None):
        '''
            Get user info from the database by current user's session, included '_id' field.
        '''
        if not session_token:
            return None
        
        user = Database()._instance.get_user_collection().find_one({'session_token': session_token})
        return user

    def _delete_user_account(self, uid: str = None):
        '''
            Delete all user info from the database by user id string. 
        '''
        session = Database()._instance.client.start_session()
        try:
            with session.start_transaction():
                Database()._instance.get_user_collection().delete_one({'_id': self._get_object_id(uid)}, session=session)
                Database()._instance.get_user_config_collection().delete_one({'uid': uid}, session=session)
                # Database()._instance.get_env_sensor_collection().delete_many({'uid': uid})
        except Exception as e:
            session.abort_transaction()
            raise Exception("Delete user account failed")
        finally:
            session.end_session()

    def _get_avatar(self, uid: str = None) -> GridOut:
        '''
            Get user avatar from the database by user id string.
        '''
        user = Database()._instance.get_user_collection().find_one({'_id': self._get_object_id(uid)})
        if not user:
            raise Exception("User not find")
        
        if not user[UserDocument.FIELD_AVATAR] or user[UserDocument.FIELD_AVATAR] == "":
            raise Exception("No avatar found")
        
        file = Database()._instance.fs.get(ObjectId(user[UserDocument.FIELD_AVATAR]))

        if not file:
            raise Exception("Can not get file")
        
        return file

    async def _update_avatar(self, uid: str = None, file: any = None) -> dict:
        '''
            Update user avatar in the database by user id string and avatar file.
        '''
        user = Database()._instance.get_user_collection().find_one({'_id': self._get_object_id(uid)})

        if not user:
            raise Exception("User not find")
        
        if user[UserDocument.FIELD_AVATAR] and user[UserDocument.FIELD_AVATAR] != "":
            Database()._instance.fs.delete(ObjectId(user[UserDocument.FIELD_AVATAR]))

        contents = await file.read()
        file_id = Database()._instance.fs.put(
            contents,
            filename=file.filename,
            content_type=file.content_type
        )

        Database()._instance.get_user_collection().update_one({'_id': self._get_object_id(uid)}, {'$set': {'avatar': file_id}})

        return {
            "file_id": str(file_id),
            "file_name": file.filename,
            "file_type": file.content_type,
            "file_size": len(contents)
        }
    

    def _delete_avatar(self, uid: str = None):
        '''
            Delete user avatar from the database by user id string.
        '''
        user = Database()._instance.get_user_collection().find_one({'_id': self._get_object_id(uid)})

        if not user:
            raise Exception("User not find")
        
        if not user[UserDocument.FIELD_AVATAR] or user[UserDocument.FIELD_AVATAR] == "":
            raise Exception("No avatar found")
        
        Database()._instance.fs.delete(ObjectId(user[UserDocument.FIELD_AVATAR]))

        Database()._instance.get_user_collection().update_one({'_id': self._get_object_id(uid)}, {'$set': {'avatar': ""}})
