from flask import Flask
from flask_cors import CORS
from app.config import Config
from app.routes.server.server import server_bp
from app.routes.data.data import data_bp
from app.routes.analyze.analyze import analyze_bp
from app.routes.visualization.visualization import visualization_bp

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    CORS(app)
    
    app.register_blueprint(server_bp)
    app.register_blueprint(data_bp)
    app.register_blueprint(analyze_bp)
    app.register_blueprint(visualization_bp)
    return app 