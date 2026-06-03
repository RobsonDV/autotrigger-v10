"""
JourneyView — Painel principal da tela de execução.

Layout:
  ┌─────────────────────────────────────────────────────┐
  │ [Sidebar: cards das sequências]  [Detalhe da seq]   │
  │                                  [Step flow visual] │
  │                                  [Timer]            │
  │                                  [Log em tempo real]│
  └─────────────────────────────────────────────────────┘
"""
from __future__ import annotations

import customtkinter as ctk
import tkinter as tk
from datetime import datetime
from typing import Callable, Dict, Optional

STEP_ICONS = {
    "mute":          "🔇",
    "unmute":        "🔊",
    "open_channel":  "📻",
    "close_channel": "🔕",
    "hotkey":        "⌨",
    "play_audio":    "🎵",
    "stream":        "📡",
    "wait_time":     "⏳",
    "wait_keyword":  "🔍",
}

_STATE_COLORS = {
    "idle":      "#444466",
    "running":   "#00e676",
    "done":      "#4fc3f7",
    "error":     "#ff5252",
    "cancelled": "#ff9800",
}

_STATE_TEXTS = {
    "idle":      ("● Aguardando", "#556688"),
    "running":   ("● Executando", "#00e676"),
    "done":      ("✓ Concluída",  "#4fc3f7"),
    "error":     ("✗ Erro",       "#ff5252"),
    "cancelled": ("⏹ Cancelado",  "#ff9800"),
}


# ── Sequence card (sidebar) ───────────────────────────────────────────────────

class _SequenceCard(ctk.CTkFrame):
    def __init__(self, parent, seq: dict, on_click: Callable, **kw):
        super().__init__(parent, corner_radius=8, **kw)
        self._seq = seq
        self._on_click = on_click
        self._build()
        for w in (self, self._dot, self._name, self._kw_lbl):
            w.bind("<Button-1>", lambda _e: self._on_click(self._seq["id"]))

    def _build(self):
        self.columnconfigure(1, weight=1)
        self._dot = ctk.CTkLabel(
            self, text="●", width=18, text_color="#444466",
            font=ctk.CTkFont(size=15),
        )
        self._dot.grid(row=0, column=0, rowspan=2, padx=(8, 4), pady=8, sticky="ns")

        self._name = ctk.CTkLabel(
            self, text=self._seq.get("name", ""),
            font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
        )
        self._name.grid(row=0, column=1, sticky="ew", padx=(0, 8), pady=(8, 2))

        kw = self._seq.get("keyword_trigger", "")
        self._kw_lbl = ctk.CTkLabel(
            self, text=f"⌁ {kw}", text_color="#666688",
            font=ctk.CTkFont(size=11), anchor="w",
        )
        self._kw_lbl.grid(row=1, column=1, sticky="ew", padx=(0, 8), pady=(0, 8))

    def set_selected(self, v: bool):
        self.configure(fg_color="#142a4a" if v else "transparent")

    def set_state(self, state: str):
        self._dot.configure(text_color=_STATE_COLORS.get(state, "#444466"))

    def update_seq(self, seq: dict):
        self._seq = seq
        self._name.configure(text=seq.get("name", ""))
        self._kw_lbl.configure(text=f"⌁ {seq.get('keyword_trigger', '')}")


# ── Step box (flow visual) ─────────────────────────────────────────────────────

_STEP_BG = {
    "pending":   "#111122",
    "active":    "#0d2a52",
    "done":      "#0d3a1a",
    "error":     "#3a0d0d",
}
_STEP_BORDER = {
    "pending":   "#2a2a3a",
    "active":    "#2979ff",
    "done":      "#2e7d32",
    "error":     "#b71c1c",
}


class _StepBox(ctk.CTkFrame):
    def __init__(self, parent, step: dict, **kw):
        super().__init__(
            parent, corner_radius=8, width=88, height=70,
            fg_color=_STEP_BG["pending"],
            border_color=_STEP_BORDER["pending"], border_width=1,
            **kw,
        )
        self.pack_propagate(False)
        self._build(step)

    def _build(self, step: dict):
        icon = STEP_ICONS.get(step.get("type", ""), "▸")
        label = step.get("label") or step.get("type", "?")
        if len(label) > 10:
            label = label[:9] + "…"

        self._icon_lbl = ctk.CTkLabel(
            self, text=icon, font=ctk.CTkFont(size=17),
        )
        self._icon_lbl.pack(pady=(8, 1))

        self._txt_lbl = ctk.CTkLabel(
            self, text=label, font=ctk.CTkFont(size=9),
            text_color="#8888aa", wraplength=80,
        )
        self._txt_lbl.pack(pady=(0, 4))

    def set_status(self, status: str):
        self.configure(
            fg_color=_STEP_BG.get(status, _STEP_BG["pending"]),
            border_color=_STEP_BORDER.get(status, _STEP_BORDER["pending"]),
            border_width=2 if status == "active" else 1,
        )
        text_colors = {
            "active": "#ffffff",
            "done":   "#80e0a0",
            "error":  "#ff8a80",
        }
        self._txt_lbl.configure(
            text_color=text_colors.get(status, "#8888aa")
        )


