import socket
from flask import Blueprint, request
from app import redis_client  # Import the module instead of the variable directly
from app.utils import get_env_variable

main_blueprint = Blueprint("main", __name__)

@main_blueprint.route("/")
def home():
    # Get application name and environment
    app_name    = get_env_variable("APP_NAME", "Flask CI Demo")
    environment = get_env_variable("STAGE_ENVIRONMENT", "development")
    hostname    = socket.gethostname()
    pod_ip      = socket.gethostbyname(hostname)

    image_version = "3.0.0"
    # Use the current redis_instance from redis_client module
    redis_info = redis_client.redis_instance.info()
    redis_clients = redis_info.get("connected_clients", "N/A")
    redis_uptime = redis_info.get("uptime_in_seconds", "N/A")
    connection_count = redis_client.redis_instance.incr("connection_count")

    return f"""
    <html>
    <head>
        <title>{app_name} - Deployment Info</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #dcdcdc;
                padding: 20px;
            }}
            h1, h2, p {{
                color: #333;
            }}
            .connection-box {{
                border: 2px solid #333;
                padding: 10px;
                margin-top: 20px;
                background-color: #fff;
            }}
            .connection-count {{
                font-weight: bold;
                font-size: 28px;
            }}
            .connection-info {{
                font-size: 14px;
                color: #555;
                margin-top: 10px;
            }}
        </style>
    </head>
    <body>
        <h1>Application Name       : <b>{app_name}</b></h1>
        <h2>Environment            : <b>{environment}</b></h2>
        <h2>Image Version          : <b>{image_version}</b></h2>
        <p><b>Pod Name             : </b>{hostname}</p>
        <p><b>Pod IP               : </b>{pod_ip}</p>
        <div class="connection-box">
            <p><b>Redis Connection Count :</b> <span class="connection-count">{connection_count}</span></p>
            <p class="connection-info"><b>Connected Clients:</b> {redis_clients}</p>
            <p class="connection-info"><b>Server Uptime (sec):</b> {redis_uptime}</p>
        </div>
    </body>
    </html>
    """
