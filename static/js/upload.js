/* =====================================================================
   ImageOpt – upload & preview logic
   ===================================================================== */

"use strict";

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let currentPreset       = "balanced";
let currentOrigFilename = null;
let currentOptFilename  = null;
let currentFormat       = "";    // "" | "JPEG" | "PNG" | "WEBP"
let currentCrop         = null;  // null | {x_pct, y_pct, w_pct, h_pct}
let cropperInstance     = null;
let beforeImgDataUrl    = null;  // data URL stored when file loads

// ---------------------------------------------------------------------------
// DOM refs
// ---------------------------------------------------------------------------
const dropZone      = document.getElementById("drop-zone");
const fileInput     = document.getElementById("file-input");

// Before pane
const dropIdle      = document.getElementById("drop-idle");
const beforeImg     = document.getElementById("before-img");
const beforeSize    = document.getElementById("before-size");

// After pane
const afterPlaceholder = document.getElementById("after-placeholder");
const afterLoading     = document.getElementById("after-loading");
const afterImg         = document.getElementById("after-img");
const afterSize        = document.getElementById("after-size");

// Stats bar
const statsBar      = document.getElementById("stats-bar");
const statFormat    = document.getElementById("stat-format");
const statDims      = document.getElementById("stat-dims");
const statOriginal  = document.getElementById("stat-original");
const statOptimized = document.getElementById("stat-optimized");
const statSavings   = document.getElementById("stat-savings");
const btnDownload   = document.getElementById("btn-download");

// Controls
const qualitySlider    = document.getElementById("quality-slider");
const qualityValue     = document.getElementById("quality-value");
const qualityNote      = document.getElementById("quality-note");
const resizeSlider     = document.getElementById("resize-slider");
const resizeValue      = document.getElementById("resize-value");
const stripMetadata    = document.getElementById("strip-metadata");
const paramSummary     = document.getElementById("param-summary");
const presetDesc       = document.getElementById("preset-desc");

// Adjustment sliders
const brightnessSlider = document.getElementById("brightness-slider");
const brightnessValue  = document.getElementById("brightness-value");
const contrastSlider   = document.getElementById("contrast-slider");
const contrastValue    = document.getElementById("contrast-value");
const sharpnessSlider  = document.getElementById("sharpness-slider");
const sharpnessValue   = document.getElementById("sharpness-value");
const blurSlider       = document.getElementById("blur-slider");
const blurValue        = document.getElementById("blur-value");

// Crop controls
const btnOpenCrop  = document.getElementById("btn-open-crop");
const cropBadge    = document.getElementById("crop-badge");
const btnClearCrop = document.getElementById("btn-clear-crop");

// Crop modal
const cropModal    = document.getElementById("crop-modal");
const cropImg      = document.getElementById("crop-img");
const btnCropCancel = document.getElementById("btn-crop-cancel");
const btnCropReset  = document.getElementById("btn-crop-reset");
const btnCropApply  = document.getElementById("btn-crop-apply");

// Alerts / reset
const alertsArea    = document.getElementById("alerts-area");
const resetRow      = document.getElementById("reset-row");
const btnReset      = document.getElementById("btn-reset");
const btnReoptimize = document.getElementById("btn-reoptimize");

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------
const ALLOWED_TYPES  = new Set(["image/jpeg", "image/png", "image/webp"]);
const REJECTED_TYPES = new Set(["image/svg+xml", "image/gif", "image/bmp"]);
const MAX_BYTES      = 25 * 1024 * 1024;   // 25 MB

const PRESET_DESCS = {
  speed:       "Fast encoding; reduced quality.",
  balanced:    "Best quality/size tradeoff (default).",
  max_quality: "Best output quality; slower encoding.",
};

const PRESET_LABELS = {
  speed:       "Speed",
  balanced:    "Balanced",
  max_quality: "Max Quality",
};

