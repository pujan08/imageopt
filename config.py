import os
import secrets


class Config:
    SECRET_KEY = secrets.token_hex(32)
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024          # 25 MB hard limit
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_uploads")
    ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
    REJECTED_EXTENSIONS = {"svg", "gif", "bmp", "tiff", "ico"}
    TEMP_FILE_MAX_AGE = 600     # seconds – 10 minutes
    CLEANUP_INTERVAL = 300      # seconds – run cleanup every 5 minutes
    RATELIMIT_STORAGE_URI = "memory://"
    RATELIMIT_DEFAULT = ["200 per day", "50 per hour"]
