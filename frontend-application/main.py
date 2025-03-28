import os
import socket
from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():

    app_name = os.getenv("APP_NAME")
    environment = os.getenv("STAGE_ENVIRONMENT")
    hostname = socket.gethostname()
    pod_ip = socket.gethostbyname(hostname)
    
    image_version = "2.0.0"

    return f"""
    <html>
    <head>
        <title>{app_name} - Deployment Info</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #add8e6;
                padding: 20px;
            }}
            h1, h2, p {{
                color: #333;
            }}
        </style>
    </head>
    <body>
        <h1>Application Name       : <b>{app_name}</b></h1>
        <h2>Environment            : <b>{environment}</b></h2>
        <h2>Image Version          : <b>{image_version}</b></h2>
        <p><b>Pod Name             : </b>{hostname}</p>
        <p><b>Pod IP               : </b>{pod_ip}</p>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
