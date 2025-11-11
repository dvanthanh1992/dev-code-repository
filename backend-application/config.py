import os

class Config:
    APP_NAME = os.getenv("APP_NAME", "Flask CI Demo")
    STAGE_ENVIRONMENT = os.getenv("STAGE_ENVIRONMENT", "development")
    REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
