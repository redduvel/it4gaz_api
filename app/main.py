import os
from app import create_app

app = create_app()

if __name__ == "__main__":
    debug_mode = os.getenv('FLASK_DEBUG', 'True') == 'True'
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', debug=debug_mode, port=port)