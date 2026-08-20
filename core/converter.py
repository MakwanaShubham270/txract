"""
core/converter.py – TXRACT main pipeline (hybrid OCR).

Optimized for:
    - Accuracy: PSM 11 + upscaling + Otsu threshold for map text
    - Speed:   Parallel tile processing, skip blank tiles

OCR Modes:
    - "auto"     : RapidOCR (English) + Tesseract (guj+eng)
    - "english"  : RapidOCR only (fastest)
    - "gujarati" : Tesseract only, Gujarati language
    - "hindi"    : Tesseract only, Hindi language
"""

from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

logger = logging.getLogger(__name__)


# ── Configuration ──────────────────────────────────────────────────────────────
RENDER_DPI           = 350
OCR_TILE_ROWS        = 4
OCR_TILE_COLS        = 4
OCR_TILE_OVERLAP     = 0.12
CONFIDENCE_THRESHOLD = 0.5
FIXED_TEXT_HEIGHT    = 40
DEDUP_DISTANCE       = 25

MAX_WORKERS          = min(4, os.cpu_count() or 2)

BLANK_TILE_THRESHOLD = 250
BLANK_TILE_STD_MAX   = 8

# ── OCR Modes ────────────────────────────────────────────────────────────────
OCR_MODE_AUTO     = "auto"
OCR_MODE_ENGLISH  = "english"
OCR_MODE_GUJARATI = "gujarati"
OCR_MODE_HINDI    = "hindi"

# Regex helpers
_DIGIT_RE       = re.compile(r"[\d\u0966-\u096F\u0AE6-\u0AEF]")
_LETTER_RE      = re.compile(r"[A-Za-z]{3,}")
_INDIC_DIGIT_RE = re.compile(r"[\u0966-\u096F\u0AE6-\u0AEF]")

_GUJARATI_TO_ASCII   = str.maketrans("૦૧૨૩૪૫૬૭૮૯", "0123456789")
_DEVANAGARI_TO_ASCII = str.maketrans("०१२३४५६७८९", "0123456789")

_rapid_reader    = None
_tesseract_ready = False


# ══════════════════════════════════════════════════════════════════════════════
# DIGIT NORMALISATION
# ══════════════════════════════════════════════════════════════════════════════

def normalise_digits(text: str) -> str:
    text = text.translate(_GUJARATI_TO_ASCII)
    text = text.translate(_DEVANAGARI_TO_ASCII)
    return text


# ══════════════════════════════════════════════════════════════════════════════
# OCR ENGINE INITIALISATION
# ══════════════════════════════════════════════════════════════════════════════

def get_rapid_reader():
    global _rapid_reader
    if _rapid_reader is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
        except ImportError as exc:
            raise RuntimeError(
                "rapidocr_onnxruntime not installed."
            ) from exc
        _rapid_reader = RapidOCR()
        logger.info("RapidOCR initialised (English).")
    return _rapid_reader


def check_tesseract() -> bool:
    global _tesseract_ready
    if _tesseract_ready:
        return True
    try:
        import pytesseract
        version = pytesseract.get_tesseract_version()
        langs   = pytesseract.get_languages()
        has_guj = "guj" in langs
        has_eng = "eng" in langs
        if has_guj and has_eng:
            logger.info("Tesseract %s ready (guj + eng).", version)
            _tesseract_ready = True
            return True
        else:
            missing = [l for l, ok in [("guj", has_guj), ("eng", has_eng)]
                       if not ok]
            logger.warning("Tesseract missing: %s", missing)
            return False
    except Exception as exc:
        logger.warning("Tesseract not available: %s", exc)
        return False


# ══════════════════════════════════════════════════════════════════════════════
# INPUT LOADING
# ══════════════════════════════════════════════════════════════════════════════

