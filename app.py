import logging
import os

from flask import Flask, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from routes.main import main_bp
from utils.cleanup import TempFileCleanup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

limiter = Limiter(key_func=get_remote_address)


def create_app(config_class=Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ------------------------------------------------------------------ limits
    limiter.init_app(app)
    # 30 requests/min per IP specifically on the upload route
    limiter.limit("30 per minute")(main_bp)

    # ----------------------------------------------------------- blueprints
    app.register_blueprint(main_bp)

    # --------------------------------------------------- temp upload folder
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # ----------------------------------------------- background cleanup
    cleaner = TempFileCleanup(
        upload_folder=app.config["UPLOAD_FOLDER"],
        max_age=app.config["TEMP_FILE_MAX_AGE"],
        interval=app.config["CLEANUP_INTERVAL"],
    )
    cleaner.start()

    # --------------------------------------------------------- error handlers
    @app.errorhandler(413)
    def payload_too_large(e):
        return jsonify({"error": "File exceeds the 25 MB size limit."}), 413

    @app.errorhandler(429)
    def rate_limited(e):
        return (
            jsonify({"error": "Too many requests. Please wait a moment and try again."}),
            429,
        )

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error."}), 500

    return app


if __name__ == "__main__":
    application = create_app()
    application.run(debug=True, host="0.0.0.0", port=5000)
