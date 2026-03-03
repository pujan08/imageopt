import io
from PIL import Image

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp"}
REJECTED_EXTENSIONS = {"svg", "gif", "bmp", "tiff", "ico"}
ALLOWED_PIL_FORMATS = {"JPEG", "PNG", "WEBP"}


def validate_image(file_storage):
    """Validate an uploaded FileStorage object.

    Returns:
        (True, None) on success.
        (False, error_message) on failure.
    """
    filename = (file_storage.filename or "").strip().lower()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else ""

    if ext in REJECTED_EXTENSIONS:
        return False, (
            f"'{ext.upper()}' files are not supported. "
            "Please upload a JPEG, PNG, or WEBP image."
        )

    if ext not in ALLOWED_EXTENSIONS:
        return False, "Only JPEG, PNG, and WEBP images are accepted."

    # Read raw bytes so we can open multiple times without consuming the stream
    file_storage.seek(0)
    raw = file_storage.read()
    file_storage.seek(0)

    if not raw:
        return False, "The uploaded file is empty."

    # 1st pass – structural integrity check via verify()
    try:
        img_check = Image.open(io.BytesIO(raw))
        img_check.verify()          # advances & closes the internal stream
    except Exception:
        return False, "The file is corrupted or is not a valid image."

    # 2nd pass – confirm PIL-reported format
    try:
        img_fmt = Image.open(io.BytesIO(raw))
        detected = img_fmt.format
    except Exception:
        return False, "Could not determine image format."

    if detected not in ALLOWED_PIL_FORMATS:
        return False, (
            f"Detected format '{detected}' is not supported. "
            "Please use JPEG, PNG, or WEBP."
        )

    return True, None