// ---------------------------------------------------------------------------
// Preset pills
// ---------------------------------------------------------------------------
document.querySelectorAll(".preset-pill").forEach((pill) => {
  pill.addEventListener("click", () => {
    document.querySelectorAll(".preset-pill").forEach((p) => p.classList.remove("active"));
    pill.classList.add("active");
    currentPreset = pill.dataset.preset;
    qualitySlider.value = pill.dataset.hint;
    qualityValue.textContent = pill.dataset.hint;
    presetDesc.textContent = PRESET_DESCS[currentPreset] || "";
    updateParamSummary();
  });
});

// ---------------------------------------------------------------------------
// Format pills
// ---------------------------------------------------------------------------
document.querySelectorAll(".format-pill").forEach((pill) => {
  pill.addEventListener("click", () => {
    document.querySelectorAll(".format-pill").forEach((p) => p.classList.remove("active"));
    pill.classList.add("active");
    currentFormat = pill.dataset.format;
    updateParamSummary();
  });
});

// ---------------------------------------------------------------------------
// Slider / toggle handlers
// ---------------------------------------------------------------------------
qualitySlider.addEventListener("input", () => {
  qualityValue.textContent = qualitySlider.value;
  updateParamSummary();
});

resizeSlider.addEventListener("input", () => {
  resizeValue.textContent = resizeSlider.value;
  updateParamSummary();
});

stripMetadata.addEventListener("change", updateParamSummary);

brightnessSlider.addEventListener("input", () => {
  brightnessValue.textContent = brightnessSlider.value;
  updateParamSummary();
});

contrastSlider.addEventListener("input", () => {
  contrastValue.textContent = contrastSlider.value;
  updateParamSummary();
});

sharpnessSlider.addEventListener("input", () => {
  sharpnessValue.textContent = sharpnessSlider.value;
  updateParamSummary();
});

blurSlider.addEventListener("input", () => {
  blurValue.textContent = blurSlider.value;
  updateParamSummary();
});

function updateParamSummary() {
  const label   = PRESET_LABELS[currentPreset] || currentPreset;
  const q       = qualitySlider.value;
  const r       = parseInt(resizeSlider.value, 10);
  const metaTag = stripMetadata.checked ? "Strip EXIF" : "Keep EXIF";

  let resizeTag;
  if (r === 100)    resizeTag = "100%";
  else if (r < 100) resizeTag = `\u2193${r}%`;
  else              resizeTag = `\u2191${r}%`;

  let tags =
    `<span class="ps-tag ps-preset">${escapeHtml(label)}</span>` +
    `<span class="ps-tag">Q${q}</span>` +
    `<span class="ps-tag">${resizeTag}</span>` +
    `<span class="ps-tag">${metaTag}</span>`;

  if (currentFormat) {
    tags += `<span class="ps-tag">\u2192${currentFormat}</span>`;
  }

  const b = parseInt(brightnessSlider.value, 10);
  if (b !== 100) {
    const diff = b - 100;
    tags += `<span class="ps-tag">B${diff > 0 ? "+" : ""}${diff}</span>`;
  }

  const c = parseInt(contrastSlider.value, 10);
  if (c !== 100) {
    const diff = c - 100;
    tags += `<span class="ps-tag">C${diff > 0 ? "+" : ""}${diff}</span>`;
  }

  const s = parseInt(sharpnessSlider.value, 10);
  if (s !== 100) {
    const diff = s - 100;
    tags += `<span class="ps-tag">S${diff > 0 ? "+" : ""}${diff}</span>`;
  }

  const bl = parseInt(blurSlider.value, 10);
  if (bl > 0) {
    tags += `<span class="ps-tag">Blur${bl}</span>`;
  }

  if (currentCrop) {
    tags += `<span class="ps-tag">Crop</span>`;
  }

  paramSummary.innerHTML = tags;
}

