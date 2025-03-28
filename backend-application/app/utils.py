import os

def get_env_variable(name, default=None):
    return os.getenv(name, default)