def load_image_from_pdf(pdf_path: str, page_index: int = 0,
                        dpi: int = RENDER_DPI) -> Image.Image:
    import fitz
    doc = fitz.open(pdf_path)
    if page_index >= len(doc):
        doc.close()
        raise ValueError(
            f"Page index {page_index} out of range "
            f"(document has {len(doc)} page(s))."
        )
    page   = doc[page_index]
    matrix = fitz.Matrix(dpi / 72, dpi / 72)
    pix    = page.get_pixmap(matrix=matrix, alpha=False)
    img    = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()
    logger.info("PDF rendered: %dx%d @ %d DPI",
                img.size[0], img.size[1], dpi)
    return img


def load_image_from_file(image_path: str) -> Image.Image:
    img = Image.open(image_path).convert("RGB")
    logger.info("Image loaded: %dx%d (%s)",
                img.size[0], img.size[1], Path(image_path).suffix)
    return img


def load_input(input_path: str, page_index: int = 0) -> Image.Image:
    ext = Path(input_path).suffix.lower()
    if ext == ".pdf":
        return load_image_from_pdf(input_path, page_index)
    elif ext in {".tif", ".tiff", ".png", ".jpg", ".jpeg"}:
        return load_image_from_file(input_path)
    else:
        raise ValueError(f"Unsupported file type: '{ext}'.")


# ══════════════════════════════════════════════════════════════════════════════
# IMAGE ENHANCEMENT
# ══════════════════════════════════════════════════════════════════════════════

def enhance_for_ocr(pil_image: Image.Image) -> np.ndarray:
    """Light CLAHE contrast enhancement — helps faded scans."""
    arr      = np.array(pil_image)
    gray     = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    clahe    = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    enhanced = clahe.apply(gray)
    return cv2.cvtColor(enhanced, cv2.COLOR_GRAY2RGB)


def is_blank_tile(tile: np.ndarray) -> bool:
    """Return True if the tile is mostly white/uniform (skip OCR)."""
    if tile.size == 0:
        return True
    gray = (cv2.cvtColor(tile, cv2.COLOR_RGB2GRAY)
            if tile.ndim == 3 else tile)
    mean = float(np.mean(gray))
    std  = float(np.std(gray))
    return mean > BLANK_TILE_THRESHOLD and std < BLANK_TILE_STD_MAX


# ══════════════════════════════════════════════════════════════════════════════
# FILTERS
# ══════════════════════════════════════════════════════════════════════════════

def is_survey_number(text: str) -> bool:
    """Return True if text looks like a survey / parcel number."""
    text = normalise_digits(text.strip())
    if not text or len(text) > 12:
        return False
    if not re.search(r"\d", text):
        return False
    if re.search(r"[a-z]", text):
        return False
    if re.search(r"\d[A-Z]\d", text) or re.match(r"^[A-Z]\d", text):
        return False
    if not re.fullmatch(r"[\d/\-A-Z]+", text):
        return False
    return True


def has_indic_digits(text: str) -> bool:
    return bool(_INDIC_DIGIT_RE.search(text))


# ══════════════════════════════════════════════════════════════════════════════
# ENGINE-SPECIFIC OCR CALLS
# ══════════════════════════════════════════════════════════════════════════════

def run_rapid_on_tile(reader, tile: np.ndarray) -> list:
    """Run RapidOCR on a tile (handles English)."""
    try:
        result, _ = reader(tile)
    except Exception as exc:
        logger.debug("RapidOCR tile error: %s", exc)
        return []
    if not result:
        return []
    return [(d[0], d[1], float(d[2])) for d in result]


