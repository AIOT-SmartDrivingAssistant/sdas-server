from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

hashed_password = pwd_context.hash("testpassword")
print("Hashed Password:", hashed_password)

is_valid = pwd_context.verify("testpassword", hashed_password)
print("Password Valid:", is_valid)