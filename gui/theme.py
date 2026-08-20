"""
gui/theme.py – Central design tokens for TXRACT UI.
"""

from __future__ import annotations
import platform
import tkinter as tk


# ══════════════════════════════════════════════════════════════════════════════
# COLOUR PALETTE
# ══════════════════════════════════════════════════════════════════════════════

COLOURS: dict[str, str] = {
    "background":       "#1e1e2e",
    "surface":          "#2a2a3e",
    "surface_hover":    "#33334d",
    "surface_alt":      "#242438",
    "log_background":   "#13131f",
    "accent":           "#7c6af7",
    "accent_hover":     "#6a58e0",
    "accent_light":     "#a99eff",
    "success":          "#4caf7d",
    "warning":          "#f0a500",
    "error":            "#e05c5c",
    "info":             "#4da6ff",
    "text_primary":     "#e0e0f0",
    "text_secondary":   "#9090b0",
    "text_disabled":    "#55556a",
    "text_on_accent":   "#ffffff",
    "button_text":      "#000000",
    "border":           "#3a3a5c",
    "border_focus":     "#7c6af7",
    "divider":          "#2e2e48",
    "progress_track":   "#2a2a3e",
    "progress_fill":    "#7c6af7",
}


# ══════════════════════════════════════════════════════════════════════════════
# TYPOGRAPHY
# ══════════════════════════════════════════════════════════════════════════════

def _resolve_font_family() -> str:
    system = platform.system()
    if system == "Windows":
        return "Segoe UI"
    if system == "Darwin":
        return "SF Pro Display"
    return "DejaVu Sans"


def _resolve_mono_family() -> str:
    system = platform.system()
    if system == "Windows":
        return "Consolas"
    if system == "Darwin":
        return "Menlo"
    return "DejaVu Sans Mono"


_FF = _resolve_font_family()
_FM = _resolve_mono_family()

FONTS: dict[str, tuple] = {
    "normal":     (_FF, 10),
    "bold":       (_FF, 10, "bold"),
    "small":      (_FF,  8),
    "small_bold": (_FF,  8, "bold"),
    "heading":    (_FF, 13, "bold"),
    "subheading": (_FF, 11, "bold"),
    "caption":    (_FF,  9),
    "mono":       (_FM,  9),
}


# ══════════════════════════════════════════════════════════════════════════════
# LAYOUT
# ══════════════════════════════════════════════════════════════════════════════

LAYOUT: dict[str, int] = {
    "padding":         12,
    "padding_small":    6,
    "padding_large":   20,
    "gap":              8,
    "button_width":    14,
    "button_width_sm": 10,
    "input_width":     42,
    "min_width":      820,
    "min_height":     640,
    "log_height":      10,
}


# ══════════════════════════════════════════════════════════════════════════════
# FILE TYPE INFO
# ══════════════════════════════════════════════════════════════════════════════

SUPPORTED_FORMATS: dict[str, dict[str, str]] = {
    ".pdf":  {"label": "PDF Document", "icon": "📄"},
    ".tif":  {"label": "TIFF Image",   "icon": "🗺"},
    ".tiff": {"label": "TIFF Image",   "icon": "🗺"},
    ".png":  {"label": "PNG Image",    "icon": "🖼"},
    ".jpg":  {"label": "JPEG Image",   "icon": "🖼"},
    ".jpeg": {"label": "JPEG Image",   "icon": "🖼"},
}


# ══════════════════════════════════════════════════════════════════════════════
# LOG COLOUR TAGS
# ══════════════════════════════════════════════════════════════════════════════

LOG_TAGS: dict[str, dict[str, str]] = {
    "info":      {"foreground": COLOURS["text_primary"]},
    "success":   {"foreground": COLOURS["success"]},
    "warning":   {"foreground": COLOURS["warning"]},
    "error":     {"foreground": COLOURS["error"]},
    "accent":    {"foreground": COLOURS["accent_light"]},
    "separator": {"foreground": COLOURS["text_disabled"]},
    "path":      {"foreground": COLOURS["info"], "font": FONTS["mono"]},
}


# ══════════════════════════════════════════════════════════════════════════════
# THEME APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

def apply_theme(root: tk.Tk) -> None:
    """Apply dark theme to root window."""
    from tkinter import ttk

    root.configure(bg=COLOURS["background"])
    root.option_add("*Font", FONTS["normal"])

    style = ttk.Style(root)
    available = style.theme_names()
    base = "clam" if "clam" in available else available[0]
    style.theme_use(base)

    # Frames
    style.configure("TFrame", background=COLOURS["background"])

    # Labels
    style.configure(
        "TLabel",
        background=COLOURS["background"],
        foreground=COLOURS["text_primary"],
        font=FONTS["normal"],
    )

    # Buttons
    style.configure(
        "Accent.TButton",
        background=COLOURS["accent"],
        foreground=COLOURS["button_text"],
        font=FONTS["bold"],
        relief="flat",
        padding=(10, 5),
    )
    style.map(
        "Accent.TButton",
        background=[("active", COLOURS["accent_hover"])],
    )

    # Progress bar
    style.configure(
        "TProgressbar",
        troughcolor=COLOURS["progress_track"],
        background=COLOURS["progress_fill"],
        thickness=8,
    )

    # Scrollbar
    style.configure(
        "TScrollbar",
        background=COLOURS["surface"],
        troughcolor=COLOURS["background"],
        arrowcolor=COLOURS["text_secondary"],
    )