# ── Main view ─────────────────────────────────────────────────────────────────

class JourneyView(ctk.CTkFrame):
    def __init__(self, parent, **kw):
        super().__init__(parent, **kw)
        self._cards: Dict[str, _SequenceCard] = {}
        self._selected_id: Optional[str] = None
        self._step_boxes: list[_StepBox] = []

        # Callbacks set by MainWindow
        self._on_cancel_cb: Optional[Callable] = None
        self._on_select_cb: Optional[Callable] = None  # (seq_id) -> None
        self._on_new_cb: Optional[Callable] = None

        self._build()

    # ── callbacks ─────────────────────────────────────────────────────────────

    def set_on_cancel(self, fn: Callable):
        self._on_cancel_cb = fn

    def set_on_select(self, fn: Callable):
        """fn(seq_id) called when user clicks a sidebar card."""
        self._on_select_cb = fn

    def set_on_new(self, fn: Callable):
        self._on_new_cb = fn

    # ── public API ────────────────────────────────────────────────────────────

    def load_sequences(self, sequences: list):
        """Rebuild sidebar from sequence list."""
        for c in self._cards.values():
            c.destroy()
        self._cards.clear()
        for seq in sequences:
            self._add_card(seq)
        if sequences:
            self._auto_select(sequences[0]["id"], sequences[0].get("steps", []),
                              sequences[0].get("name", ""))

    def update_card(self, seq: dict):
        sid = seq["id"]
        if sid in self._cards:
            self._cards[sid].update_seq(seq)
            if self._selected_id == sid:
                self._seq_name_lbl.configure(text=seq.get("name", ""))
                self._rebuild_step_boxes(seq.get("steps", []))
        else:
            self._add_card(seq)

    def remove_card(self, seq_id: str):
        if seq_id in self._cards:
            self._cards[seq_id].destroy()
            del self._cards[seq_id]
        if self._selected_id == seq_id:
            self._clear_detail()

    def select_sequence(self, seq: dict):
        """Select a sequence and display its steps."""
        self._auto_select(seq["id"], seq.get("steps", []), seq.get("name", ""))

    def set_runner_state(self, seq_id: str, state_name: str, step_idx: int):
        """Called (on main thread) when a runner's state/step changes."""
        if seq_id in self._cards:
            self._cards[seq_id].set_state(state_name)
        if self._selected_id == seq_id:
            self._update_step_display(step_idx, state_name)
            txt, color = _STATE_TEXTS.get(state_name, ("", "#556688"))
            self._status_lbl.configure(text=txt, text_color=color)
            if state_name == "running":
                self._cancel_btn.grid()
            else:
                self._cancel_btn.grid_remove()
            if state_name not in ("running",):
                self._timer_lbl.configure(text="")

    def set_tick(self, seq_id: str, step_idx: int, elapsed: float, total: float):
        """Called (on main thread) on each tick for timed steps."""
        if self._selected_id != seq_id:
            return
        e_m, e_s = divmod(int(elapsed), 60)
        t_m, t_s = divmod(int(total), 60)
        self._timer_lbl.configure(
            text=f"⏱  {e_m:02d}:{e_s:02d}  /  {t_m:02d}:{t_s:02d}"
        )

    def log(self, msg: str, level: str = "info"):
        """Append a line to the log box."""
        colors = {
            "info":    "#ccccdd",
            "success": "#80e0a0",
            "warn":    "#ffb74d",
            "error":   "#ff8a80",
        }
        self._log_box.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_box.insert("end", f"[{ts}] ", "ts")
        self._log_box.insert("end", msg + "\n", level)
        self._log_box.tag_config("ts", foreground="#445566")
        self._log_box.tag_config(level, foreground=colors.get(level, "#ccccdd"))
        self._log_box.configure(state="disabled")
        self._log_box.see("end")

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        self.rowconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        # ── Left sidebar ──────────────────────────────────────────────────────
        sidebar = ctk.CTkFrame(
            self, width=220, corner_radius=0,
            fg_color=("#0b0b1a", "#080812"),
        )
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.rowconfigure(1, weight=1)
        sidebar.grid_propagate(False)

        ctk.CTkLabel(
            sidebar, text="SEQUÊNCIAS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#445577",
        ).pack(pady=(12, 4), padx=12, anchor="w")

        self._cards_frame = ctk.CTkScrollableFrame(
            sidebar, fg_color="transparent",
        )
        self._cards_frame.pack(fill="both", expand=True, padx=6, pady=4)

        ctk.CTkButton(
            sidebar, text="＋  Nova Sequência", height=32,
            fg_color="#1a3a6a", hover_color="#0d2a52",
            command=lambda: self._on_new_cb and self._on_new_cb(),
        ).pack(fill="x", padx=8, pady=(4, 8))

        # ── Right detail panel ────────────────────────────────────────────────
        right = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)

        # Header bar
        hdr = ctk.CTkFrame(
            right, height=42, corner_radius=0,
            fg_color=("#0c1a2a", "#070d14"),
        )
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.columnconfigure(1, weight=1)

        self._seq_name_lbl = ctk.CTkLabel(
            hdr, text="Selecione uma sequência",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#888899",
        )
        self._seq_name_lbl.grid(row=0, column=0, padx=14, pady=8, sticky="w")

        self._status_lbl = ctk.CTkLabel(
            hdr, text="", text_color="#445566",
            font=ctk.CTkFont(size=12),
        )
        self._status_lbl.grid(row=0, column=1, padx=8, pady=8, sticky="e")

        self._cancel_btn = ctk.CTkButton(
            hdr, text="⏹  Cancelar", width=110, height=28,
            fg_color="#7f0000", hover_color="#560000",
            command=self._on_cancel,
        )
        self._cancel_btn.grid(row=0, column=2, padx=8, pady=7)
        self._cancel_btn.grid_remove()

        # Step flow (horizontal scroll)
        flow_outer = ctk.CTkFrame(
            right, height=96, corner_radius=0,
            fg_color=("#080818", "#050510"),
        )
        flow_outer.grid(row=1, column=0, sticky="ew")
        flow_outer.grid_propagate(False)

        self._flow_scroll = ctk.CTkScrollableFrame(
            flow_outer, orientation="horizontal",
            height=86, fg_color="transparent",
        )
        self._flow_scroll.pack(fill="both", expand=True, padx=8, pady=4)

        # Timer label
        self._timer_lbl = ctk.CTkLabel(
            right, text="",
            text_color="#ffd54f",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        )
        self._timer_lbl.grid(row=2, column=0, sticky="w", padx=16, pady=(4, 0))

        # Log box
        log_frame = ctk.CTkFrame(right, corner_radius=0, fg_color="transparent")
        log_frame.grid(row=3, column=0, sticky="nsew")
        log_frame.rowconfigure(1, weight=1)
        log_frame.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            log_frame, text="  📋  Log em tempo real",
            font=ctk.CTkFont(size=11), text_color="#445566",
            anchor="w",
        ).grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))

        self._log_box = ctk.CTkTextbox(
            log_frame, state="disabled", wrap="word",
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=("#080816", "#04040e"),
            text_color="#ccccdd",
        )
        self._log_box.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

    # ── internals ─────────────────────────────────────────────────────────────

    def _add_card(self, seq: dict):
        sid = seq["id"]
        card = _SequenceCard(
            self._cards_frame, seq,
            on_click=self._on_card_click,
            fg_color="transparent",
        )
        card.pack(fill="x", padx=4, pady=3)
        self._cards[sid] = card

    def _on_card_click(self, seq_id: str):
        if self._on_select_cb:
            self._on_select_cb(seq_id)

    def _auto_select(self, seq_id: str, steps: list, name: str):
        if self._selected_id and self._selected_id in self._cards:
            self._cards[self._selected_id].set_selected(False)
        self._selected_id = seq_id
        if seq_id in self._cards:
            self._cards[seq_id].set_selected(True)
        self._seq_name_lbl.configure(text=name, text_color="#e0e0f0")
        self._rebuild_step_boxes(steps)
        self._status_lbl.configure(text="● Aguardando", text_color="#445566")
        self._timer_lbl.configure(text="")
        self._cancel_btn.grid_remove()

    def _rebuild_step_boxes(self, steps: list):
        for w in self._flow_scroll.winfo_children():
            w.destroy()
        self._step_boxes.clear()

        if not steps:
            ctk.CTkLabel(
                self._flow_scroll,
                text="Nenhuma etapa configurada",
                text_color="#445566",
                font=ctk.CTkFont(size=12),
            ).pack(padx=16, pady=24)
            return

        for i, step in enumerate(steps):
            box = _StepBox(self._flow_scroll, step)
            box.pack(side="left", padx=(4, 0), pady=8)
            self._step_boxes.append(box)
            if i < len(steps) - 1:
                ctk.CTkLabel(
                    self._flow_scroll, text="›",
                    text_color="#2a3a4a",
                    font=ctk.CTkFont(size=18),
                ).pack(side="left", padx=2)

    def _update_step_display(self, active_idx: int, state: str):
        n = len(self._step_boxes)
        for i, box in enumerate(self._step_boxes):
            if state == "done" and active_idx >= n:
                box.set_status("done")
            elif i < active_idx:
                box.set_status("done")
            elif i == active_idx:
                box.set_status("error" if state == "error" else
                               "pending" if state == "cancelled" else "active")
            else:
                box.set_status("pending")

    def _clear_detail(self):
        self._seq_name_lbl.configure(
            text="Selecione uma sequência", text_color="#888899"
        )
        self._status_lbl.configure(text="")
        self._timer_lbl.configure(text="")
        for w in self._flow_scroll.winfo_children():
            w.destroy()
        self._step_boxes.clear()
        self._cancel_btn.grid_remove()
        self._selected_id = None

    def _on_cancel(self):
        if self._on_cancel_cb and self._selected_id:
            self._on_cancel_cb(self._selected_id)
