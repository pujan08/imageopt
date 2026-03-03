# Session Note — 2026-03-03

## Features Implemented

### 1. Image Adjustments
- Added brightness, contrast, sharpness, and blur sliders to the controls panel
- Sliders range: brightness/contrast/sharpness 0–200 (100 = no change), blur 0–20
- Applied via PIL `ImageEnhance` and `ImageFilter.GaussianBlur` in the processing pipeline
- Live value display and param summary tags (e.g. `B+20`, `C-10`, `Blur5`)

### 2. Format Conversion
- Added format pill selector: Same / JPEG / PNG / WebP
- Output format is independent of input — e.g. upload PNG, download as WEBP
- Mode normalization and save kwargs keyed on output format (not input)
- Output filename extension changes to match selected format

### 3. Interactive Crop (Cropper.js)
- Drag-to-crop modal using Cropper.js 1.6.2
- Crop coordinates stored as percentages (0–1) and passed to the server as `crop_x/y/w/h`
- Server applies crop before metadata capture and resize
- Active crop shown via badge; clearable independently of re-optimize
- "Crop Image" button disabled until an image is loaded

## Files Changed
- `routes/main.py` — new imports, extended `_process_image`, updated `_parse_optimization_params`, updated upload/reoptimize routes
- `templates/index.html` — new control rows, crop modal, local Cropper.js references
- `static/css/style.css` — format pills, ctrl-row-label, btn-sm, crop badge, crop modal styles
- `static/js/upload.js` — new state/DOM refs, all new handlers, updated form submission and resetUI

## Bug Fixed
- Cropper.js originally loaded from CDN; Edge Tracking Prevention blocked it
- Resolved by downloading files locally to `static/css/cropper.min.css` and `static/js/cropper.min.js`
