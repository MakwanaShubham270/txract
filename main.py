"""
main.py – Application entry point for TXRACT.

Usage:
    python main.py              # normal launch
    python main.py --debug      # verbose logging
    python main.py --version    # print version
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path


APP_NAME    = "TXRACT"
APP_VERSION = "1.0.0"
APP_TAGLINE = "Survey Number Extractor"
LOG_DIR     = Path.home() / ".txract" / "logs"


# ══════════════════════════════════════════════════════════════════════════════
# FROZEN BUNDLE BOOTSTRAP
# ══════════════════════════════════════════════════════════════════════════════

def _bootstrap_frozen_env() -> None:
    """Configure paths for bundled Tesseract when running as .app/.exe"""
    if not getattr(sys, "frozen", False):
        return

    bundle_dir = Path(getattr(sys, "_MEIPASS",
                              Path(sys.executable).parent))

    tess_bin = bundle_dir / "tesseract"
    if sys.platform == "win32":
        tess_bin = bundle_dir / "tesseract.exe"

    if tess_bin.exists():
        os.environ["TESSERACT_CMD"] = str(tess_bin)

    tessdata = bundle_dir / "tessdata"
    if tessdata.is_dir():
        os.environ["TESSDATA_PREFIX"] = str(tessdata)


_bootstrap_frozen_env()


# ══════════════════════════════════════════════════════════════════════════════
# LOGGING
# ══════════════════════════════════════════════════════════════════════════════

def setup_logging(debug: bool = False) -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_file = LOG_DIR / f"{datetime.now().strftime('%Y-%m-%d')}.log"

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    if not debug:
        for noisy in ("PIL", "onnxruntime"):
            logging.getLogger(noisy).setLevel(logging.WARNING)

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    ))

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG if debug else logging.INFO)
    console_handler.setFormatter(
        logging.Formatter(fmt="%(levelname)-8s  %(message)s")
    )

    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    return log_file


# ══════════════════════════════════════════════════════════════════════════════
# CHECKS
# ══════════════════════════════════════════════════════════════════════════════

def _check_python_version() -> None:
    if sys.version_info < (3, 8):
        print(
            f"ERROR: {APP_NAME} requires Python 3.8+.\n"
            f"You have: {sys.version}",
            file=sys.stderr,
        )
        sys.exit(1)


def _check_tkinter() -> None:
    try:
        import tkinter  # noqa
    except ImportError:
        print(
            "ERROR: Tkinter not available.\n"
            "macOS: install Python from python.org\n"
            "Linux: sudo apt install python3-tk",
            file=sys.stderr,
        )
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# CLI
# ══════════════════════════════════════════════════════════════════════════════

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="txract",
        description=f"{APP_NAME} v{APP_VERSION} - {APP_TAGLINE}",
    )
    parser.add_argument(
        "--version", "-v",
        action="version",
        version=f"{APP_NAME} {APP_VERSION}",
    )
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable verbose logging",
    )
    return parser.parse_args()


# ══════════════════════════════════════════════════════════════════════════════
# SPLASH SCREEN
# ══════════════════════════════════════════════════════════════════════════════

def _make_splash() -> tk.Tk:
    """Create a splash window that shows while heavy imports load."""
    splash = tk.Tk()
    splash.title("")
    splash.overrideredirect(True)
    splash.configure(bg="#1e1e2e")

    w, h = 420, 220
    x = (splash.winfo_screenwidth()  - w) // 2
    y = (splash.winfo_screenheight() - h) // 2
    splash.geometry(f"{w}x{h}+{x}+{y}")

    tk.Label(
        splash, text=APP_NAME,
        font=("Helvetica", 34, "bold"),
        fg="#7c6af7", bg="#1e1e2e",
    ).pack(pady=(40, 5))

    tk.Label(
        splash, text=APP_TAGLINE,
        font=("Helvetica", 13),
        fg="#9090b0", bg="#1e1e2e",
    ).pack()

    tk.Label(
        splash, text=f"v{APP_VERSION}",
        font=("Helvetica", 10),
        fg="#55556a", bg="#1e1e2e",
    ).pack(pady=(4, 0))

    tk.Label(
        splash, text="Loading...",
        font=("Helvetica", 11),
        fg="#a99eff", bg="#1e1e2e",
    ).pack(pady=(20, 0))

    splash.update()
    return splash


# ══════════════════════════════════════════════════════════════════════════════
# LAUNCH
# ══════════════════════════════════════════════════════════════════════════════

def _show_fatal_error(title: str, message: str) -> None:
    try:
        root = tk.Tk()
        root.withdraw()
        tk.messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        print(f"FATAL: {title}\n{message}", file=sys.stderr)


def launch(debug: bool = False) -> None:
    log = logging.getLogger(__name__)
    log.info("=" * 60)
    log.info("%s v%s", APP_NAME, APP_VERSION)
    log.info("Python %s | %s", sys.version.split()[0], sys.platform)
    log.info("Frozen: %s", getattr(sys, "frozen", False))
    log.info("=" * 60)

    # ── Show splash immediately (before slow imports) ────────────────
    splash = _make_splash()

    # ── Import App (this triggers all the heavy imports) ─────────────
    try:
        from gui.app import App
    except ImportError as exc:
        splash.destroy()
        msg = (
            f"Failed to import UI:\n\n{exc}\n\n"
            "Install packages:\n"
            "  pip install pymupdf Pillow opencv-python "
            "ezdxf numpy rapidocr-onnxruntime pytesseract"
        )
        log.critical("UI import failed: %s", exc, exc_info=True)
        _show_fatal_error(f"{APP_NAME} - Import Error", msg)
        sys.exit(1)

    # ── Close splash and open main window ────────────────────────────
    try:
        log.info("Creating main window...")
        splash.destroy()
        app = App()
        app.mainloop()
        log.info("%s closed normally.", APP_NAME)
    except KeyboardInterrupt:
        log.info("Interrupted by user")
        sys.exit(0)
    except Exception as exc:
        msg = f"Unexpected error:\n\n{exc}\n\nSee log: {LOG_DIR}"
        log.critical("Unhandled exception: %s", exc, exc_info=True)
        _show_fatal_error(f"{APP_NAME} - Error", msg)
        sys.exit(1)


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    _check_python_version()
    _check_tkinter()

    args = parse_args()
    log_file = setup_logging(debug=args.debug)

    print(f"{APP_NAME} - {APP_TAGLINE}")
    print(f"Version  : {APP_VERSION}")
    print(f"Log file : {log_file}")
    print()

    launch(debug=args.debug)


if __name__ == "__main__":
    main()