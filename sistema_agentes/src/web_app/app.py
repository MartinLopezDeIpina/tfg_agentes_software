import os

from src.web_app.app_config import Config
from src.web_app.frontend_routes import bp
from flask import Flask

app = Flask(__name__)
app.config.from_object(Config)
app.register_blueprint(bp)

if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=app.config['DEBUG'])