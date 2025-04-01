import os
import socket
import json
from flask import Flask, request, jsonify
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
    
    image_version = "1.1.0"
    
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
            .api-info {{
                background-color: #f5f5f5;
                padding: 15px;
                margin-top: 20px;
                border-left: 4px solid #4CAF50;
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
        <div class="api-info">
            <h3>API Endpoints</h3>
            <p><b>GET /api/status</b> - System status information</p>
            <p><b>POST /api/messages</b> - Send a new message</p>
            <p><b>GET /api/messages</b> - Get all messages</p>
        </div>
    </body>
    </html>
    """

@app.route("/api/status")
def status():
    app_name = os.getenv("APP_NAME")
    environment = os.getenv("STAGE_ENVIRONMENT")
    hostname = socket.gethostname()
    
    status_info = {
        "application": app_name,
        "environment": environment,
        "status": "operational",
        "hostname": hostname,
        "version": "1.1.0"
    }
    
    return jsonify(status_info)
    
@app.route("/api/messages", methods=["GET", "POST"])
def messages():
    if request.method == "POST":
        try:
            data = request.json
            if not data or not data.get("message"):
                return jsonify({"status": "error", "error": "Missing message content"}), 400
                
            message_id = r.incr("message_id_counter")
            message_data = {
                "id": message_id,
                "message": data.get("message"),
                "timestamp": r.time()[0]
            }
            
            r.hset(f"message:{message_id}", mapping=message_data)
            r.lpush("messages", message_id)
            
            return jsonify({"status": "success", "message_id": message_id}), 201
            
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500
    else:
        try:
            message_ids = r.lrange("messages", 0, -1)
            messages = []
            
            for message_id in message_ids:
                message_data = r.hgetall(f"message:{message_id.decode()}")
                if message_data:
                    messages.append({k.decode(): v.decode() for k, v in message_data.items()})
            
            return jsonify(messages)
            
        except Exception as e:
            return jsonify({"status": "error", "error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)