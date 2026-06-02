"""
Janela principal do app — abas Configuração e Log/Status.
"""
import customtkinter as ctk

from ui.config_tab import ConfigTab
from ui.log_tab import LogTab
from sequence import State


_STATE_DISPLAY = {
    State.IDLE:         ("Aguardando keyword...",          "#888888"),
    State.MUTING:       ("Mutando entrada + STOP...",       "#ff9800"),
    State.AUDIO1:       ("Tocando Vinheta 1...",            "#4fc3f7"),
    State.STREAMING:    ("🔴  Streaming ativo!",              "#00e676"),
    State.AUDIO2:       ("Tocando Vinheta 2...",            "#4fc3f7"),
    State.PLAY_CMD:     ("Enviando comando PLAY...",        "#ff9800"),
    State.WAITING_NEXT: ("Aguardando retorno pelo TXT...",  "#ffa726"),
    State.STOP_RETURN:  ("STOP + Desmutando entrada...",    "#ff9800"),
}


class MainWindow(ctk.CTk):
    def __init__(self, config, audio_manager, sequence, file_monitor, player):
        super().__init__()

        self._config = config
        self._audio_mgr = audio_manager
        self._sequence = sequence
        self._file_monitor = file_monitor
        self._player_ref = player  # para ligar o log e configurar output device

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("MaisNova — Sport Trigger")
        self.geometry("760x620")
        self.minsize(620, 500)

        self._build_ui()
        self._connect_sequence()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Auto-iniciar monitor se TXT já estiver configurado
        self.after(500, self._auto_start_monitor)

    # ── layout ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=0)
        self.rowconfigure(3, weight=0)
        self.columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkFrame(self, height=54, corner_radius=0,
                               fg_color=("#0d0d1f", "#0a0a18"))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(1, weight=1)

        ctk.CTkLabel(
            header,
            text="  🎙  MaisNova Sport Trigger",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#4fc3f7",
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=16, pady=10)

        self._header_state = ctk.CTkLabel(
            header,
            text="● Parado",
            font=ctk.CTkFont(size=12),
            text_color="#888888",
            anchor="e",
        )
        self._header_state.grid(row=0, column=1, sticky="e", padx=16)

        # Tabs
        self._tabs = ctk.CTkTabview(self, corner_radius=8)
        self._tabs.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)

        self._tabs.add("⚙  Configuração")
        self._tabs.add("📋  Log / Status")

        # Log tab — criada primeiro para referência imediata nos logs
        self._log_tab = LogTab(
            self._tabs.tab("📋  Log / Status"),
            fg_color="transparent",
        )
        self._log_tab.pack(fill="both", expand=True)

        # Config tab
        self._config_tab = ConfigTab(
            self._tabs.tab("⚙  Configuração"),
            config=self._config,
            audio_manager=self._audio_mgr,
            on_save=self._on_config_saved,
            on_test=self._test_sequence,
            fg_color="transparent",
        )
        self._config_tab.pack(fill="both", expand=True)

        # Barra de controles
        ctrl = ctk.CTkFrame(self, height=48, corner_radius=0,
                            fg_color=("#141428", "#0e0e20"))
        ctrl.grid(row=2, column=0, sticky="ew")

        self._monitor_btn = ctk.CTkButton(
            ctrl, text="▶  Iniciar Monitor", width=170,
            fg_color="#1b5e20", hover_color="#0a3d12",
            command=self._toggle_monitor,
        )
        self._monitor_btn.pack(side="left", padx=(12, 6), pady=8)

        self._cancel_btn = ctk.CTkButton(
            ctrl, text="⏹  Cancelar Sequência", width=190,
            fg_color="#7f0000", hover_color="#560000",
            state="disabled",
            command=self._cancel_sequence,
        )
        self._cancel_btn.pack(side="left", padx=6, pady=8)

        self._monitor_dot = ctk.CTkLabel(
            ctrl, text="● Monitor parado",
            text_color="#ff4444",
            font=ctk.CTkFont(size=12),
        )
        self._monitor_dot.pack(side="right", padx=16)

        # Status bar
        self._statusbar = ctk.StringVar(value="  Pronto.")
        ctk.CTkLabel(
            self,
            textvariable=self._statusbar,
            height=22,
            corner_radius=0,
            fg_color=("#111120", "#0a0a18"),
            text_color="#555566",
            font=ctk.CTkFont(size=11),
            anchor="w",
        ).grid(row=3, column=0, sticky="ew")

    # ── sequence integration ─────────────────────────────────────────────────

    def _connect_sequence(self):
        """Liga callbacks da máquina de estados à UI."""
        def _on_state(state: State):
            text, color = _STATE_DISPLAY.get(state, ("Desconhecido", "#888888"))
            self._log_tab.set_status(text, color)
            self._log_tab.set_sequence_state(state.value)
            dot = f"\u25cf {text}"
            self.after(0, lambda: self._header_state.configure(text=dot, text_color=color))
            self.after(0, lambda: self._statusbar.set(f"  Estado: {text}"))

            is_idle = (state == State.IDLE)
            self.after(0, lambda: self._cancel_btn.configure(
                state="disabled" if is_idle else "normal"
            ))

        def _log(msg: str, level: str = "info"):
            self._log_tab.log(msg, level)

        self._sequence.set_on_state_change(_on_state)
        self._sequence._log = _log
        # Liga log do player à UI também
        self._player_ref.set_log(_log)

    # ── monitor ──────────────────────────────────────────────────────────────

    def _auto_start_monitor(self):
        if self._config.get("txt_file_path", ""):
            self._do_start_monitor()

    def _toggle_monitor(self):
        if self._file_monitor.is_running():
            self._file_monitor.stop()
            self._monitor_btn.configure(
                text="▶  Iniciar Monitor", fg_color="#1b5e20", hover_color="#0a3d12")
            self._monitor_dot.configure(text="● Monitor parado", text_color="#ff4444")
            self._log_tab.log("Monitor parado.", "warn")
        else:
            self._do_start_monitor()

    def _do_start_monitor(self):
        txt = self._config.get("txt_file_path", "")
        kw_start = self._config.get("keyword_start", "")
        kw_unmute = self._config.get("keyword_unmute", "")

        if not txt:
            self._log_tab.log("Configure o caminho do arquivo TXT primeiro.", "error")
            self._tabs.set("⚙  Configuração")
            return

        ok = self._file_monitor.start(
            filepath=txt,
            keyword_start=kw_start,
            keyword_unmute=kw_unmute,
            on_start=self._sequence.trigger_start,
            on_unmute=self._sequence.trigger_unmute,
            log_callback=lambda msg: self._log_tab.log(msg),
        )

        if ok:
            self._monitor_btn.configure(
                text="⏹  Parar Monitor", fg_color="#7f0000", hover_color="#560000")
            self._monitor_dot.configure(text="● Monitor ativo", text_color="#00e676")
            self._log_tab.log(f"Monitor ativo: {txt}", "success")
            self._log_tab.log(
                f"Aguardando keyword '{kw_start}' no arquivo...", "info")
        else:
            self._log_tab.log(
                f"Falha ao iniciar monitor. Verifique o arquivo: {txt}", "error")

    # ── misc ──────────────────────────────────────────────────────────────────

    def _on_config_saved(self, msg: str, error: bool = False):
        self._statusbar.set(f"  {msg}")
        self._log_tab.log(msg, "error" if error else "success")
        # Reaplicar dispositivo de saída ao player quando config for salva
        self._player_ref.set_output_device(self._config.get("output_device_id", ""))

    def _test_sequence(self):
        self._tabs.set("📋  Log / Status")
        self._log_tab.log("▶ Teste manual iniciado.", "info")
        self._sequence.trigger_start()

    def _cancel_sequence(self):
        self._sequence.cancel()

    def _on_close(self):
        """Fecha para a bandeja em vez de encerrar."""
        self.withdraw()

    def show(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def log(self, msg: str, level: str = "info"):
        self._log_tab.log(msg, level)
