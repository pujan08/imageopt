from __future__ import annotations

import io
import logging
import os
import re
import uuid
from pathlib import Path

from flask import (
    Blueprint,
    after_this_request,
    current_app,
    jsonify,
    render_template,
    request,
    send_file,
)
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from PIL.PngImagePlugin import PngInfo

from utils.validators import validate_image

main_bp = Blueprint("main", __name__)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------

PRESETS = {
    "speed": {
        "quality_hint": 65,
        "desc": "Fast encoding; reduced quality.",
        "jpeg": {"subsampling": 2,  "optimize": False, "progressive": False},
        "webp": {"method": 0},
        "png":  {"compress_level": 2},
    },
    "balanced": {
        "quality_hint": 85,
        "desc": "Best quality/size tradeoff (default).",
        "jpeg": {"subsampling": -1, "optimize": True,  "progressive": True},
        "webp": {"method": 4},
        "png":  {"compress_level": 6},
    },
    "max_quality": {
        "quality_hint": 92,
        "desc": "Best output quality; slower encoding.",
        "jpeg": {"subsampling": 0,  "optimize": True,  "progressive": True},
        "webp": {"method": 6},
        "png":  {"compress_level": 9},
    },
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fmt_bytes(size: int) -> str:
    """Human-readable byte size (B / KB / MB)."""
    for unit in ("B", "KB", "MB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


_SAFE_RE = re.compile(r'^(orig_|opt_)?[0-9a-f]{32}\.(jpg|png|webp)$')


def _safe_filename(raw: str) -> str | None:
    """Return the bare filename if it looks safe, else None."""
    name = Path(raw).name
    if name != raw:
        return None
    if not _SAFE_RE.match(name):
        return None
    return name


def _prepare_for_jpeg(img: Image.Image) -> Image.Image:
    """Composite transparent images onto a white background for JPEG output."""
    if img.mode in ("RGBA", "LA", "P"):
        rgba = img.convert("RGBA")
        bg = Image.new("RGB", rgba.size, (255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[3])
        return bg
    if img.mode == "CMYK":
        return img.convert("RGB")
    if img.mode not in ("RGB", "L"):
        return img.convert("RGB")
    return img


def _process_image(
    raw: bytes,
    *,
    quality: int,
    resize: int,
    strip_metadata: bool,
    preset: dict,
    output_format: str | None = None,  # "JPEG"|"PNG"|"WEBP" or None = keep input fmt
    crop: tuple[float, float, float, float] | None = None,  # (x_pct,y_pct,w_pct,h_pct) 0-1
    brightness: float = 1.0,
    contrast: float = 1.0,
    sharpness: float = 1.0,
    blur: float = 0.0,
) -> tuple[bytes, str, int, int]:
    """Process image bytes. Returns (output_bytes, format, width, height)."""
    img = Image.open(io.BytesIO(raw))
    input_fmt = img.format  # "JPEG" | "PNG" | "WEBP"

    # 1. Auto-orient EXIF
    img = ImageOps.exif_transpose(img)

    # 2. Crop (before metadata capture so dimensions are final)
    if crop is not None:
        cx, cy, cw, ch = crop
        iw, ih = img.size
        x1 = round(cx * iw)
        y1 = round(cy * ih)
        x2 = round((cx + cw) * iw)
        y2 = round((cy + ch) * ih)
        x1, x2 = max(0, x1), min(iw, x2)
        y1, y2 = max(0, y1), min(ih, y2)
        if x2 > x1 and y2 > y1:
            img = img.crop((x1, y1, x2, y2))

    # 3. Capture metadata if keeping it (post-orient/crop)
    fmt = input_fmt
    exif_bytes = None
    png_info = None
    if not strip_metadata:
        if fmt in ("JPEG", "WEBP"):
            exif_bytes = img.info.get("exif")
        elif fmt == "PNG":
            text_meta = {k: v for k, v in img.info.items() if isinstance(v, str)}
            if text_meta:
                png_info = PngInfo()
                for k, v in text_meta.items():
                    png_info.addText(k, v)

    # 4. Resize (aspect preserved)
    if resize != 100:
        new_w = max(1, round(img.width * resize / 100))
        new_h = max(1, round(img.height * resize / 100))
        resample = Image.Resampling.LANCZOS if resize < 100 else Image.Resampling.BICUBIC
        img = img.resize((new_w, new_h), resample)

    # 5. Determine output format
    out_fmt = output_format or input_fmt

    width, height = img.size

    # 6. Normalize mode (keyed on out_fmt to enable format conversion)
    if out_fmt == "JPEG":
        img = _prepare_for_jpeg(img)
    elif out_fmt == "PNG":
        if img.mode not in ("RGB", "RGBA", "L", "LA", "P"):
            img = img.convert("RGBA")
    elif out_fmt == "WEBP":
        if img.mode not in ("RGB", "RGBA", "L"):
            img = img.convert("RGBA" if img.mode == "P" else "RGB")

    # 7. Adjustments
    if brightness != 1.0:
        img = ImageEnhance.Brightness(img).enhance(brightness)
    if contrast != 1.0:
        img = ImageEnhance.Contrast(img).enhance(contrast)
    if sharpness != 1.0:
        img = ImageEnhance.Sharpness(img).enhance(sharpness)
    if blur > 0.0:
        img = img.filter(ImageFilter.GaussianBlur(radius=blur))

    # 8. Build save kwargs
    save_kwargs: dict = {}
    if out_fmt == "JPEG":
        save_kwargs = {**preset["jpeg"], "quality": quality}
        if exif_bytes and input_fmt == out_fmt:
            save_kwargs["exif"] = exif_bytes
    elif out_fmt == "WEBP":
        save_kwargs = {**preset["webp"], "quality": quality}
        if exif_bytes and input_fmt == out_fmt:
            save_kwargs["exif"] = exif_bytes
    elif out_fmt == "PNG":
        compress_level = max(1, min(9, round(quality * 9 / 95)))
        save_kwargs = {"compress_level": compress_level}
        if png_info and input_fmt == out_fmt:
            save_kwargs["pnginfo"] = png_info

    # 9. Encode
    output = io.BytesIO()
    img.save(output, format=out_fmt, **save_kwargs)
    return output.getvalue(), out_fmt, width, height


def _parse_optimization_params():
    """Parse optimization params from request form."""
    quality = request.form.get("quality", 85, type=int)
    quality = max(1, min(95, quality))

    resize = request.form.get("resize", 100, type=int)
    resize = max(10, min(200, resize))

    strip_raw = request.form.get("strip_metadata", "true").lower()
    strip_metadata = strip_raw not in ("false", "0", "no")

    preset_name = request.form.get("preset", "balanced")
    if preset_name not in PRESETS:
        preset_name = "balanced"
    preset = PRESETS[preset_name]

    out_fmt = request.form.get("output_format", "").upper()
    if out_fmt not in ("JPEG", "PNG", "WEBP"):
        out_fmt = None

    brightness = max(0.0, min(3.0, request.form.get("brightness", 1.0, type=float)))
    contrast   = max(0.0, min(3.0, request.form.get("contrast",   1.0, type=float)))
    sharpness  = max(0.0, min(3.0, request.form.get("sharpness",  1.0, type=float)))
    blur       = max(0.0, min(20.0, request.form.get("blur",      0.0, type=float)))

    cx = request.form.get("crop_x", type=float)
    cy = request.form.get("crop_y", type=float)
    cw = request.form.get("crop_w", type=float)
    ch = request.form.get("crop_h", type=float)
    crop = (cx, cy, cw, ch) if None not in (cx, cy, cw, ch) and cw > 0 and ch > 0 else None

    return quality, resize, strip_metadata, preset, preset_name, out_fmt, crop, brightness, contrast, sharpness, blur


def _build_result(
    orig_filename: str,
    opt_filename: str,
    fmt: str,
    width: int,
    height: int,
    original_size: int,
    optimized_size: int,
    quality: int,
    resize: int,
    strip_metadata: bool,
    preset_name: str,
) -> dict:
    savings = max(0.0, (1 - optimized_size / original_size) * 100) if original_size else 0.0
    return {
        "success": True,
        "orig_filename": orig_filename,
        "opt_filename": opt_filename,
        "format": fmt,
        "dimensions": f"{width} \u00d7 {height}",
        "original_size_fmt": _fmt_bytes(original_size),
        "optimized_size_fmt": _fmt_bytes(optimized_size),
        "savings_percent": round(savings, 1),
        "params_applied": {
            "quality": quality,
            "resize": resize,
            "strip_metadata": strip_metadata,
            "preset": preset_name,
        },
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/upload", methods=["POST"])
def upload():
    if "image" not in request.files:
        return jsonify({"error": "No file provided."}), 400

    file = request.files["image"]
    if not file.filename:
        return jsonify({"error": "No file selected."}), 400

    valid, error = validate_image(file)
    if not valid:
        return jsonify({"error": error}), 400

    quality, resize, strip_metadata, preset, preset_name, out_fmt, crop, brightness, contrast, sharpness, blur = _parse_optimization_params()

    try:
        file.seek(0)
        raw = file.read()
        original_size = len(raw)

        img_probe = Image.open(io.BytesIO(raw))
        input_fmt = img_probe.format
        img_probe.close()

        ext_map = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
        input_ext = ext_map.get(input_fmt)
        if not input_ext:
            return jsonify({"error": "Unsupported image format."}), 400

        uid = uuid.uuid4().hex
        upload_folder = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)

        # Save original for re-optimization
        orig_filename = f"orig_{uid}.{input_ext}"
        orig_path = os.path.join(upload_folder, orig_filename)
        with open(orig_path, "wb") as fout:
            fout.write(raw)

        # Process and save optimized
        opt_bytes, fmt_out, width, height = _process_image(
            raw, quality=quality, resize=resize,
            strip_metadata=strip_metadata, preset=preset,
            output_format=out_fmt, crop=crop,
            brightness=brightness, contrast=contrast,
            sharpness=sharpness, blur=blur,
        )
        out_ext = ext_map.get(fmt_out, input_ext)
        opt_filename = f"opt_{uid}.{out_ext}"
        opt_path = os.path.join(upload_folder, opt_filename)
        with open(opt_path, "wb") as fout:
            fout.write(opt_bytes)

        return jsonify(_build_result(
            orig_filename, opt_filename, fmt_out, width, height,
            original_size, len(opt_bytes), quality, resize, strip_metadata, preset_name,
        ))

    except Exception as exc:
        logger.exception("Image processing error: %s", exc)
        return jsonify({"error": "Image processing failed. Please try a different file."}), 500


@main_bp.route("/reoptimize", methods=["POST"])
def reoptimize():
    orig_filename = request.form.get("orig_filename", "")
    old_opt_filename = request.form.get("old_opt_filename", "")

    safe_orig = _safe_filename(orig_filename)
    if not safe_orig or not safe_orig.startswith("orig_"):
        return jsonify({"error": "Invalid original filename."}), 400

    safe_old_opt = _safe_filename(old_opt_filename) if old_opt_filename else None

    upload_folder = current_app.config["UPLOAD_FOLDER"]
    orig_path = os.path.join(upload_folder, safe_orig)
    if not os.path.isfile(orig_path):
        return jsonify({"error": "Original file not found or expired. Please re-upload."}), 404

    quality, resize, strip_metadata, preset, preset_name, out_fmt, crop, brightness, contrast, sharpness, blur = _parse_optimization_params()

    try:
        with open(orig_path, "rb") as fin:
            raw = fin.read()
        original_size = len(raw)

        # Delete old optimized file
        if safe_old_opt:
            old_opt_path = os.path.join(upload_folder, safe_old_opt)
            if os.path.isfile(old_opt_path):
                os.unlink(old_opt_path)

        # Process
        opt_bytes, fmt_out, width, height = _process_image(
            raw, quality=quality, resize=resize,
            strip_metadata=strip_metadata, preset=preset,
            output_format=out_fmt, crop=crop,
            brightness=brightness, contrast=contrast,
            sharpness=sharpness, blur=blur,
        )

        # uid from original filename; ext from output format
        ext_map = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
        uid = safe_orig[5:37]  # strip "orig_", take 32 hex chars
        out_ext = ext_map.get(fmt_out, safe_orig.rsplit(".", 1)[1])
        opt_filename = f"opt_{uid}.{out_ext}"
        opt_path = os.path.join(upload_folder, opt_filename)
        with open(opt_path, "wb") as fout:
            fout.write(opt_bytes)

        return jsonify(_build_result(
            safe_orig, opt_filename, fmt_out, width, height,
            original_size, len(opt_bytes), quality, resize, strip_metadata, preset_name,
        ))

    except Exception as exc:
        logger.exception("Reoptimize error: %s", exc)
        return jsonify({"error": "Image processing failed. Please try again."}), 500


@main_bp.route("/preview/<path:filename>")
def preview(filename: str):
    safe = _safe_filename(filename)
    if not safe:
        return jsonify({"error": "Invalid filename."}), 400

    path = os.path.join(current_app.config["UPLOAD_FOLDER"], safe)
    if not os.path.isfile(path):
        return jsonify({"error": "File not found or already expired."}), 404

    return send_file(path)


@main_bp.route("/download/<path:filename>")
def download(filename: str):
    safe = _safe_filename(filename)
    if not safe:
        return jsonify({"error": "Invalid filename."}), 400

    path = os.path.join(current_app.config["UPLOAD_FOLDER"], safe)
    if not os.path.isfile(path):
        return jsonify({"error": "File not found or already expired."}), 404

    # Read fully into memory before serving so the file can be deleted immediately
    with open(path, "rb") as fin:
        data = fin.read()
    buf = io.BytesIO(data)
    buf.seek(0)

    # Delete opt_ files after response is sent
    if safe.startswith("opt_"):
        @after_this_request
        def _delete_opt(response):
            try:
                os.unlink(path)
            except OSError:
                pass
            return response

    return send_file(buf, as_attachment=True, download_name=f"optimized_{safe}")
