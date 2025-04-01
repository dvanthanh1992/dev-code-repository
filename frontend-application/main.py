import os
import socket
import requests
from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    app_name = os.getenv("APP_NAME")
    environment = os.getenv("STAGE_ENVIRONMENT")
    hostname = socket.gethostname()
    pod_ip = socket.gethostbyname(hostname)
    
    image_version = "4.1.0"
    
    # Thử lấy thông tin status từ backend
    backend_status = "Unknown"
    try:
        backend_url = os.getenv("BACKEND_SERVICE_URL", "http://backend-service")
        response = requests.get(f"{backend_url}/api/status", timeout=2)
        if response.status_code == 200:
            backend_status = "Operational"
    except:
        backend_status = "Unavailable"

    return f"""
    <html>
    <head>
        <title>{app_name} - Deployment Info</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #add8e6;
                padding: 20px;
                color: #333;
            }}
            h1, h2, p {{
                color: #333;
            }}
            .status-box {{
                background-color: #fff;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                padding: 20px;
                margin-top: 20px;
            }}
            .status-indicator {{
                display: inline-block;
                width: 12px;
                height: 12px;
                border-radius: 50%;
                margin-right: 8px;
            }}
            .status-operational {{
                background-color: #4CAF50;
            }}
            .status-unavailable {{
                background-color: #f44336;
            }}
            .container {{
                max-width: 800px;
                margin: 0 auto;
            }}
            .header {{
                background-color: #fff;
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Application Name: <b>{app_name}</b></h1>
                <h2>Environment: <b>{environment}</b></h2>
                <h2>Image Version: <b>{image_version}</b></h2>
            </div>
            
            <div class="status-box">
                <h3>Frontend Status</h3>
                <p><b>Pod Name: </b>{hostname}</p>
                <p><b>Pod IP: </b>{pod_ip}</p>
            </div>
            
            <div class="status-box">
                <h3>Backend Status</h3>
                <p>
                    <span class="status-indicator {
                        'status-operational' if backend_status == 'Operational' else 'status-unavailable'
                    }"></span>
                    <b>Status: </b>{backend_status}
                </p>
            </div>
        </div>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)