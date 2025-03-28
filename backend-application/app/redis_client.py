import os
import redis

redis_instance = None

def init_redis():
    global redis_instance
    redis_host = os.getenv("REDIS_HOST", "localhost")
    redis_port = int(os.getenv("REDIS_PORT", 6379))
    redis_instance = redis.Redis(host=redis_host, port=redis_port, db=0)