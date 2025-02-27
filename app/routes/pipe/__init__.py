from flask import Blueprint

pipe_bp = Blueprint('pipe', __name__, url_prefix='/api/pipe')

from app.routes.pipe import pipe_routes 