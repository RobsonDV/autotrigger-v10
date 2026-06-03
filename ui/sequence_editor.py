"""
Editor de sequências — CTkToplevel modal.

Permite criar/editar:
  - Nome, keyword de trigger, habilitado
  - Lista de etapas (mover, excluir, editar via StepDialog)
"""
from __future__ import annotations

import copy
import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from typing import Callable, Optional

import audio_manager as _audio
import hotkey_sender as _hotkey

STEP_TYPES = [
    ("mute",          "🔇  Mute Dispositivo"),
    ("unmute",        "🔊  Unmute Dispositivo"),
    ("open_channel",  "📻  Abrir Canal (mute linha)"),
    ("close_channel", "🔕  Fechar Canal (unmute linha)"),
    ("hotkey",        "⌨  Enviar Hotkey"),
    ("play_audio",    "🎵  Tocar Áudio"),
    ("stream",        "📡  Streaming"),
    ("wait_time",     "⏳  Aguardar Tempo"),
    ("wait_keyword",  "🔍  Aguardar Keyword"),
]

_TYPE_LABELS = {t: lbl for t, lbl in STEP_TYPES}
_LABEL_TO_TYPE = {lbl: t for t, lbl in STEP_TYPES}


def _fmt_secs(seconds) -> str:
    """Convert seconds to 'Xm Ys' string."""
    s = int(seconds or 0)
    m, s = divmod(s, 60)
    if m:
        return f"{m}m {s}s" if s else f"{m}m"
    return f"{s}s"


def _parse_secs(text: str) -> int:
    """Parse '5m 30s', '330', '5:30' into seconds."""
    text = text.strip()
    if "m" in text or "s" in text:
        m = s = 0
        for part in text.replace("m", " ").replace("s", " ").split():
            try:
                val = int(part)
                if "m" in text and str(val) + "m" in text.replace(" ", ""):
                    m = val
                elif "s" in text and str(val) + "s" in text.replace(" ", ""):
                    s = val
                else:
                    m = val
            except ValueError:
                pass
        return m * 60 + s
    if ":" in text:
        parts = text.split(":")
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except Exception:
            pass
    try:
        return int(text)
    except ValueError:
        return 0


# ── Step dialog ───────────────────────────────────────────────────────────────

