"""
gui/app.py – Main application window for TXRACT.
"""

from __future__ import annotations

import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

from core.utils import (
    FILE_TYPE_FILTER,
    check_dependencies,
    parse_pages_arg,
    validate_any_input,
)
from gui.theme import COLOURS, FONTS, LAYOUT, apply_theme
from gui.widgets import (
    Card,
    DangerButton,
    Divider,
    FieldLabel,
    FileTypeBadge,
    HintLabel,
    IconButton,
    LogPanel,
    ProgressBar,
    SecondaryButton,
    SectionLabel,
    StatusBar,
    StyledButton,
    StyledEntry,
    SurveyCountBadge,
)

# ── App metadata ───────────────────────────────────────────────────────────────
APP_NAME    = "TXRACT"
APP_VERSION = "1.0.0"
APP_TAGLINE = "Survey Number Extractor"

_C = COLOURS
_F = FONTS
_L = LAYOUT


# ── OCR Modes (must match values in core/converter.py) ───────────────────────
OCR_MODE_AUTO     = "auto"
OCR_MODE_ENGLISH  = "english"
OCR_MODE_GUJARATI = "gujarati"
OCR_MODE_HINDI    = "hindi"

OCR_MODE_LABELS = {
    OCR_MODE_AUTO:     "Auto (Mixed)",
    OCR_MODE_ENGLISH:  "English Only",
    OCR_MODE_GUJARATI: "Gujarati Map",
    OCR_MODE_HINDI:    "Hindi Map",
}

OCR_MODE_TOOLTIPS = {
    OCR_MODE_AUTO:     "Runs both engines - best for mixed-language maps",
    OCR_MODE_ENGLISH:  "RapidOCR only - fastest, English numbers only",
    OCR_MODE_GUJARATI: "Tesseract only - best accuracy for Gujarati maps",
    OCR_MODE_HINDI:    "Tesseract only - best accuracy for Hindi maps",
}


# ── Lazy import for converter (heavy — loads cv2, rapidocr, etc.) ────────────
def _lazy_import_converter():
    """Import run_conversion only when needed. Speeds up app startup."""
    from core.converter import run_conversion
    return run_conversion


