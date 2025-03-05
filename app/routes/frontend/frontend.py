from flask import Blueprint, send_from_directory, current_app
import os

frontend_bp = Blueprint('frontend', __name__)

# Получаем абсолютный путь к директории frontend
FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'frontend')

@frontend_bp.route('/')
def serve_frontend():
    print(f"Attempting to serve index.html from: {FRONTEND_DIR}")
    if not os.path.exists(os.path.join(FRONTEND_DIR, 'index.html')):
        print("index.html not found!")
        return "File not found", 404
    return send_from_directory(FRONTEND_DIR, 'index.html')

@frontend_bp.route('/<path:path>')
def serve_static(path):
    print(f"Attempting to serve {path} from: {FRONTEND_DIR}")
    if not os.path.exists(os.path.join(FRONTEND_DIR, path)):
        print(f"{path} not found!")
        return "File not found", 404
    return send_from_directory(FRONTEND_DIR, path) 