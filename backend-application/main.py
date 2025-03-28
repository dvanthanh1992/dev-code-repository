import os
import socket
from flask import Flask
import redis

app = Flask(__name__)

redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
r = redis.Redis(host=redis_host, port=redis_port, db=0)

@app.route("/")
def home():

    app_name    = os.getenv("APP_NAME")
    environment = os.getenv("STAGE_ENVIRONMENT")
    hostname    = socket.gethostname()
    pod_ip      = socket.gethostbyname(hostname)
    
    image_version = "4.0.0"
    
    redis_info = r.info()
    redis_clients = redis_info.get("connected_clients", "N/A")
    redis_uptime = redis_info.get("uptime_in_seconds", "N/A")
    connection_count = r.incr("connection_count")

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