class App(tk.Tk):
    """Root window of TXRACT."""

    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME}  -  {APP_TAGLINE}")
        self.resizable(True, True)
        self.minsize(_L["min_width"], _L["min_height"])

        apply_theme(self)

        self._running = False
        self._ocr_preloaded = False

        # OCR mode state
        self._ocr_mode = tk.StringVar(value=OCR_MODE_AUTO)
        self._mode_buttons: dict = {}

        self._build_ui()
        self._check_dependencies()

        # MAC FIX: Disabled background loading.
        # Loading heavy C-libraries (OpenCV/ONNX) in a background thread
        # causes a fatal segmentation fault on macOS.
        # self.after(1000, self._preload_ocr_engines)

    # ══════════════════════════════════════════════════════════════════════
    # UI CONSTRUCTION
    # ══════════════════════════════════════════════════════════════════════

    def _build_ui(self) -> None:
        self._build_header()
        Divider(self).pack(fill="x", padx=_L["padding"])
        self._build_file_section()
        Divider(self).pack(fill="x", padx=_L["padding"])
        self._build_options_section()
        Divider(self).pack(fill="x", padx=_L["padding"])
        self._build_action_section()
        self._build_log_section()
        self._build_status_bar()

    # ── Header ─────────────────────────────────────────────────────────────

    def _build_header(self) -> None:
        frame = tk.Frame(self, bg=_C["background"])
        frame.pack(fill="x", padx=_L["padding"], pady=_L["padding"])

        tk.Label(
            frame, text=APP_NAME,
            font=(_F["heading"][0], 20, "bold"),
            fg=_C["accent"], bg=_C["background"],
        ).pack(side="left")

        tk.Label(
            frame, text=f"  {APP_TAGLINE}",
            font=_F["subheading"],
            fg=_C["text_secondary"], bg=_C["background"],
        ).pack(side="left", anchor="s", pady=(0, 3))

        tk.Label(
            frame, text="PDF / TIFF / PNG / JPEG  ->  DXF",
            font=_F["small"],
            fg=_C["text_disabled"], bg=_C["background"],
        ).pack(side="right", anchor="s", pady=4)

    # ── File section ───────────────────────────────────────────────────────

    def _build_file_section(self) -> None:
        outer = tk.Frame(self, bg=_C["background"])
        outer.pack(fill="x", padx=_L["padding"], pady=_L["padding"])

        SectionLabel(outer, "Input / Output").pack(anchor="w", pady=(0, 8))

        FieldLabel(outer, "Input File").pack(anchor="w")
        HintLabel(
            outer, text="Supported: PDF, TIFF, PNG, JPEG. "
                        "You can also paste a file path directly below.",
        ).pack(anchor="w", pady=(0, 2))

        input_row = tk.Frame(outer, bg=_C["background"])
        input_row.pack(fill="x", pady=(0, _L["gap"]))

        self._input_var = tk.StringVar()
        self._input_var.trace_add("write", self._on_input_path_changed)

        StyledEntry(
            input_row, textvariable=self._input_var,
        ).pack(side="left", fill="x", expand=True, padx=(0, _L["gap"]))

        self._filetype_badge = FileTypeBadge(input_row, extension="")
        self._filetype_badge.pack(side="left", padx=(0, _L["gap"]))

        IconButton(
            input_row, icon="Browse",
            command=self._browse_input,
            tooltip="Browse for input file",
        ).pack(side="right")

        FieldLabel(outer, "Output Directory").pack(anchor="w")

        output_row = tk.Frame(outer, bg=_C["background"])
        output_row.pack(fill="x", pady=(2, 0))

        self._dir_var = tk.StringVar()
        StyledEntry(
            output_row, textvariable=self._dir_var,
        ).pack(side="left", fill="x", expand=True, padx=(0, _L["gap"]))

        IconButton(
            output_row, icon="Browse",
            command=self._browse_dir,
            tooltip="Browse for output directory",
        ).pack(side="right")

    # ── Options section ────────────────────────────────────────────────────

    def _build_options_section(self) -> None:
        outer = tk.Frame(self, bg=_C["background"])
        outer.pack(fill="x", padx=_L["padding"], pady=_L["padding"])

        SectionLabel(outer, "Options").pack(anchor="w", pady=(0, 8))

        pages_row = tk.Frame(outer, bg=_C["background"])
        pages_row.pack(fill="x", pady=(0, _L["gap"]))

        FieldLabel(
            pages_row, "Pages (PDF only)", width=18
        ).pack(side="left")

        self._pages_var = tk.StringVar()
        StyledEntry(
            pages_row, textvariable=self._pages_var, width=16,
        ).pack(side="left")

        HintLabel(
            pages_row,
            text="  e.g. 1  /  1,3,5  /  2-6  /  blank = all pages",
        ).pack(side="left", padx=_L["gap"])

        # ── OCR MODE SELECTOR ─────────────────────────────────────────
        self._build_ocr_mode_selector(outer)

        # ── Existing language info card ───────────────────────────────
        lang_card = Card(outer)
        lang_card.pack(fill="x", pady=(0, _L["gap"]))

        tk.Label(
            lang_card.inner,
            text="[Languages]  TXRACT detects survey numbers in:",
            font=_F["small_bold"],
            fg=_C["text_secondary"], bg=_C["surface"],
        ).pack(anchor="w")

        scripts_row = tk.Frame(lang_card.inner, bg=_C["surface"])
        scripts_row.pack(anchor="w", pady=(4, 0))

        for name, sample, colour in [
            ("English",  "0-9",              _C["text_primary"]),
            ("Hindi",    "0-9 Devanagari",   _C["accent_light"]),
            ("Gujarati", "0-9 Gujarati",     _C["info"]),
        ]:
            pill = tk.Frame(scripts_row, bg=_C["surface_hover"])
            pill.pack(side="left", padx=(0, _L["gap"]))
            tk.Label(
                pill, text=f"  {name}  {sample}  ",
                font=_F["caption"], fg=colour,
                bg=_C["surface_hover"], pady=2,
            ).pack()

        engine_row = tk.Frame(lang_card.inner, bg=_C["surface"])
        engine_row.pack(anchor="w", pady=(6, 0))

        tk.Label(
            engine_row, text="Engines:",
            font=_F["small_bold"],
            fg=_C["text_secondary"], bg=_C["surface"],
        ).pack(side="left")

        for engine, colour in [
            ("RapidOCR (English)",           _C["text_primary"]),
            ("Tesseract (Gujarati / Hindi)", _C["accent_light"]),
        ]:
            tk.Label(
                engine_row, text=f"  {engine}",
                font=_F["caption"], fg=colour, bg=_C["surface"],
            ).pack(side="left")

    def _build_ocr_mode_selector(self, parent) -> None:
        """OCR mode selector — user chooses which OCR engine to use."""
        mode_card = Card(parent)
        mode_card.pack(fill="x", pady=(0, _L["gap"]))

        tk.Label(
            mode_card.inner,
            text="[OCR Mode]  Select based on your map type:",
            font=_F["small_bold"],
            fg=_C["text_secondary"], bg=_C["surface"],
        ).pack(anchor="w", pady=(0, 6))

        btn_row = tk.Frame(mode_card.inner, bg=_C["surface"])
        btn_row.pack(anchor="w", fill="x")

        # Create toggle-style buttons for each mode
        for mode in [OCR_MODE_AUTO, OCR_MODE_ENGLISH,
                     OCR_MODE_GUJARATI, OCR_MODE_HINDI]:
            btn = tk.Button(
                btn_row,
                text=OCR_MODE_LABELS[mode],
                font=_F["caption"],
                relief="flat",
                bd=0,
                padx=14, pady=6,
                cursor="hand2",
                command=lambda m=mode: self._set_ocr_mode(m),
            )
            btn.pack(side="left", padx=(0, _L["gap"]))
            self._mode_buttons[mode] = btn

        # Description label (changes when mode changes)
        self._mode_desc = tk.Label(
            mode_card.inner,
            text="",
            font=_F["small"],
            fg=_C["text_disabled"], bg=_C["surface"],
            wraplength=600, justify="left",
        )
        self._mode_desc.pack(anchor="w", pady=(6, 0))

        # Apply initial mode styling
        self._set_ocr_mode(OCR_MODE_AUTO)

    def _set_ocr_mode(self, mode: str) -> None:
        """Update selected OCR mode and refresh button styles."""
        self._ocr_mode.set(mode)

        # Update button appearances (highlight selected)
        for m, btn in self._mode_buttons.items():
            if m == mode:
                # Selected: filled with accent colour
                btn.configure(
                    bg=_C["accent"],
                    fg="#ffffff",
                    activebackground=_C["accent"],
                    activeforeground="#ffffff",
                )
            else:
                # Unselected: subtle
                btn.configure(
                    bg=_C["surface_hover"],
                    fg=_C["text_secondary"],
                    activebackground=_C["surface_hover"],
                    activeforeground=_C["text_primary"],
                )

        # Update description
        self._mode_desc.configure(text=OCR_MODE_TOOLTIPS[mode])

    # ── Action section ─────────────────────────────────────────────────────

    def _build_action_section(self) -> None:
        outer = tk.Frame(self, bg=_C["background"])
        outer.pack(fill="x", padx=_L["padding"], pady=_L["padding"])

        self._progress = ProgressBar(outer)
        self._progress.pack(fill="x", pady=(0, _L["gap"]))

        btn_row = tk.Frame(outer, bg=_C["background"])
        btn_row.pack(fill="x")

        self._convert_btn = StyledButton(
            btn_row, text=">  Extract Survey Numbers",
            command=self._start_conversion,
            width=26,
            tooltip="Start OCR extraction and write DXF",
        )
        self._convert_btn.pack(side="left")

        SecondaryButton(
            btn_row, text="Clear Log",
            command=self._clear_log,
            tooltip="Erase all log messages",
        ).pack(side="left", padx=(_L["gap"], 0))

        SecondaryButton(
            btn_row, text="Open Output",
            command=self._open_output,
            width=14,
            tooltip="Open the output folder",
        ).pack(side="right")

        self._count_badge = SurveyCountBadge(outer)
        self._count_badge.pack(anchor="w", pady=(_L["gap"], 0))

    # ── Log section ────────────────────────────────────────────────────────

    def _build_log_section(self) -> None:
        frame = tk.Frame(self, bg=_C["background"])
        frame.pack(
            fill="both", expand=True,
            padx=_L["padding"], pady=(0, _L["padding"]),
        )
        SectionLabel(frame, "Log").pack(anchor="w", pady=(0, _L["gap"]))
        self._log = LogPanel(frame)
        self._log.pack(fill="both", expand=True)

    # ── Status bar ─────────────────────────────────────────────────────────

    def _build_status_bar(self) -> None:
        self._status = StatusBar(self)
        self._status.pack(fill="x", side="bottom")
        self._status.set_right(f"{APP_NAME}  v{APP_VERSION}")

    # ══════════════════════════════════════════════════════════════════════
    # DEPENDENCY CHECK  (fast — no OCR calls)
    # ══════════════════════════════════════════════════════════════════════

    def _check_dependencies(self) -> None:
        errors = check_dependencies()
        if not errors:
            self._log.append(
                f"[OK]  {APP_NAME} is ready. All packages loaded.",
                tag="success",
            )
            self._log.append(
                "[i]  Select an input file, choose an OCR mode, "
                "and click 'Extract Survey Numbers' to begin.",
                tag="info",
            )
            self._status.set("Ready")
        else:
            for err in errors:
                self._log.append(f"[!]  {err}", tag="error")
            self._log.append(
                "\nInstall missing packages:\n"
                "  pip install pymupdf Pillow opencv-python "
                "ezdxf numpy rapidocr-onnxruntime pytesseract",
                tag="warning",
            )
            self._status.set("Missing dependencies - see log")
            self._convert_btn.set_enabled(False)

    # ══════════════════════════════════════════════════════════════════════
    # OCR PRELOAD  (background, doesn't block UI)
    # ══════════════════════════════════════════════════════════════════════

    def _preload_ocr_engines(self) -> None:
        """Warm up OCR engines in background so first click is instant."""
        if self._ocr_preloaded:
            return

        def _load():
            try:
                from core.converter import (
                    get_rapid_reader, check_tesseract,
                )

                self.after(0, lambda: self._status.set(
                    "Loading RapidOCR..."
                ))
                get_rapid_reader()

                self.after(0, lambda: self._status.set(
                    "Checking Tesseract..."
                ))
                tess_ok = check_tesseract()

                self._ocr_preloaded = True

                def _done():
                    if tess_ok:
                        self._log.append(
                            "[OK]  OCR engines ready "
                            "(RapidOCR + Tesseract guj+eng).",
                            tag="success",
                        )
                    else:
                        self._log.append(
                            "[!]  RapidOCR ready. Tesseract not available "
                            "(Gujarati OCR disabled).",
                            tag="warning",
                        )
                    self._status.set("Ready")

                self.after(0, _done)

            except Exception as exc:
                self.after(0, lambda: self._log.append(
                    f"[!]  OCR preload failed: {exc}",
                    tag="warning",
                ))

        threading.Thread(target=_load, daemon=True).start()

    # ══════════════════════════════════════════════════════════════════════
    # FILE BROWSING  (macOS-safe: AppleScript Bypass for Anaconda bug)
    # ══════════════════════════════════════════════════════════════════════

    def _browse_input(self) -> None:
        """Open file browser safely using macOS native AppleScript."""
        path = ""

        if sys.platform == "darwin":
            script = ('set theFile to choose file with prompt '
                      '"Select Input File"\nPOSIX path of theFile')
            try:
                result = subprocess.check_output(['osascript', '-e', script])
                path = result.decode('utf-8').strip()
            except subprocess.CalledProcessError:
                return
        else:
            path = filedialog.askopenfilename(
                title="Select Input File",
                initialdir=str(Path.home()),
                filetypes=FILE_TYPE_FILTER,
            )

        if not path:
            return

        self._input_var.set(path)

        if not self._dir_var.get().strip():
            self._dir_var.set(str(Path(path).parent / "txract_output"))

        ok, msg = validate_any_input(path)
        self._log.append(
            f"{'[OK]' if ok else '[!]'}  {msg}",
            tag="success" if ok else "error",
        )

    def _browse_dir(self) -> None:
        """Open directory browser safely using macOS native AppleScript."""
        path = ""

        if sys.platform == "darwin":
            script = ('set theFolder to choose folder with prompt '
                      '"Select Output Directory"\nPOSIX path of theFolder')
            try:
                result = subprocess.check_output(['osascript', '-e', script])
                path = result.decode('utf-8').strip()
            except subprocess.CalledProcessError:
                return
        else:
            path = filedialog.askdirectory(
                title="Select Output Directory",
                initialdir=str(Path.home()),
                mustexist=False,
            )

        if not path:
            return

        self._dir_var.set(path)

    def _on_input_path_changed(self, *_args) -> None:
        path = self._input_var.get().strip()
        ext = Path(path).suffix if path else ""
        self._filetype_badge.update_extension(ext)

    # ══════════════════════════════════════════════════════════════════════
    # INPUT VALIDATION
    # ══════════════════════════════════════════════════════════════════════

    def _validate_inputs(self):
        input_path = self._input_var.get().strip()
        output_dir = self._dir_var.get().strip()
        pages_str  = self._pages_var.get().strip()

        if not input_path:
            messagebox.showwarning(
                f"{APP_NAME} - Missing Input",
                "Please select an input file.",
            )
            return False, None, None, None

        ok, msg = validate_any_input(input_path)
        if not ok:
            messagebox.showerror(f"{APP_NAME} - Invalid File", msg)
            return False, None, None, None

        if not output_dir:
            messagebox.showwarning(
                f"{APP_NAME} - Missing Output",
                "Please select an output directory.",
            )
            return False, None, None, None

        pages = None
        if pages_str and Path(input_path).suffix.lower() == ".pdf":
            try:
                pages = parse_pages_arg(pages_str)
            except ValueError as exc:
                messagebox.showerror(
                    f"{APP_NAME} - Invalid Pages", str(exc)
                )
                return False, None, None, None

        return True, input_path, output_dir, pages

    # ══════════════════════════════════════════════════════════════════════
    # CONVERSION
    # ══════════════════════════════════════════════════════════════════════

    def _start_conversion(self) -> None:
        if self._running:
            return

        ok, input_path, output_dir, pages = self._validate_inputs()
        if not ok:
            return

        # Get selected OCR mode
        ocr_mode = self._ocr_mode.get()

        self._set_running(True)
        self._log.clear()
        self._count_badge.reset()

        ext = Path(input_path).suffix.upper().lstrip(".")
        self._log.append(
            f">  {APP_NAME} - starting extraction\n"
            f"   Input    : {input_path}\n"
            f"   Format   : {ext}\n"
            f"   Output   : {output_dir}\n"
            f"   Pages    : "
            f"{pages if pages else 'All (PDF) / N/A (image)'}\n"
            f"   OCR Mode : {OCR_MODE_LABELS[ocr_mode]}",
            tag="info",
        )
        self._log.append_separator()

        # Lazy load converter here
        run_conversion = _lazy_import_converter()

        threading.Thread(
            target=run_conversion,
            kwargs=dict(
                input_path=input_path,
                output_dir=output_dir,
                pages=pages,
                ocr_mode=ocr_mode,   # ← Pass selected mode
                progress_callback=self._on_progress,
                completion_callback=self._on_complete,
                error_callback=self._on_error,
            ),
            daemon=True,
        ).start()

    def _set_running(self, running: bool) -> None:
        self._running = running
        if running:
            self._convert_btn.set_enabled(False)
            self._progress.start_indeterminate()
            self._status.set("Processing...")
        else:
            self._convert_btn.set_enabled(True)
            self._progress.stop()

    # ══════════════════════════════════════════════════════════════════════
    # THREAD CALLBACKS
    # ══════════════════════════════════════════════════════════════════════

    def _on_progress(self, message: str) -> None:
        self.after(0, self._log.append, f"   {message}", "info")
        self.after(0, self._status.set, message)

    def _on_complete(self, dxf_files: list) -> None:
        count = len(dxf_files)

        def _update():
            self._set_running(False)
            self._log.append_separator()
            self._log.append(
                f"[OK]  {APP_NAME} complete - "
                f"{count} DXF file(s) created:",
                tag="success",
            )
            for f in dxf_files:
                self._log.append(f"   -> {f}", tag="path")
            self._log.append(
                "\n[i]  Open the DXF in AutoCAD or any DXF viewer.\n"
                "     Layer: SURVEY_NUMBERS (yellow)",
                tag="info",
            )
            self._count_badge.update(count)
            self._status.set(f"Done - {count} file(s) created")

        self.after(0, _update)

    def _on_error(self, message: str) -> None:
        def _update():
            self._set_running(False)
            self._log.append_separator()
            self._log.append(f"[X]  Error: {message}", tag="error")
            self._status.set("Error")

        self.after(0, _update)

    # ══════════════════════════════════════════════════════════════════════
    # UTILITIES
    # ══════════════════════════════════════════════════════════════════════

    def _clear_log(self) -> None:
        self._log.clear()
        self._count_badge.reset()

    def _open_output(self) -> None:
        output_dir = self._dir_var.get().strip()
        if not output_dir or not Path(output_dir).exists():
            messagebox.showwarning(
                f"{APP_NAME} - Not Found",
                "Output directory does not exist yet.\n"
                "Run an extraction first.",
            )
            return
        try:
            if sys.platform == "win32":
                subprocess.Popen(["explorer", output_dir])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", output_dir])
            else:
                subprocess.Popen(["xdg-open", output_dir])
        except Exception as exc:
            messagebox.showerror(
                f"{APP_NAME} - Cannot Open Folder", str(exc)
            )