// ---------------------------------------------------------------------------
// Quality note (per format, slider stays enabled for all formats)
// ---------------------------------------------------------------------------
function setFormatNote(mimeType) {
  if (mimeType === "image/png") {
    qualityNote.textContent = "PNG: lossless \u00b7 quality controls compression effort.";
  } else {
    qualityNote.textContent = "JPEG/WEBP: lossy quality (1\u201395).";
  }
}

// ---------------------------------------------------------------------------
// Drag-and-drop
// ---------------------------------------------------------------------------
["dragenter", "dragover"].forEach((evt) => {
  dropZone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropZone.classList.add("drag-hover");
  });
});

["dragleave", "dragend"].forEach((evt) => {
  dropZone.addEventListener(evt, () => {
    dropZone.classList.remove("drag-hover");
  });
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("drag-hover");
  const file = e.dataTransfer.files[0];
  if (file) handleFile(file);
});

dropZone.addEventListener("click", (e) => {
  if (e.target.closest(".btn-browse")) return;
  fileInput.click();
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  if (file) handleFile(file);
  fileInput.value = "";
});

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------
function handleFile(file) {
  clearAlerts();

  if (REJECTED_TYPES.has(file.type)) {
    showError(`"${file.type}" is not supported. Please upload a JPEG, PNG, or WEBP image.`);
    return;
  }

  if (!ALLOWED_TYPES.has(file.type)) {
    showError("Only JPEG, PNG, and WEBP images are accepted.");
    return;
  }

  if (file.size > MAX_BYTES) {
    showError(`File is too large (${fmtBytes(file.size)}). Maximum size is 25 MB.`);
    return;
  }

  setFormatNote(file.type);
  showBeforePreview(file);
  uploadAndOptimize(file);
}

// ---------------------------------------------------------------------------
// Before pane – show local preview immediately
// ---------------------------------------------------------------------------
function showBeforePreview(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    beforeImgDataUrl = e.target.result;
    beforeImg.src = beforeImgDataUrl;
    beforeImg.classList.remove("hidden");
    dropIdle.classList.add("hidden");
    beforeSize.textContent = fmtBytes(file.size);
    btnOpenCrop.disabled = false;
  };
  reader.readAsDataURL(file);

  // Reset after pane to loading state
  afterImg.onload  = null;
  afterImg.onerror = null;
  afterImg.classList.add("hidden");
  afterImg.src = "";
  afterPlaceholder.classList.add("hidden");
  afterLoading.classList.remove("hidden");
  afterSize.textContent = "";

  statsBar.classList.add("hidden");
  resetRow.classList.add("hidden");
  btnReoptimize.classList.add("hidden");

  // Clear stale filenames
  currentOrigFilename = null;
  currentOptFilename  = null;
}

// ---------------------------------------------------------------------------
// Crop modal
// ---------------------------------------------------------------------------
btnOpenCrop.addEventListener("click", openCropModal);

function openCropModal() {
  if (!beforeImgDataUrl) return;
  cropImg.src = "";
  cropModal.classList.remove("hidden");

  cropImg.onload = () => {
    if (cropperInstance) {
      cropperInstance.destroy();
      cropperInstance = null;
    }
    cropperInstance = new Cropper(cropImg, {
      viewMode: 1,
      autoCropArea: 1,
      movable: true,
      zoomable: false,
    });
  };
  cropImg.src = beforeImgDataUrl;
}

function closeCropModal() {
  cropModal.classList.add("hidden");
  if (cropperInstance) {
    cropperInstance.destroy();
    cropperInstance = null;
  }
}

btnCropCancel.addEventListener("click", closeCropModal);

btnCropReset.addEventListener("click", () => {
  if (cropperInstance) cropperInstance.reset();
});

btnCropApply.addEventListener("click", () => {
  if (!cropperInstance) return;
  const data       = cropperInstance.getData(true);  // rounded
  const imgData    = cropperInstance.getImageData();
  const naturalW   = imgData.naturalWidth;
  const naturalH   = imgData.naturalHeight;

  currentCrop = {
    x_pct: data.x / naturalW,
    y_pct: data.y / naturalH,
    w_pct: data.width  / naturalW,
    h_pct: data.height / naturalH,
  };

  cropBadge.classList.remove("hidden");
  closeCropModal();
  updateParamSummary();
});