class StepDialog(ctk.CTkToplevel):
    """Modal dialog for editing a single step."""

    def __init__(self, parent, step: dict, on_save: Callable):
        super().__init__(parent)
        self._step = copy.deepcopy(step)
        self._on_save = on_save

        self.title("Editar Etapa")
        self.geometry("480x380")
        self.resizable(False, False)
        self.grab_set()
        self.focus_set()

        self._devices: list = []
        self._build()
        self._load_devices()
        self._update_fields()

    def _build(self):
        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)

        # Type selector
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        top.columnconfigure(1, weight=1)

        ctk.CTkLabel(top, text="Tipo:", anchor="w", width=80).grid(
            row=0, column=0, sticky="w"
        )
        self._type_var = ctk.StringVar(
            value=_TYPE_LABELS.get(self._step.get("type", "hotkey"), STEP_TYPES[4][1])
        )
        self._type_combo = ctk.CTkComboBox(
            top, variable=self._type_var,
            values=[lbl for _, lbl in STEP_TYPES],
            state="readonly",
            command=lambda _v: self._update_fields(),
        )
        self._type_combo.grid(row=0, column=1, sticky="ew")

        # Dynamic fields container
        self._fields_frame = ctk.CTkFrame(self, fg_color="transparent")
        self._fields_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=8)
        self._fields_frame.columnconfigure(1, weight=1)

        # Buttons
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 16))
        ctk.CTkButton(btns, text="Cancelar", width=100,
                      fg_color="#2a2a3a", hover_color="#3a3a4a",
                      command=self.destroy).pack(side="right", padx=4)
        ctk.CTkButton(btns, text="OK", width=100,
                      fg_color="#1565c0", hover_color="#0d47a1",
                      command=self._ok).pack(side="right", padx=4)

    def _load_devices(self):
        try:
            inputs = _audio.list_input_devices()
            outputs = _audio.list_output_devices()
            seen = set()
            all_devs = []
            for d in inputs + outputs:
                if d["id"] not in seen:
                    seen.add(d["id"])
                    all_devs.append(d)
            self._devices = all_devs
        except Exception:
            self._devices = []

    def _update_fields(self):
        for w in self._fields_frame.winfo_children():
            w.destroy()

        t = _LABEL_TO_TYPE.get(self._type_var.get(), self._step.get("type", "hotkey"))
        step = self._step
        frame = self._fields_frame
        row = 0

        def lbl(text):
            nonlocal row
            ctk.CTkLabel(frame, text=text, anchor="w", width=100).grid(
                row=row, column=0, sticky="w", pady=4
            )

        def entry(default="", width=300):
            nonlocal row
            var = ctk.StringVar(value=str(default))
            e = ctk.CTkEntry(frame, textvariable=var, width=width)
            e.grid(row=row, column=1, sticky="ew", pady=4)
            row += 1
            return var

        def device_row(default_id="", default_name=""):
            nonlocal row
            dev_names = [d["name"] for d in self._devices] or ["(nenhum)"]
            var = ctk.StringVar()
            # Try to match current device
            for d in self._devices:
                if d["id"] == default_id or d["name"] == default_name:
                    var.set(d["name"])
                    break
            else:
                var.set(dev_names[0])
            combo = ctk.CTkComboBox(frame, variable=var, values=dev_names,
                                    state="readonly", width=300)
            combo.grid(row=row, column=1, sticky="ew", pady=4)
            row += 1
            return var

        # ── field sets per type ──────────────────────────────────────────────
        if t in ("mute", "unmute", "open_channel", "close_channel"):
            lbl("Dispositivo:")
            self._f_device = device_row(step.get("device_id", ""),
                                        step.get("device_name", ""))
            lbl("Label:")
            self._f_label = entry(step.get("label", ""))

        elif t == "hotkey":
            lbl("Hotkey:")
            hk_frame = ctk.CTkFrame(frame, fg_color="transparent")
            hk_frame.grid(row=row, column=1, sticky="ew", pady=4)
            hk_frame.columnconfigure(0, weight=1)
            self._f_hotkey = ctk.StringVar(value=step.get("hotkey", ""))
            ctk.CTkEntry(hk_frame, textvariable=self._f_hotkey).grid(
                row=0, column=0, sticky="ew"
            )
            ctk.CTkButton(hk_frame, text="Capturar", width=80,
                          command=self._capture_hotkey).grid(
                row=0, column=1, padx=(4, 0)
            )
            row += 1
            lbl("Label:")
            self._f_label = entry(step.get("label", ""))

        elif t == "play_audio":
            lbl("Arquivo:")
            fa_frame = ctk.CTkFrame(frame, fg_color="transparent")
            fa_frame.grid(row=row, column=1, sticky="ew", pady=4)
            fa_frame.columnconfigure(0, weight=1)
            self._f_file = ctk.StringVar(value=step.get("file", ""))
            ctk.CTkEntry(fa_frame, textvariable=self._f_file).grid(
                row=0, column=0, sticky="ew"
            )
            ctk.CTkButton(fa_frame, text="📁", width=32,
                          command=self._browse_audio).grid(
                row=0, column=1, padx=(4, 0)
            )
            row += 1
            lbl("Label:")
            self._f_label = entry(step.get("label", ""))

        elif t == "stream":
            lbl("URL:")
            self._f_url = entry(step.get("url", ""))
            lbl("Duração:")
            dur_frame = ctk.CTkFrame(frame, fg_color="transparent")
            dur_frame.grid(row=row, column=1, sticky="ew", pady=4)
            self._f_dur = ctk.StringVar(
                value=_fmt_secs(step.get("duration_seconds", 300))
            )
            ctk.CTkEntry(dur_frame, textvariable=self._f_dur, width=120).pack(
                side="left"
            )
            ctk.CTkLabel(dur_frame, text="  ex: 30m, 5m 30s, 330",
                         text_color="#445566",
                         font=ctk.CTkFont(size=11)).pack(side="left")
            row += 1
            lbl("Label:")
            self._f_label = entry(step.get("label", "Stream"))

        elif t == "wait_time":
            lbl("Duração:")
            dur_frame = ctk.CTkFrame(frame, fg_color="transparent")
            dur_frame.grid(row=row, column=1, sticky="ew", pady=4)
            self._f_secs = ctk.StringVar(
                value=_fmt_secs(step.get("seconds", 60))
            )
            ctk.CTkEntry(dur_frame, textvariable=self._f_secs, width=120).pack(
                side="left"
            )
            ctk.CTkLabel(dur_frame, text="  ex: 30m, 5m 30s, 90",
                         text_color="#445566",
                         font=ctk.CTkFont(size=11)).pack(side="left")
            row += 1
            lbl("Label:")
            self._f_label = entry(step.get("label", "Aguardar"))

        elif t == "wait_keyword":
            lbl("Keyword:")
            self._f_kw = entry(step.get("keyword", ""))
            lbl("Label:")
            self._f_label = entry(step.get("label", "Aguardar keyword"))

    def _capture_hotkey(self):
        self._type_combo.configure(state="disabled")
        self.after(50, self._do_capture)

    def _do_capture(self):
        import threading
        def _run():
            hk = _hotkey.capture_hotkey()
            self.after(0, lambda: [
                self._f_hotkey.set(hk),
                self._type_combo.configure(state="readonly"),
            ])
        threading.Thread(target=_run, daemon=True).start()

    def _browse_audio(self):
        path = filedialog.askopenfilename(
            title="Selecionar arquivo de áudio",
            filetypes=[
                ("Áudio", "*.mp3 *.wav *.ogg *.flac *.aac"),
                ("Todos", "*.*"),
            ],
        )
        if path:
            self._f_file.set(path)

    def _ok(self):
        t = _LABEL_TO_TYPE.get(self._type_var.get(), "hotkey")
        step = {"type": t}

        if t in ("mute", "unmute", "open_channel", "close_channel"):
            name = self._f_device.get()
            device_id = ""
            for d in self._devices:
                if d["name"] == name:
                    device_id = d["id"]
                    break
            step["device_id"] = device_id
            step["device_name"] = name
            step["label"] = self._f_label.get() or name

        elif t == "hotkey":
            step["hotkey"] = self._f_hotkey.get()
            step["label"] = self._f_label.get() or self._f_hotkey.get()

        elif t == "play_audio":
            step["file"] = self._f_file.get()
            step["label"] = self._f_label.get() or "Áudio"

        elif t == "stream":
            step["url"] = self._f_url.get()
            step["duration_seconds"] = _parse_secs(self._f_dur.get())
            step["label"] = self._f_label.get() or "Stream"

        elif t == "wait_time":
            step["seconds"] = _parse_secs(self._f_secs.get())
            step["label"] = self._f_label.get() or "Aguardar"

        elif t == "wait_keyword":
            step["keyword"] = self._f_kw.get()
            step["label"] = self._f_label.get() or f"Aguardar {step['keyword']}"

        self._on_save(step)
        self.destroy()


