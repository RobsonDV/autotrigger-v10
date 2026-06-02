"""
Aba de Log / Status em tempo real com painel visual da sequência.
"""
import threading
from datetime import datetime

import customtkinter as ctk

_LEVEL_COLORS = {
    "info":    "#cccccc",
    "warn":    "#ffc200",
    "error":   "#ff4444",
    "success": "#66bb6a",
}

# Definição visual dos passos da sequência
# (label_top, label_bottom, estado State correspondente)
_STEPS = [
    ("🔇 MUTE",   "⏹ STOP",     "muting"),
    ("🎵",        "VINHETA 1",   "audio1"),
    ("📡",        "STREAMING",   "streaming"),
    ("🎵",        "VINHETA 2",   "audio2"),
    ("▶",         "PLAY",        "play_cmd"),
    ("⏳",        "AGUARDANDO",  "waiting_next"),
    ("⏹ STOP",   "🔊 DESMUTE",  "stop_return"),
]

_COLOR_IDLE    = ("#1a1a2e", "#111122")
_COLOR_ACTIVE  = ("#1565c0", "#0d47a1")
_COLOR_DONE    = ("#1b5e20", "#0a3d12")
_TEXT_IDLE     = "#444466"
_TEXT_ACTIVE   = "#ffffff"
_TEXT_DONE     = "#66bb6a"


class SequencePanel(ctk.CTkFrame):
    """Painel visual com os passos da jornada esportiva."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._step_frames: list[ctk.CTkFrame] = []
        self._step_labels_top: list[ctk.CTkLabel] = []
        self._step_labels_bot: list[ctk.CTkLabel] = []
        self._current_step = -1
        self._build()

    def _build(self):
        self.columnconfigure(tuple(range(len(_STEPS) * 2 - 1)), weight=1)

        for i, (top, bot, _) in enumerate(_STEPS):
            col = i * 2  # colunas pares = steps, ímpares = setas

            frame = ctk.CTkFrame(
                self,
                fg_color=_COLOR_IDLE,
                corner_radius=8,
                border_width=1,
                border_color=("#222244", "#1a1a33"),
            )
            frame.grid(row=0, column=col, padx=3, pady=6, sticky="ew")
            frame.columnconfigure(0, weight=1)

            lbl_top = ctk.CTkLabel(
                frame, text=top,
                font=ctk.CTkFont(size=16),
                text_color=_TEXT_IDLE,
            )
            lbl_top.grid(row=0, column=0, padx=6, pady=(8, 2))

            lbl_bot = ctk.CTkLabel(
                frame, text=bot,
                font=ctk.CTkFont(size=9, weight="bold"),
                text_color=_TEXT_IDLE,
            )
            lbl_bot.grid(row=1, column=0, padx=6, pady=(0, 8))

            self._step_frames.append(frame)
            self._step_labels_top.append(lbl_top)
            self._step_labels_bot.append(lbl_bot)

            # Seta entre passos
            if i < len(_STEPS) - 1:
                ctk.CTkLabel(
                    self, text="→",
                    font=ctk.CTkFont(size=16),
                    text_color="#333355",
                ).grid(row=0, column=col + 1, padx=1)

    def set_active_state(self, state_value: str):
        """Atualiza o passo ativo pelo valor do State enum."""
        target = -1
        for i, (_, _, sv) in enumerate(_STEPS):
            if sv == state_value:
                target = i
                break

        if target == self._current_step:
            return

        self._current_step = target

        for i, (frame, lt, lb) in enumerate(
            zip(self._step_frames, self._step_labels_top, self._step_labels_bot)
        ):
            if i < target:
                # Passo concluído
                frame.configure(fg_color=_COLOR_DONE, border_color=("#2e7d32", "#1b5e20"))
                lt.configure(text_color=_TEXT_DONE)
                lb.configure(text_color=_TEXT_DONE)
            elif i == target:
                # Passo ativo
                frame.configure(fg_color=_COLOR_ACTIVE, border_color=("#42a5f5", "#1565c0"))
                lt.configure(text_color=_TEXT_ACTIVE)
                lb.configure(text_color=_TEXT_ACTIVE)
            else:
                # Passo futuro
                frame.configure(fg_color=_COLOR_IDLE, border_color=("#222244", "#1a1a33"))
                lt.configure(text_color=_TEXT_IDLE)
                lb.configure(text_color=_TEXT_IDLE)

    def reset(self):
        self._current_step = -1
        for frame, lt, lb in zip(
            self._step_frames, self._step_labels_top, self._step_labels_bot
        ):
            frame.configure(fg_color=_COLOR_IDLE, border_color=("#222244", "#1a1a33"))
            lt.configure(text_color=_TEXT_IDLE)
            lb.configure(text_color=_TEXT_IDLE)


class LogTab(ctk.CTkFrame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._lock = threading.Lock()
        self._build_ui()

    def _build_ui(self):
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

        # Painel visual de sequência
        ctk.CTkLabel(
            self,
            text="FLUXO DA JORNADA ESPORTIVA",
            font=ctk.CTkFont(size=10, weight="bold"),
            text_color="#444466",
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=12, pady=(8, 0))

        self.sequence_panel = SequencePanel(
            self,
            fg_color=("#0d0d1e", "#080810"),
            corner_radius=8,
        )
        self.sequence_panel.grid(row=1, column=0, sticky="ew", padx=8, pady=(2, 6))

        # Banner de status atual
        self._status_var = ctk.StringVar(value="Aguardando...")
        self._status_label = ctk.CTkLabel(
            self,
            textvariable=self._status_var,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=("#1a1a2e", "#111122"),
            corner_radius=6,
            height=36,
            anchor="center",
        )
        self._status_label.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 4))

        # Área de log
        self._log_text = ctk.CTkTextbox(
            self,
            state="disabled",
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self._log_text.grid(row=3, column=0, sticky="nsew", padx=8, pady=4)
        self.rowconfigure(3, weight=1)

        # Botão limpar
        ctk.CTkButton(
            self,
            text="Limpar Log",
            width=120,
            height=28,
            command=self._clear,
        ).grid(row=4, column=0, sticky="e", padx=8, pady=(0, 8))

    # ── public API ──────────────────────────────────────────────────────────

    def log(self, message: str, level: str = "info"):
        """Adiciona uma linha ao log com timestamp. Thread-safe."""
        ts = datetime.now().strftime("%H:%M:%S")
        color = _LEVEL_COLORS.get(level, _LEVEL_COLORS["info"])
        tag = f"lvl_{level}"
        line = f"[{ts}] {message}\n"

        def _update():
            with self._lock:
                self._log_text.configure(state="normal")
                self._log_text.insert("end", line)
                try:
                    last_start = self._log_text.index("end-2l")
                    last_end = self._log_text.index("end-1c")
                    self._log_text.tag_config(tag, foreground=color)
                    self._log_text.tag_add(tag, last_start, last_end)
                except Exception:
                    pass
                self._log_text.configure(state="disabled")
                self._log_text.see("end")

        self.after(0, _update)

    def set_status(self, text: str, color: str = "#4fc3f7"):
        """Atualiza o banner de status."""
        def _update():
            self._status_var.set(text)
            self._status_label.configure(text_color=color)
        self.after(0, _update)

    def set_sequence_state(self, state_value: str):
        """Atualiza o painel visual de sequência. Thread-safe."""
        def _update():
            if state_value == "idle":
                self.sequence_panel.reset()
            else:
                self.sequence_panel.set_active_state(state_value)
        self.after(0, _update)

    # ── private ─────────────────────────────────────────────────────────────

    def _clear(self):
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")
