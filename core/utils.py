"""
core/utils.py – Helper utilities for TXRACT.
"""

from __future__ import annotations

from pathlib import Path


# ── Supported file types for dialog filter ────────────────────────────────────
FILE_TYPE_FILTER: list[tuple[str, str]] = [
    ("All supported",  "*.pdf *.tif *.tiff *.png *.jpg *.jpeg"),
    ("PDF",            "*.pdf"),
    ("TIFF",           "*.tif *.tiff"),
    ("PNG",            "*.png"),
    ("JPEG",           "*.jpg *.jpeg"),
    ("All files",      "*.*"),
]

SUPPORTED_EXTS = {".pdf", ".tif", ".tiff", ".png", ".jpg", ".jpeg"}


# ══════════════════════════════════════════════════════════════════════════════
# DEPENDENCY CHECK  (fast — no heavy imports, no binary calls)
# ══════════════════════════════════════════════════════════════════════════════

def check_dependencies() -> list[str]:
    """
    Check that all required packages are importable.

    NOTE: This is a fast check only — we do NOT call Tesseract binary
    or load OCR models here. Those checks happen lazily when the
    user actually starts an extraction (via check_tesseract()).
    """
    errors: list[str] = []

    checks = [
        ("fitz",                  "pymupdf"),
        ("PIL",                   "Pillow"),
        ("cv2",                   "opencv-python"),
        ("numpy",                 "numpy"),
        ("ezdxf",                 "ezdxf"),
        ("rapidocr_onnxruntime",  "rapidocr-onnxruntime"),
        ("pytesseract",           "pytesseract"),
    ]

    for import_name, pip_name in checks:
        try:
            __import__(import_name)
        except ImportError:
            errors.append(f"Missing package: {pip_name}")

    return errors


# ══════════════════════════════════════════════════════════════════════════════
# INPUT VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def validate_any_input(path: str) -> tuple[bool, str]:
    """Validate that path is an existing supported file."""
    p = Path(path)
    if not p.exists():
        return False, f"File does not exist: {path}"
    if not p.is_file():
        return False, f"Not a file: {path}"
    if p.suffix.lower() not in SUPPORTED_EXTS:
        return False, (
            f"Unsupported file type: '{p.suffix}'.\n"
            f"Supported: {', '.join(sorted(SUPPORTED_EXTS))}"
        )
    if p.stat().st_size == 0:
        return False, f"File is empty: {path}"
    return True, f"Valid input: {p.name}"


# ══════════════════════════════════════════════════════════════════════════════
# PAGE-RANGE PARSING
# ══════════════════════════════════════════════════════════════════════════════

def parse_pages_arg(pages_arg: str) -> list[int]:
    """
    Convert a string like '1,3,5-7' into a sorted list of 0-based indices.
    """
    pages: set[int] = set()
    for part in pages_arg.split(","):
        part = part.strip()
        if not part:
            continue

        if "-" in part:
            try:
                a, b = part.split("-", 1)
                start = int(a.strip())
                end   = int(b.strip())
            except ValueError:
                raise ValueError(
                    f"Invalid range '{part}'. Use integers like '3-7'."
                )
            if start < 1 or end < 1:
                raise ValueError(
                    f"Page numbers must be >= 1 (got '{part}')."
                )
            if start > end:
                raise ValueError(
                    f"Range start must be <= end (got '{part}')."
                )
            pages.update(range(start - 1, end))
        else:
            try:
                n = int(part)
            except ValueError:
                raise ValueError(
                    f"Invalid page number '{part}'."
                )
            if n < 1:
                raise ValueError(
                    f"Page must be >= 1 (got '{part}')."
                )
            pages.add(n - 1)

    if not pages:
        raise ValueError("No valid page numbers given.")

    return sorted(pages)