# ── Sequence editor ───────────────────────────────────────────────────────────

class SequenceEditor(ctk.CTkToplevel):
    def __init__(self, parent, seq: dict, on_save: Callable):
        super().__init__(parent)
        self._seq = copy.deepcopy(seq)
        self._on_save = on_save

        self.title("Editor de Sequência")
        self.geometry("560x560")
        self.minsize(500, 480)
        self.grab_set()
        self.focus_set()

        self._build()
        self._load_values()

    def _build(self):
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

        # ── Header fields ─────────────────────────────────────────────────────
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 4))
        hdr.columnconfigure(1, weight=1)
        hdr.columnconfigure(3, weight=1)

        ctk.CTkLabel(hdr, text="Nome:", anchor="w", width=60).grid(
            row=0, column=0, sticky="w"
        )
        self._name_var = ctk.StringVar()
        ctk.CTkEntry(hdr, textvariable=self._name_var).grid(
            row=0, column=1, sticky="ew", padx=(4, 12)
        )

        ctk.CTkLabel(hdr, text="Keyword:", anchor="w", width=65).grid(
            row=0, column=2, sticky="w"
        )
        self._kw_var = ctk.StringVar()
        ctk.CTkEntry(hdr, textvariable=self._kw_var).grid(
            row=0, column=3, sticky="ew", padx=(4, 0)
        )

        # Enabled toggle
        self._enabled_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(hdr, text="Habilitada",
                        variable=self._enabled_var).grid(
            row=1, column=0, columnspan=2, pady=(6, 0), sticky="w"
        )

        # ── Steps label + toolbar ─────────────────────────────────────────────
        bar = ctk.CTkFrame(self, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(8, 2))
        ctk.CTkLabel(bar, text="ETAPAS",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#445577").pack(side="left")
        ctk.CTkButton(bar, text="＋  Adicionar Etapa", width=140,
                      fg_color="#1a3a6a", hover_color="#0d2a52",
                      command=self._add_step).pack(side="right")

        # ── Steps scrollable list ─────────────────────────────────────────────
        self._steps_scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self._steps_scroll.grid(row=2, column=0, sticky="nsew", padx=12, pady=4)
        self._steps_scroll.columnconfigure(0, weight=1)

        self._step_rows: list[ctk.CTkFrame] = []

        # ── Bottom buttons ────────────────────────────────────────────────────
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        ctk.CTkButton(btns, text="Cancelar", width=100,
                      fg_color="#2a2a3a", hover_color="#3a3a4a",
                      command=self.destroy).pack(side="right", padx=4)
        ctk.CTkButton(btns, text="Salvar", width=100,
                      fg_color="#1565c0", hover_color="#0d47a1",
                      command=self._save).pack(side="right", padx=4)

    def _load_values(self):
        self._name_var.set(self._seq.get("name", ""))
        self._kw_var.set(self._seq.get("keyword_trigger", ""))
        self._enabled_var.set(self._seq.get("enabled", True))
        self._rebuild_step_rows()

    def _rebuild_step_rows(self):
        for w in self._steps_scroll.winfo_children():
            w.destroy()
        self._step_rows.clear()

        steps = self._seq.get("steps", [])
        if not steps:
            ctk.CTkLabel(
                self._steps_scroll,
                text="Nenhuma etapa. Clique em '+ Adicionar Etapa'.",
                text_color="#445566",
            ).pack(pady=16)
            return

        for i, step in enumerate(steps):
            row = self._make_step_row(i, step)
            self._step_rows.append(row)

    def _make_step_row(self, idx: int, step: dict) -> ctk.CTkFrame:
        steps = self._seq.get("steps", [])
        n = len(steps)

        icon = {
            "mute": "🔇", "unmute": "🔊", "open_channel": "📻",
            "close_channel": "🔕", "hotkey": "⌨", "play_audio": "🎵",
            "stream": "📡", "wait_time": "⏳", "wait_keyword": "🔍",
        }.get(step.get("type", ""), "▸")

        label = step.get("label") or step.get("type", "?")
        t_label = _TYPE_LABELS.get(step.get("type", ""), step.get("type", ""))

        # Summary info per type
        summary = ""
        t = step.get("type", "")
        if t in ("mute", "unmute", "open_channel", "close_channel"):
            summary = step.get("device_name", step.get("device_id", ""))[:30]
        elif t == "hotkey":
            summary = step.get("hotkey", "")
        elif t == "play_audio":
            import os
            summary = os.path.basename(step.get("file", ""))[:30]
        elif t == "stream":
            summary = f"{step.get('url','')[:20]}  ·  {_fmt_secs(step.get('duration_seconds',0))}"
        elif t == "wait_time":
            summary = _fmt_secs(step.get("seconds", 0))
        elif t == "wait_keyword":
            summary = step.get("keyword", "")

        f = ctk.CTkFrame(
            self._steps_scroll, corner_radius=6,
            fg_color="#111120",
        )
        f.pack(fill="x", padx=2, pady=3)
        f.columnconfigure(1, weight=1)

        # Index + icon
        ctk.CTkLabel(f, text=f"{idx + 1}. {icon}",
                     width=44, font=ctk.CTkFont(size=13),
                     anchor="w").grid(row=0, column=0, padx=(8, 4), pady=6, sticky="w")

        # Info
        info = ctk.CTkFrame(f, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew")
        ctk.CTkLabel(info, text=label,
                     font=ctk.CTkFont(size=12, weight="bold"),
                     anchor="w").pack(anchor="w")
        ctk.CTkLabel(info, text=f"{t_label}  {('· ' + summary) if summary else ''}",
                     text_color="#556688",
                     font=ctk.CTkFont(size=10), anchor="w").pack(anchor="w")

        # Buttons
        btn_f = ctk.CTkFrame(f, fg_color="transparent")
        btn_f.grid(row=0, column=2, padx=6, pady=6)

        ctk.CTkButton(btn_f, text="✎", width=28, height=26,
                      command=lambda i=idx: self._edit_step(i)).pack(side="left", padx=2)
        ctk.CTkButton(btn_f, text="↑", width=28, height=26,
                      state="normal" if idx > 0 else "disabled",
                      command=lambda i=idx: self._move_step(i, -1)).pack(side="left", padx=2)
        ctk.CTkButton(btn_f, text="↓", width=28, height=26,
                      state="normal" if idx < n - 1 else "disabled",
                      command=lambda i=idx: self._move_step(i, 1)).pack(side="left", padx=2)
        ctk.CTkButton(btn_f, text="✕", width=28, height=26,
                      fg_color="#4a1a1a", hover_color="#6a2020",
                      command=lambda i=idx: self._del_step(i)).pack(side="left", padx=2)

        return f

    # ── step operations ───────────────────────────────────────────────────────

    def _add_step(self):
        new_step = {"type": "hotkey", "hotkey": "", "label": "Nova Etapa"}
        StepDialog(self, new_step, on_save=self._on_step_added)

    def _on_step_added(self, step: dict):
        self._seq.setdefault("steps", []).append(step)
        self._rebuild_step_rows()

    def _edit_step(self, idx: int):
        steps = self._seq.get("steps", [])
        if 0 <= idx < len(steps):
            StepDialog(self, steps[idx], on_save=lambda s, i=idx: self._on_step_edited(i, s))

    def _on_step_edited(self, idx: int, step: dict):
        self._seq["steps"][idx] = step
        self._rebuild_step_rows()

    def _move_step(self, idx: int, direction: int):
        steps = self._seq.get("steps", [])
        new_idx = idx + direction
        if 0 <= new_idx < len(steps):
            steps[idx], steps[new_idx] = steps[new_idx], steps[idx]
            self._rebuild_step_rows()

    def _del_step(self, idx: int):
        steps = self._seq.get("steps", [])
        if 0 <= idx < len(steps):
            del steps[idx]
            self._rebuild_step_rows()

    # ── save ──────────────────────────────────────────────────────────────────

    def _save(self):
        self._seq["name"] = self._name_var.get() or "Sequência"
        self._seq["keyword_trigger"] = self._kw_var.get().strip().upper()
        self._seq["enabled"] = self._enabled_var.get()
        self._on_save(self._seq)
        self.destroy()
