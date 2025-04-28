import redis

try:
    redis_client = redis.StrictRedis(host='localhost', port=6379, db=0)
    redis_client.ping()
    print("Connected to Redis!")
except Exception as e:
    print(f"Error: {e}")