def run_tesseract_on_tile(tile: np.ndarray,
                          lang: str = "guj+eng") -> list:
    """
    Tuned for sparse map text.
    - PSM 11: sparse text mode (correct for scattered numbers on maps)
    - Upscales small tiles 2x for better recognition of small digits
    - Otsu threshold: preserves digit shapes better than adaptive
    - Bilateral filter: gentle denoising that keeps edges sharp
    """
    try:
        import pytesseract
        from pytesseract import Output
    except ImportError:
        return []

    gray_tile = cv2.cvtColor(tile, cv2.COLOR_RGB2GRAY)
    orig_h, orig_w = gray_tile.shape

    # Upscale small tiles for better small-digit recognition
    scale = 1
    if max(orig_h, orig_w) < 1500:
        scale = 2
        gray_tile = cv2.resize(
            gray_tile, (orig_w * scale, orig_h * scale),
            interpolation=cv2.INTER_CUBIC
        )

    # Gentle denoising
    denoised = cv2.bilateralFilter(gray_tile, 9, 75, 75)

    # Otsu threshold
    _, thresh_tile = cv2.threshold(
        denoised, 0, 255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    tess_ready_tile = cv2.cvtColor(thresh_tile, cv2.COLOR_GRAY2RGB)

    try:
        # Whitelist based on language
        if "guj" in lang:
            whitelist = "0123456789૦૧૨૩૪૫૬૭૮૯/-"
        elif "hin" in lang:
            whitelist = "0123456789०१२३४५६७८९/-"
        else:
            whitelist = "0123456789/-"

        config = (
            f"--psm 11 --oem 3 "
            f"-c tessedit_char_whitelist={whitelist}"
        )
        data = pytesseract.image_to_data(
            tess_ready_tile,
            lang=lang,
            config=config,
            output_type=Output.DICT,
        )
    except Exception as exc:
        logger.debug("Tesseract tile error: %s", exc)
        return []

    output = []
    n = len(data.get("text", []))
    for i in range(n):
        text = data["text"][i].strip()
        conf = int(data["conf"][i])
        if not text or conf < 30:
            continue

        x = data["left"][i]
        y = data["top"][i]
        w = data["width"][i]
        h = data["height"][i]

        if w < 8 or h < 8:
            continue

        if scale > 1:
            x = x // scale
            y = y // scale
            w = w // scale
            h = h // scale

        box = [
            [x,     y    ],
            [x + w, y    ],
            [x + w, y + h],
            [x,     y + h],
        ]
        output.append((box, text, conf / 100.0))

    return output


# ══════════════════════════════════════════════════════════════════════════════
# DETECTION NORMALISATION
# ══════════════════════════════════════════════════════════════════════════════

def normalise_detection(text: str, conf: float, box,
                        x_offset: int, y_offset: int):
    original_text = text.strip()
    normalised    = normalise_digits(original_text)

    if not is_survey_number(normalised):
        return None
    if conf < CONFIDENCE_THRESHOLD:
        return None

    xs = [p[0] + x_offset for p in box]
    ys = [p[1] + y_offset for p in box]

    return {
        "text":          normalised,
        "original_text": original_text,
        "x":             (min(xs) + max(xs)) / 2.0,
        "y":             (min(ys) + max(ys)) / 2.0,
        "bbox":          (min(xs), min(ys), max(xs), max(ys)),
        "confidence":    conf,
        "has_indic":     has_indic_digits(original_text),
    }


# ══════════════════════════════════════════════════════════════════════════════
# DEDUPLICATION
# ══════════════════════════════════════════════════════════════════════════════

def deduplicate_texts(texts: list, distance: int = DEDUP_DISTANCE) -> list:
    if not texts:
        return []

    texts.sort(
        key=lambda t: (not t.get("has_indic", False), -t["confidence"])
    )

    cell  = distance
    grid: dict = {}
    kept: list = []

    for t in texts:
        gx, gy    = int(t["x"] // cell), int(t["y"] // cell)
        duplicate = False
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for other in grid.get((gx + dx, gy + dy), []):
                    ddx = other["x"] - t["x"]
                    ddy = other["y"] - t["y"]
                    if ddx * ddx + ddy * ddy < distance * distance:
                        if (not other.get("has_indic")
                                and t.get("has_indic")):
                            kept.remove(other)
                            grid[(gx + dx, gy + dy)].remove(other)
                            duplicate = False
                        else:
                            duplicate = True
                        break
                if duplicate:
                    break
            if duplicate:
                break
        if not duplicate:
            kept.append(t)
            grid.setdefault((gx, gy), []).append(t)

    return kept


# ══════════════════════════════════════════════════════════════════════════════
# PARALLEL TILED HYBRID OCR
# ══════════════════════════════════════════════════════════════════════════════

def _process_single_tile(args):
    """Worker function for parallel tile OCR."""
    (tile, x0, y0, rapid, tesseract_ok, ocr_mode) = args

    if is_blank_tile(tile):
        return []

    results = []

    # RapidOCR: run in auto or english mode
    if rapid is not None and ocr_mode in (OCR_MODE_AUTO, OCR_MODE_ENGLISH):
        rapid_results = run_rapid_on_tile(rapid, tile)
        for box, text, conf in rapid_results:
            det = normalise_detection(text, conf, box, x0, y0)
            if det:
                results.append(det)

    # Tesseract: run in auto, gujarati, or hindi mode
    if tesseract_ok and ocr_mode in (
        OCR_MODE_AUTO, OCR_MODE_GUJARATI, OCR_MODE_HINDI
    ):
        if ocr_mode == OCR_MODE_GUJARATI:
            tess_lang = "guj"
        elif ocr_mode == OCR_MODE_HINDI:
            tess_lang = "hin"
        else:
            tess_lang = "guj+eng"

        tess_results = run_tesseract_on_tile(tile, lang=tess_lang)
        for box, text, conf in tess_results:
            det = normalise_detection(text, conf, box, x0, y0)
            if det:
                results.append(det)

    return results


def extract_survey_numbers(pil_image: Image.Image,
                           progress_callback=None,
                           ocr_mode: str = OCR_MODE_AUTO) -> list:
    """
    Run OCR based on mode.
        - "auto"     : Both RapidOCR (English) + Tesseract (guj+eng)
        - "english"  : RapidOCR only (fastest)
        - "gujarati" : Tesseract only, Gujarati language
        - "hindi"    : Tesseract only, Hindi language
    """
    # Only load RapidOCR if we'll actually use it
    rapid = None
    if ocr_mode in (OCR_MODE_AUTO, OCR_MODE_ENGLISH):
        rapid = get_rapid_reader()

    tesseract_ok = check_tesseract()

    if progress_callback:
        progress_callback(f"OCR mode: {ocr_mode.upper()}")
        if ocr_mode == OCR_MODE_GUJARATI and not tesseract_ok:
            progress_callback(
                "[!] Tesseract NOT available - Gujarati mode needs it!"
            )
        elif ocr_mode == OCR_MODE_HINDI and not tesseract_ok:
            progress_callback(
                "[!] Tesseract NOT available - Hindi mode needs it!"
            )
        progress_callback("Enhancing image...")

    img_array    = enhance_for_ocr(pil_image)
    img_h, img_w = img_array.shape[:2]

    tile_w    = img_w // OCR_TILE_COLS
    tile_h    = img_h // OCR_TILE_ROWS
    overlap_x = int(tile_w * OCR_TILE_OVERLAP)
    overlap_y = int(tile_h * OCR_TILE_OVERLAP)

    tasks = []
    for row in range(OCR_TILE_ROWS):
        for col in range(OCR_TILE_COLS):
            x0 = max(0, col * tile_w - overlap_x)
            y0 = max(0, row * tile_h - overlap_y)
            x1 = min(img_w, (col + 1) * tile_w + overlap_x)
            y1 = min(img_h, (row + 1) * tile_h + overlap_y)
            tile = img_array[y0:y1, x0:x1]
            if tile.size == 0:
                continue
            tasks.append((tile, x0, y0, rapid, tesseract_ok, ocr_mode))

    total_tiles = len(tasks)
    all_texts: list = []
    completed = 0

    if progress_callback:
        progress_callback(
            f"OCR: {total_tiles} tiles, {MAX_WORKERS} workers"
        )

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(_process_single_tile, t)
                   for t in tasks]
        for fut in as_completed(futures):
            completed += 1
            if progress_callback:
                progress_callback(
                    f"OCR tile {completed}/{total_tiles}"
                )
            try:
                all_texts.extend(fut.result())
            except Exception as exc:
                logger.debug("Tile worker error: %s", exc)

    all_texts = deduplicate_texts(all_texts)
    logger.info("Survey numbers found: %d (mode=%s)",
                len(all_texts), ocr_mode)
    return all_texts


# ══════════════════════════════════════════════════════════════════════════════
# DXF BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def build_dxf(texts: list, image_size: tuple, output_dxf: Path,
              text_height: float = FIXED_TEXT_HEIGHT) -> None:
    import ezdxf
    img_w, img_h = image_size
    doc          = ezdxf.new("R2018")
    doc.header["$INSUNITS"] = 0
    msp          = doc.modelspace()
    doc.layers.new(name="SURVEY_NUMBERS", dxfattribs={"color": 2})

    placed = 0
    for t in texts:
        try:
            entity = msp.add_text(
                t["text"],
                dxfattribs={
                    "layer":  "SURVEY_NUMBERS",
                    "height": text_height,
                },
            )
            entity.set_placement(
                (t["x"], img_h - t["y"]),
                align=ezdxf.enums.TextEntityAlignment.MIDDLE_CENTER,
            )
            placed += 1
        except Exception as exc:
            logger.warning("Could not place text '%s': %s",
                           t["text"], exc)
    doc.saveas(str(output_dxf))
    logger.info("DXF saved: %s (%d entities)", output_dxf, placed)


