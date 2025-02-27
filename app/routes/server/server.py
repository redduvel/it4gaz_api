from flask import Blueprint, jsonify, request
from app.db_client import DBClient

server_bp = Blueprint('server', __name__, url_prefix='/api/v1')

@server_bp.route('/ping', methods=['GET'])
def ping():
    db_client = DBClient()
    supabase = db_client.get_supabase()
    
    try:
        return jsonify({
            "status": "ok", 
            "message": "pong", 
        })
    
    except Exception as e:
        print(f"Error querying Supabase: {str(e)}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500