btnClearCrop.addEventListener("click", () => {
  currentCrop = null;
  cropBadge.classList.add("hidden");
  updateParamSummary();
});

// ---------------------------------------------------------------------------
// Upload & optimize
// ---------------------------------------------------------------------------
async function uploadAndOptimize(file) {
  const formData = new FormData();
  formData.append("image", file);
  formData.append("quality", qualitySlider.value);
  formData.append("resize", resizeSlider.value);
  formData.append("strip_metadata", stripMetadata.checked ? "true" : "false");
  formData.append("preset", currentPreset);
  formData.append("output_format", currentFormat);
  formData.append("brightness", brightnessSlider.value / 100);
  formData.append("contrast",   contrastSlider.value  / 100);
  formData.append("sharpness",  sharpnessSlider.value / 100);
  formData.append("blur",       blurSlider.value);
  if (currentCrop) {
    formData.append("crop_x", currentCrop.x_pct);
    formData.append("crop_y", currentCrop.y_pct);
    formData.append("crop_w", currentCrop.w_pct);
    formData.append("crop_h", currentCrop.h_pct);
  }

  try {
    const res  = await fetch("/upload", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok || data.error) {
      throw new Error(data.error || `Server error (${res.status})`);
    }

    handleUploadResult(data);

  } catch (err) {
    afterLoading.classList.add("hidden");
    afterPlaceholder.classList.remove("hidden");
    showError(err.message || "Upload failed. Please try again.");
    resetRow.classList.remove("hidden");
  }
}

// ---------------------------------------------------------------------------
// Re-optimize (shared result path)
// ---------------------------------------------------------------------------
async function reoptimize() {
  if (!currentOrigFilename) return;

  clearAlerts();
  afterImg.onload  = null;   // prevent stale handlers firing on src reset
  afterImg.onerror = null;
  afterImg.classList.add("hidden");
  afterImg.src = "";
  afterPlaceholder.classList.add("hidden");
  afterLoading.classList.remove("hidden");
  afterSize.textContent = "";
  statsBar.classList.add("hidden");
  btnReoptimize.classList.add("hidden");

  const formData = new FormData();
  formData.append("orig_filename",    currentOrigFilename);
  formData.append("old_opt_filename", currentOptFilename || "");
  formData.append("quality",          qualitySlider.value);
  formData.append("resize",           resizeSlider.value);
  formData.append("strip_metadata",   stripMetadata.checked ? "true" : "false");
  formData.append("preset",           currentPreset);
  formData.append("output_format",    currentFormat);
  formData.append("brightness",       brightnessSlider.value / 100);
  formData.append("contrast",         contrastSlider.value  / 100);
  formData.append("sharpness",        sharpnessSlider.value / 100);
  formData.append("blur",             blurSlider.value);
  if (currentCrop) {
    formData.append("crop_x", currentCrop.x_pct);
    formData.append("crop_y", currentCrop.y_pct);
    formData.append("crop_w", currentCrop.w_pct);
    formData.append("crop_h", currentCrop.h_pct);
  }

  try {
    const res  = await fetch("/reoptimize", { method: "POST", body: formData });
    const data = await res.json();

    if (!res.ok || data.error) {
      throw new Error(data.error || `Server error (${res.status})`);
    }

    handleUploadResult(data);

  } catch (err) {
    afterLoading.classList.add("hidden");
    afterPlaceholder.classList.remove("hidden");
    showError(err.message || "Re-optimize failed. Please try again.");
    resetRow.classList.remove("hidden");
    btnReoptimize.classList.remove("hidden");
  }
}

btnReoptimize.addEventListener("click", reoptimize);