# ══════════════════════════════════════════════════════════════════════════════
# PER-FILE CONVERTER
# ══════════════════════════════════════════════════════════════════════════════

def convert_file(input_path: str, output_path: Path, base_name: str,
                 page_index: int = 0, progress_callback=None,
                 ocr_mode: str = OCR_MODE_AUTO) -> Path:
    if progress_callback:
        progress_callback(f"Loading: {Path(input_path).name}")
    image = load_input(input_path, page_index=page_index)

    suffix    = (f"_page_{page_index + 1}"
                 if Path(input_path).suffix.lower() == ".pdf" else "")
    file_stem = f"{base_name}{suffix}"

    if progress_callback:
        progress_callback("Extracting survey numbers")
    texts = extract_survey_numbers(
        image,
        progress_callback=progress_callback,
        ocr_mode=ocr_mode,
    )

    if progress_callback:
        progress_callback(f"Found {len(texts)} survey number(s).")

    dxf_path = output_path / f"{file_stem}.dxf"
    if progress_callback:
        progress_callback(f"Writing DXF: {dxf_path.name}")
    build_dxf(texts, image.size, dxf_path)
    return dxf_path


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def run_conversion(input_path: str, output_dir: str,
                   pages=None,
                   ocr_mode: str = OCR_MODE_AUTO,
                   progress_callback=None,
                   completion_callback=None,
                   error_callback=None) -> list:
    try:
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        ext         = Path(input_path).suffix.lower()
        base_name   = Path(input_path).stem
        dxf_files: list = []

        if ext == ".pdf":
            import fitz
            doc         = fitz.open(input_path)
            total_pages = len(doc)
            doc.close()

            if pages is None:
                pages = list(range(total_pages))

            invalid = [p + 1 for p in pages
                       if p < 0 or p >= total_pages]
            if invalid:
                raise ValueError(
                    f"Page(s) {invalid} out of range. "
                    f"PDF has {total_pages} page(s)."
                )

            for page_index in pages:
                if progress_callback:
                    progress_callback(
                        f"--- Page {page_index + 1} of {len(pages)} ---"
                    )
                dxf_files.append(convert_file(
                    input_path, output_path, base_name,
                    page_index=page_index,
                    progress_callback=progress_callback,
                    ocr_mode=ocr_mode,
                ))
        else:
            dxf_files.append(convert_file(
                input_path, output_path, base_name,
                page_index=0,
                progress_callback=progress_callback,
                ocr_mode=ocr_mode,
            ))

        if completion_callback:
            completion_callback(dxf_files)
        return dxf_files

    except Exception as exc:
        logger.error("Conversion failed: %s", exc, exc_info=True)
        if error_callback:
            error_callback(str(exc))
        return []