# ImageOpt

A web-based image optimizer built with Flask and Pillow. Upload JPEG, PNG, or WEBP images and compress, resize, adjust, crop, and convert them — all in the browser.

## Features

- **Lossless & lossy compression** — quality slider + Speed / Balanced / Max Quality presets
- **Resize** — scale up or down while preserving aspect ratio
- **Format conversion** — output as JPEG, PNG, or WebP regardless of input format
- **Adjustments** — brightness, contrast, sharpness, and Gaussian blur sliders
- **Interactive crop** — drag-to-crop modal powered by Cropper.js
- **EXIF handling** — strip or keep image metadata; always auto-orients on load
- **Rate limiting** — 30 requests / minute per IP
- **Auto cleanup** — temporary files deleted after 10 minutes

## Tech Stack

- **Backend:** Python 3.11, Flask 3, Pillow, flask-limiter
- **Frontend:** Vanilla JS, Cropper.js (served locally)
- **Deployment:** Render (via `render.yaml`)

## Running Locally

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000`.

## Deploying to Render

1. Fork / clone this repo and push to GitHub
2. Go to [render.com](https://render.com) → New → Web Service
3. Connect your GitHub repo
4. Render auto-detects `render.yaml` — click **Deploy**

The app will be live at `https://imageopt.onrender.com` (or similar free-tier URL).

## Supported Formats

| Format | Input | Output |
|--------|-------|--------|
| JPEG   | yes   | yes    |
| PNG    | yes   | yes    |
| WebP   | yes   | yes    |

Max file size: **25 MB**
