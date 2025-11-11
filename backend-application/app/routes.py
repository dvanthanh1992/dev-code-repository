import socket
from flask import Blueprint, request
from app import redis_client
from app.utils import get_env_variable
import random

main_blueprint = Blueprint("main", __name__)

@main_blueprint.route("/")
def home():
    app_name = get_env_variable("APP_NAME", "Flask CI Demo")
    environment = get_env_variable("STAGE_ENVIRONMENT", "development")
    hostname = socket.gethostname()
    pod_ip = socket.gethostbyname(hostname)
    
    # Version/color variants for rollout simulation
    version = get_env_variable("APP_VERSION", "v1")
    color = get_env_variable("APP_COLOR", "blue")
    
    image_version = "1.0.0"
    redis_info = redis_client.redis_instance.info()
    redis_clients = redis_info.get("connected_clients", "N/A")
    redis_uptime = redis_info.get("uptime_in_seconds", "N/A")
    connection_count = redis_client.redis_instance.incr("connection_count")
    
    # Color mapping
    color_map = {
        "blue": "#4169E1",
        "green": "#32CD32",
        "yellow": "#FFD700",
        "red": "#DC143C",
        "purple": "#9370DB"
    }
    bg_color = color_map.get(color, "#4169E1")
    
    return f"""
    <html>
    <head>
        <title>{app_name} - Rollout Demo</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background: linear-gradient(135deg, {bg_color} 0%, #1a1a2e 100%);
                padding: 20px;
                margin: 0;
                min-height: 100vh;
                color: white;
            }}
            .container {{
                max-width: 800px;
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
                width: 80px;
                height: 80px;
                background: radial-gradient(circle at 30% 30%, #ffffff, {bg_color});
                border-radius: 50%;
                animation: roll 3s linear infinite;
                box-shadow: 0 10px 20px rgba(0,0,0,0.3);
                top: 60px;
            }}
            @keyframes roll {{
                0% {{ left: -100px; transform: rotate(0deg); }}
                100% {{ left: 100%; transform: rotate(360deg); }}
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
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 {app_name}</h1>
            
            <div style="text-align: center;">
                <span class="version-badge">{version}</span>
                <span class="version-badge">{color.upper()}</span>
            </div>
            
            <div class="ball-container">
                <div class="ball"></div>
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
        </div>
        
        <script>
            // Auto-refresh every 5 seconds to see rollout changes
            setTimeout(() => location.reload(), 5000);
        </script>
    </body>
    </html>
    """