// ---------------------------------------------------------------------------
// Shared result handler (upload + reoptimize)
// ---------------------------------------------------------------------------
function handleUploadResult(data) {
  currentOrigFilename = data.orig_filename;
  currentOptFilename  = data.opt_filename;

  afterImg.onload = () => {
    afterLoading.classList.add("hidden");
    afterImg.classList.remove("hidden");
    afterSize.textContent = data.optimized_size_fmt;
    updateStats(data);
    resetRow.classList.remove("hidden");
    btnReoptimize.classList.remove("hidden");
  };

  afterImg.onerror = () => {
    afterLoading.classList.add("hidden");
    afterPlaceholder.classList.remove("hidden");
    showError("Could not load optimized image preview.");
    resetRow.classList.remove("hidden");
  };

  afterImg.src = `/preview/${data.opt_filename}?t=${Date.now()}`;

  btnDownload.onclick = () => {
    window.location.href = `/download/${data.opt_filename}`;
  };
}

// ---------------------------------------------------------------------------
// Stats bar
// ---------------------------------------------------------------------------
function updateStats(data) {
  statFormat.textContent    = data.format;
  statDims.textContent      = data.dimensions;
  statOriginal.textContent  = data.original_size_fmt;
  statOptimized.textContent = data.optimized_size_fmt;

  const pct = data.savings_percent;
  statSavings.textContent = pct > 0 ? `${pct}% smaller` : "No reduction";
  statSavings.className   = "stat-value " + (pct > 0 ? "savings-positive" : "savings-zero");

  statsBar.classList.remove("hidden");
}

// ---------------------------------------------------------------------------
// Reset
// ---------------------------------------------------------------------------
btnReset.addEventListener("click", resetUI);

function resetUI() {
  // Before pane
  beforeImg.classList.add("hidden");
  beforeImg.src = "";
  beforeSize.textContent = "";
  dropIdle.classList.remove("hidden");
  beforeImgDataUrl = null;

  // After pane
  afterImg.onload  = null;
  afterImg.onerror = null;
  afterImg.classList.add("hidden");
  afterImg.src = "";
  afterSize.textContent = "";
  afterLoading.classList.add("hidden");
  afterPlaceholder.classList.remove("hidden");

  // Stats / misc
  statsBar.classList.add("hidden");
  resetRow.classList.add("hidden");
  btnReoptimize.classList.add("hidden");
  clearAlerts();

  // Clear filenames
  currentOrigFilename = null;
  currentOptFilename  = null;

  // Reset format
  currentFormat = "";
  document.querySelectorAll(".format-pill").forEach((p) => p.classList.remove("active"));
  document.querySelector('.format-pill[data-format=""]').classList.add("active");

  // Reset adjustments
  brightnessSlider.value = 100; brightnessValue.textContent = "100";
  contrastSlider.value   = 100; contrastValue.textContent   = "100";
  sharpnessSlider.value  = 100; sharpnessValue.textContent  = "100";
  blurSlider.value       = 0;   blurValue.textContent       = "0";

  // Reset crop
  currentCrop = null;
  cropBadge.classList.add("hidden");
  btnOpenCrop.disabled = true;

  updateParamSummary();
}

// ---------------------------------------------------------------------------
// Alerts
// ---------------------------------------------------------------------------
function showError(message) {
  clearAlerts();
  const div = document.createElement("div");
  div.className = "alert alert-error";
  div.innerHTML = `
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="8" r="7" stroke="currentColor" stroke-width="1.5"/>
      <path d="M8 4.5v4M8 10.5v1" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
    </svg>
    <span>${escapeHtml(message)}</span>`;
  alertsArea.appendChild(div);
  alertsArea.classList.remove("hidden");
}

function clearAlerts() {
  alertsArea.innerHTML = "";
  alertsArea.classList.add("hidden");
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function fmtBytes(bytes) {
  if (bytes < 1024)           return `${bytes} B`;
  if (bytes < 1024 * 1024)    return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
