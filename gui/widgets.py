"""
gui/widgets.py – Reusable custom Tkinter widgets for TXRACT.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from gui.theme import COLOURS, FONTS, LAYOUT, LOG_TAGS, SUPPORTED_FORMATS

_C = COLOURS
_F = FONTS
_L = LAYOUT


# ══════════════════════════════════════════════════════════════════════════════
# TOOLTIP MIXIN
# ══════════════════════════════════════════════════════════════════════════════

class TooltipMixin:
    """Add hover tooltip to any tk widget."""

    def set_tooltip(self, text: str) -> None:
        self._tooltip_text = text
        self.bind("<Enter>", self._show_tooltip, add="+")
        self.bind("<Leave>", self._hide_tooltip, add="+")
        self._tooltip_window: tk.Toplevel | None = None

    def _show_tooltip(self, event=None) -> None:
        if not getattr(self, "_tooltip_text", None):
            return
        x = self.winfo_rootx() + self.winfo_width() // 2
        y = self.winfo_rooty() + self.winfo_height() + 4
        self._tooltip_window = tw = tk.Toplevel(self)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        tw.configure(bg=_C["surface"])
        tk.Label(
            tw, text=self._tooltip_text,
            font=_F["small"], bg=_C["surface"],
            fg=_C["text_secondary"], padx=6, pady=3, relief="flat",
        ).pack()

    def _hide_tooltip(self, event=None) -> None:
        if self._tooltip_window:
            self._tooltip_window.destroy()
            self._tooltip_window = None


# ══════════════════════════════════════════════════════════════════════════════
# LABELS
# ══════════════════════════════════════════════════════════════════════════════

class SectionLabel(tk.Label):
    def __init__(self, parent, text, **kwargs):
        super().__init__(
            parent, text=text,
            font=_F["heading"], fg=_C["text_primary"],
            bg=_C["background"], anchor="w", **kwargs,
        )


class FieldLabel(tk.Label):
    def __init__(self, parent, text, **kwargs):
        super().__init__(
            parent, text=text,
            font=_F["normal"], fg=_C["text_secondary"],
            bg=_C["background"], anchor="w", **kwargs,
        )


class HintLabel(tk.Label):
    def __init__(self, parent, text, **kwargs):
        super().__init__(
            parent, text=text,
            font=_F["caption"], fg=_C["text_disabled"],
            bg=_C["background"], anchor="w",
            wraplength=540, justify="left", **kwargs,
        )


# ══════════════════════════════════════════════════════════════════════════════
# ENTRY
# ══════════════════════════════════════════════════════════════════════════════

class StyledEntry(tk.Entry):
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent, font=_F["normal"],
            bg=_C["surface"], fg=_C["text_primary"],
            insertbackground=_C["text_primary"],
            relief="flat", bd=6, **kwargs,
        )


# ══════════════════════════════════════════════════════════════════════════════
# BUTTONS
# ══════════════════════════════════════════════════════════════════════════════

class StyledButton(TooltipMixin, tk.Button):
    def __init__(self, parent, text, command,
                 width=_L["button_width"], tooltip="", **kwargs):
        super().__init__(
            parent, text=text, command=command,
            font=_F["bold"], bg=_C["accent"],
            fg=_C["button_text"],
            activebackground=_C["accent_hover"],
            activeforeground=_C["button_text"],
            relief="flat", cursor="hand2",
            width=width, padx=8, pady=6, **kwargs,
        )
        self.bind("<Enter>", lambda _e: self.config(bg=_C["accent_hover"]))
        self.bind("<Leave>", lambda _e: self.config(bg=_C["accent"]))
        if tooltip:
            self.set_tooltip(tooltip)

    def set_enabled(self, enabled: bool) -> None:
        self.config(
            state="normal" if enabled else "disabled",
            bg=_C["accent"] if enabled else _C["text_disabled"],
            cursor="hand2" if enabled else "arrow",
        )


class SecondaryButton(TooltipMixin, tk.Button):
    def __init__(self, parent, text, command,
                 width=_L["button_width_sm"], tooltip="", **kwargs):
        super().__init__(
            parent, text=text, command=command,
            font=_F["normal"], bg=_C["surface_hover"],
            fg=_C["button_text"],
            activebackground=_C["border"],
            activeforeground=_C["button_text"],
            relief="flat", cursor="hand2",
            width=width, padx=6, pady=6, **kwargs,
        )
        self.bind("<Enter>", lambda _e: self.config(bg=_C["border"]))
        self.bind("<Leave>", lambda _e: self.config(bg=_C["surface_hover"]))
        if tooltip:
            self.set_tooltip(tooltip)


class DangerButton(TooltipMixin, tk.Button):
    def __init__(self, parent, text, command,
                 width=_L["button_width_sm"], tooltip="", **kwargs):
        super().__init__(
            parent, text=text, command=command,
            font=_F["bold"], bg=_C["error"],
            fg=_C["button_text"],
            activebackground="#c44",
            activeforeground=_C["button_text"],
            relief="flat", cursor="hand2",
            width=width, padx=8, pady=6, **kwargs,
        )
        self.bind("<Enter>", lambda _e: self.config(bg="#c44"))
        self.bind("<Leave>", lambda _e: self.config(bg=_C["error"]))
        if tooltip:
            self.set_tooltip(tooltip)


class IconButton(TooltipMixin, tk.Button):
    def __init__(self, parent, icon, command, tooltip="", **kwargs):
        super().__init__(
            parent, text=icon, command=command,
            font=_F["normal"], bg=_C["surface"],
            fg=_C["text_primary"],
            activebackground=_C["surface_hover"],
            activeforeground=_C["text_primary"],
            relief="flat", cursor="hand2",
            width=3, pady=4, **kwargs,
        )
        self.bind("<Enter>", lambda _e: self.config(bg=_C["surface_hover"]))
        self.bind("<Leave>", lambda _e: self.config(bg=_C["surface"]))
        if tooltip:
            self.set_tooltip(tooltip)


# ══════════════════════════════════════════════════════════════════════════════
# STRUCTURAL
# ══════════════════════════════════════════════════════════════════════════════

class Divider(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=_C["divider"], height=1, **kwargs)


class Card(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=_C["surface"], relief="flat", **kwargs)
        self.inner = tk.Frame(
            self, bg=_C["surface"],
            padx=_L["padding"], pady=_L["padding_small"],
        )
        self.inner.pack(fill="both", expand=True)


# ══════════════════════════════════════════════════════════════════════════════
# LOG PANEL
# ══════════════════════════════════════════════════════════════════════════════

class LogPanel(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=_C["log_background"], **kwargs)

        self._text = tk.Text(
            self, font=_F["mono"],
            bg=_C["log_background"], fg=_C["text_primary"],
            relief="flat", state="disabled", wrap="word",
            padx=8, pady=8, height=_L["log_height"],
        )
        scrollbar = ttk.Scrollbar(self, command=self._text.yview)
        self._text.configure(yscrollcommand=scrollbar.set)

        for tag, opts in LOG_TAGS.items():
            self._text.tag_config(tag, **opts)

        scrollbar.pack(side="right", fill="y")
        self._text.pack(side="left", fill="both", expand=True)

    def append(self, message: str, tag: str = "info") -> None:
        self._text.configure(state="normal")
        self._text.insert("end", message + "\n", tag)
        self._text.see("end")
        self._text.configure(state="disabled")

    def append_separator(self) -> None:
        self.append("─" * 55, tag="separator")

    def clear(self) -> None:
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")


# ══════════════════════════════════════════════════════════════════════════════
# STATUS BAR
# ══════════════════════════════════════════════════════════════════════════════

class StatusBar(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=_C["surface"], **kwargs)
        self._var = tk.StringVar(value="Ready")
        self._right_var = tk.StringVar(value="")

        tk.Label(
            self, textvariable=self._var,
            font=_F["small"], fg=_C["text_secondary"],
            bg=_C["surface"], anchor="w", padx=_L["padding"],
        ).pack(side="left", fill="x", expand=True, pady=3)

        tk.Label(
            self, textvariable=self._right_var,
            font=_F["small"], fg=_C["text_disabled"],
            bg=_C["surface"], anchor="e", padx=_L["padding"],
        ).pack(side="right", pady=3)

    def set(self, message: str, colour: str = None) -> None:
        self._var.set(message)

    def set_right(self, message: str) -> None:
        self._right_var.set(message)


# ══════════════════════════════════════════════════════════════════════════════
# PROGRESS BAR
# ══════════════════════════════════════════════════════════════════════════════

class ProgressBar(ttk.Progressbar):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, mode="indeterminate", **kwargs)

    def start_indeterminate(self):
        self.config(mode="indeterminate")
        self.start(12)

    def stop(self):
        super().stop()
        self.config(value=0)


# ══════════════════════════════════════════════════════════════════════════════
# BADGES
# ══════════════════════════════════════════════════════════════════════════════

class FileTypeBadge(tk.Label):
    def __init__(self, parent, extension, **kwargs):
        info = SUPPORTED_FORMATS.get(
            extension.lower(),
            {"label": extension.upper() or "None", "icon": "📎"},
        )
        super().__init__(
            parent, text=f"{info['icon']}  {info['label']}",
            font=_F["small_bold"], fg=_C["accent_light"],
            bg=_C["surface"], padx=6, pady=2, relief="flat", **kwargs,
        )

    def update_extension(self, extension: str) -> None:
        info = SUPPORTED_FORMATS.get(
            extension.lower(),
            {"label": extension.upper() or "None", "icon": "📎"},
        )
        self.config(text=f"{info['icon']}  {info['label']}")


class SurveyCountBadge(tk.Label):
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent, text="–",
            font=_F["subheading"], fg=_C["text_disabled"],
            bg=_C["background"], **kwargs,
        )

    def update(self, count: int) -> None:
        if count == 0:
            self.config(text="0 survey numbers found", fg=_C["warning"])
        else:
            self.config(
                text=f"{count} survey number(s) found",
                fg=_C["success"],
            )

    def reset(self) -> None:
        self.config(text="–", fg=_C["text_disabled"])