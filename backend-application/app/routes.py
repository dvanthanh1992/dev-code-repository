import socket
from flask import Blueprint, request
from app import redis_client
from app.utils import get_env_variable
import random

main_blueprint = Blueprint("main", __name__)

# Version to color mapping (10 versions)
VERSION_COLOR_MAP = {
    "1.0.0": {"color": "blue", "hex": "#4169E1"},
    "2.0.0": {"color": "green", "hex": "#32CD32"},
    "3.0.0": {"color": "yellow", "hex": "#FFD700"},
    "4.0.0": {"color": "red", "hex": "#DC143C"},
    "5.0.0": {"color": "purple", "hex": "#9370DB"},
    "6.0.0": {"color": "orange", "hex": "#FF8C00"},
    "7.0.0": {"color": "cyan", "hex": "#00CED1"},
    "8.0.0": {"color": "pink", "hex": "#FF69B4"},
    "9.0.0": {"color": "lime", "hex": "#7FFF00"},
    "10.0.0": {"color": "magenta", "hex": "#FF00FF"}
}

@main_blueprint.route("/")
def home():
    app_name = get_env_variable("APP_NAME", "Flask CI Demo")
    environment = get_env_variable("STAGE_ENVIRONMENT", "development")
    hostname = socket.gethostname()
    pod_ip = socket.gethostbyname(hostname)
    

    image_version = "7.0.0"
    
    version_info = VERSION_COLOR_MAP.get(image_version, {"color": "blue", "hex": "#4169E1"})
    color = version_info["color"]
    bg_color = version_info["hex"]
    
    redis_info = redis_client.redis_instance.info()
    redis_clients = redis_info.get("connected_clients", "N/A")
    redis_uptime = redis_info.get("uptime_in_seconds", "N/A")
    connection_count = redis_client.redis_instance.incr("connection_count")
    
    # Generate 10 balls with random delays for canary effect
    balls_html = ""
    for i in range(10):
        delay = i * 0.3
        balls_html += f'<div class="ball" style="top: {20 + i * 16}px; animation-delay: {delay}s;"></div>'
    
    return f"""
    <html>
    <head>
        <title>{app_name} - Rollout Demo</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #add8e6;
                padding: 20px;
                margin: 0;
                min-height: 100vh;
                color: white;
            }}
            .container {{
                max-width: 1000px;
                margin: 0 auto;
            }}
            h1 {{
                text-align: center;
                font-size: 48px;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
            }}
            .info-box {{
                background: rgba(255,255,255,0.1);
                backdrop-filter: blur(10px);
                border-radius: 15px;
                padding: 20px;
                margin: 20px 0;
                border: 2px solid rgba(255,255,255,0.2);
            }}
            .ball-container {{
                position: relative;
                height: 200px;
                background: rgba(0,0,0,0.2);
                border-radius: 15px;
                overflow: hidden;
                margin: 30px 0;
            }}
            .ball {{
                position: absolute;
                width: 50px;
                height: 50px;
                background: radial-gradient(circle at 30% 30%, #ffffff, {bg_color});
                border-radius: 50%;
                animation: roll 4s linear infinite;
                box-shadow: 0 5px 15px rgba(0,0,0,0.4);
            }}
            @keyframes roll {{
                0% {{ left: -60px; transform: rotate(0deg); }}
                100% {{ left: 100%; transform: rotate(720deg); }}
            }}
            .metric {{
                display: inline-block;
                margin: 10px 20px;
                font-size: 18px;
            }}
            .metric-value {{
                font-weight: bold;
                font-size: 24px;
                color: {bg_color};
            }}
            .version-badge {{
                display: inline-block;
                background: {bg_color};
                padding: 10px 20px;
                border-radius: 25px;
                font-size: 24px;
                font-weight: bold;
                margin: 10px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            }}
            .version-legend {{
                display: grid;
                grid-template-columns: repeat(5, 1fr);
                gap: 10px;
                margin: 20px 0;
            }}
            .version-item {{
                padding: 8px;
                border-radius: 8px;
                text-align: center;
                font-size: 12px;
                font-weight: bold;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 {app_name}</h1>
            
            <div style="text-align: center;">
                <span class="version-badge">{image_version}</span>
                <span class="version-badge">{color.upper()}</span>
            </div>
            
            <div class="ball-container">
                {balls_html}
            </div>
            
            <div class="info-box">
                <h2 style="margin-top: 0;">📊 Deployment Info</h2>
                <div class="metric">
                    <div>Environment</div>
                    <div class="metric-value">{environment}</div>
                </div>
                <div class="metric">
                    <div>Version</div>
                    <div class="metric-value">{image_version}</div>
                </div>
                <div class="metric">
                    <div>Pod</div>
                    <div class="metric-value">{hostname}</div>
                </div>
                <div class="metric">
                    <div>IP</div>
                    <div class="metric-value">{pod_ip}</div>
                </div>
            </div>
            
            <div class="info-box">
                <h2 style="margin-top: 0;">🔴 Redis Metrics</h2>
                <div class="metric">
                    <div>Total Connections</div>
                    <div class="metric-value">{connection_count}</div>
                </div>
                <div class="metric">
                    <div>Active Clients</div>
                    <div class="metric-value">{redis_clients}</div>
                </div>
                <div class="metric">
                    <div>Uptime (sec)</div>
                    <div class="metric-value">{redis_uptime}</div>
                </div>
            </div>
            
            <div class="info-box">
                <h2 style="margin-top: 0;">🎨 Version Color Map</h2>
                <div class="version-legend">
                    {"".join([f'<div class="version-item" style="background: {v["hex"]};">{k}<br>{v["color"]}</div>' 
                             for k, v in VERSION_COLOR_MAP.items()])}
                </div>
            </div>
        </div>
        
        <script>
            setTimeout(() => location.reload(), 5000);
        </script>
    </body>
    </html>
    """
