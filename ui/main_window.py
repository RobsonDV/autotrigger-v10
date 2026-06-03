"""

Janela principal v2 — AutoTrigger V10.

Layout:

  Header:  logo | botão ⚙ Configurações | versão/update

  Body:    JourneyView (sidebar + step flow + log)

  Bottom:  status bar + botão monitor

"""

import customtkinter as ctk

from version import __version__

from ui.journey_view import JourneyView

class MainWindow(ctk.CTk):

    def __init__(self, config, engine, player):

        super().__init__()

        self._config = config

        self._engine = engine

        self._player = player

        self._pending_update = None

        ctk.set_appearance_mode("dark")

        ctk.set_default_color_theme("blue")

        self.title("AutoTrigger V10")

        self.geometry("900x640")

        self.minsize(720, 500)

        # Icone da janela
        import os, sys
        _base = sys._MEIPASS if getattr(sys, "frozen", False) else os.path.dirname(
            os.path.abspath(__file__))
        _ico = os.path.join(os.path.dirname(_base), "assets", "icon.ico")
        if os.path.exists(_ico):
            try:
                self.iconbitmap(_ico)
            except Exception:
                pass

        self._build_ui()

        self._connect_engine()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self.after(300, self._load_sequences)

        self.after(600, self._auto_start_monitor)

        self.after(3000, self._init_updater)

    # ── build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):

        self.rowconfigure(1, weight=1)

        self.columnconfigure(0, weight=1)

        # ── Header ───────────────────────────────────────────────────────────

        hdr = ctk.CTkFrame(

            self, height=54, corner_radius=0,

            fg_color=("#0d0d1f", "#0a0a18"),

        )

        hdr.grid(row=0, column=0, sticky="ew")

        hdr.columnconfigure(1, weight=1)

        ctk.CTkLabel(

            hdr,

            text="  ⚡  AutoTrigger V10",

            font=ctk.CTkFont(size=18, weight="bold"),

            text_color="#4fc3f7",

            anchor="w",

        ).grid(row=0, column=0, sticky="w", padx=16, pady=10)

        self._settings_btn = ctk.CTkButton(

            hdr, text="⚙  Configurações", width=140, height=30,

            fg_color="#1a2a3a", hover_color="#243444",

            font=ctk.CTkFont(size=12),

            command=self._open_settings,

        )

        self._settings_btn.grid(row=0, column=1, sticky="e", padx=(4, 4), pady=12)

        self._update_btn = ctk.CTkButton(

            hdr, text=f"v{__version__}", width=80, height=28,

            fg_color="transparent", hover_color="#1a1a3a",

            text_color="#555577", font=ctk.CTkFont(size=11),

            command=self._check_for_updates_manual,

        )

        self._update_btn.grid(row=0, column=2, sticky="e", padx=(0, 8), pady=12)

        # ── Journey View ─────────────────────────────────────────────────────

        self._journey = JourneyView(self, fg_color="transparent")

        self._journey.grid(row=1, column=0, sticky="nsew")

        self._journey.set_on_cancel(self._engine.cancel)

        self._journey.set_on_select(self._on_seq_selected)

        self._journey.set_on_new(self._new_sequence)

        # ── Status bar ───────────────────────────────────────────────────────

        statusbar = ctk.CTkFrame(

            self, height=40, corner_radius=0,

            fg_color=("#0a0a1a", "#070710"),

        )

        statusbar.grid(row=2, column=0, sticky="ew")

        statusbar.columnconfigure(1, weight=1)

        self._monitor_btn = ctk.CTkButton(

            statusbar, text="▶  Iniciar Monitor", width=160, height=28,

            fg_color="#1b5e20", hover_color="#0a3d12",

            font=ctk.CTkFont(size=12),

            command=self._toggle_monitor,

        )

        self._monitor_btn.grid(row=0, column=0, padx=(10, 6), pady=6, sticky="w")

        self._monitor_dot = ctk.CTkLabel(

            statusbar, text="●  Monitor parado",

            text_color="#ff4444",

            font=ctk.CTkFont(size=12),

        )

        self._monitor_dot.grid(row=0, column=1, padx=8, pady=6, sticky="w")

        self._statusbar_var = ctk.StringVar(value="  Pronto.")

        ctk.CTkLabel(

            statusbar,

            textvariable=self._statusbar_var,

            text_color="#445566",

            font=ctk.CTkFont(size=11),

            anchor="e",

        ).grid(row=0, column=2, padx=16, pady=6, sticky="e")

    # ── engine connection ─────────────────────────────────────────────────────

    def _connect_engine(self):

        def _on_update(seq_id: str, state_name: str, step_idx: int):

            self.after(0, lambda: self._journey.set_runner_state(

                seq_id, state_name, step_idx

            ))

        def _on_tick(seq_id: str, step_idx: int, elapsed: float, total: float):

            self.after(0, lambda: self._journey.set_tick(

                seq_id, step_idx, elapsed, total

            ))

        def _log(msg: str, level: str = "info"):

            self.after(0, lambda: self._journey.log(msg, level))

        self._engine.set_on_runner_update(_on_update)

        self._engine.set_on_tick(_on_tick)

        self._engine.set_log(_log)

    # ── sequence management ───────────────────────────────────────────────────

    def _load_sequences(self):

        seqs = self._config.get_sequences()

        self._journey.load_sequences(seqs)

    def _on_seq_selected(self, seq_id: str):

        seq = self._config.get_sequence_by_id(seq_id)

        if not seq:

            return

        self._journey.select_sequence(seq)

        runner = self._engine.get_runner(seq_id)

        if runner:

            self._journey.set_runner_state(seq_id, runner.state.value, runner.current_step)

    def _new_sequence(self):

        seq = self._config.new_sequence_template()

        self._open_sequence_editor(seq, is_new=True)

    # ── monitor ───────────────────────────────────────────────────────────────

    def _auto_start_monitor(self):

        if self._config.get_global().get("txt_file_path", ""):

            self._do_start_monitor()

    def _toggle_monitor(self):

        if self._engine.is_monitor_running():

            self._engine.stop_monitor()

            self._monitor_btn.configure(
                text="▶  Iniciar Monitor",

                fg_color="#1b5e20", hover_color="#0a3d12",

            )

            self._monitor_dot.configure(text="●  Monitor parado", text_color="#ff4444")

            self._journey.log("Monitor parado.", "warn")

        else:

            self._do_start_monitor()

    def _do_start_monitor(self):

        ok = self._engine.start_monitor()

        if ok:

            self._monitor_btn.configure(

                text="⏹  Parar Monitor",

                fg_color="#7f0000", hover_color="#560000",

            )

            self._monitor_dot.configure(text="●  Monitor ativo", text_color="#00e676")

            txt = self._config.get_global().get("txt_file_path", "")

            self._journey.log(f"Monitor ativo: {txt}", "success")

        else:

            self._journey.log(

                "Falha ao iniciar monitor. Verifique o caminho do TXT nas configurações.",

                "error",

            )

    # ── settings / editor ────────────────────────────────────────────────────

    def _open_settings(self):

        from ui.settings_window import SettingsWindow

        SettingsWindow(

            self,

            config=self._config,

            on_saved=self._on_settings_saved,

            on_edit_sequence=self._open_sequence_editor,

        )

    def _open_sequence_editor(self, seq: dict, is_new: bool = False):

        from ui.sequence_editor import SequenceEditor

        SequenceEditor(

            self,

            seq=seq,

            on_save=lambda s: self._on_seq_saved(s, is_new),

        )

    def _on_settings_saved(self):

        self._journey.log("Configurações salvas.", "success")

        self._engine.reload_sequences()

        self._load_sequences()

    def _on_seq_saved(self, seq: dict, is_new: bool):

        if is_new:

            self._config.add_sequence(seq)

        else:

            self._config.update_sequence(seq)

        self._config.save()

        self._journey.update_card(seq)

        self._engine.reload_sequences()

        self._journey.log(f"Sequência '{seq.get('name', '')}' salva.", "success")

    # ── auto-update ───────────────────────────────────────────────────────────

    def _init_updater(self):

        try:

            from updater import Updater

            self._updater = Updater(

                log_callback=lambda msg, level="info": self._journey.log(msg, level)

            )

            def _on_available(info):

                self.after(0, lambda: self._show_update_badge(info))

            self._updater.check_async(on_update_available=_on_available)

        except Exception as exc:

            self._journey.log(f"Auto-update: {exc}", "warn")

    def _show_update_badge(self, info):

        self._pending_update = info

        self._update_btn.configure(

            text=f"🔔 v{info.version} disponível",

            fg_color="#1565c0", hover_color="#0d47a1",

            text_color="#ffffff", width=180,

        )

        self._journey.log(

            f"Nova versão disponível: v{info.version} — clique no botão para instalar.",

            "success",

        )

    def _check_for_updates_manual(self):

        if self._pending_update:

            self._open_update_dialog(self._pending_update)

            return

        self._update_btn.configure(text="Verificando...", state="disabled")

        try:

            from updater import Updater

            u = Updater(

                log_callback=lambda msg, level="info": self._journey.log(msg, level)

            )

            def _found(info):

                self.after(0, lambda: [

                    self._update_btn.configure(state="normal"),

                    self._show_update_badge(info),

                    self._open_update_dialog(info),

                ])

            def _none():

                self.after(0, lambda: self._update_btn.configure(

                    text=f"v{__version__} ✓", state="normal", text_color="#66bb6a",

                ))

                self.after(3000, lambda: self._update_btn.configure(

                    text=f"v{__version__}", text_color="#555577"

                ))

            u.check_async(

                on_update_available=_found,

                on_up_to_date=_none,

                on_error=lambda _e: self.after(0, lambda: self._update_btn.configure(

                    text=f"v{__version__}", state="normal", text_color="#555577"

                )),

            )

        except Exception:

            self._update_btn.configure(text=f"v{__version__}", state="normal")

    def _open_update_dialog(self, info):

        from ui.update_dialog import UpdateDialog

        UpdateDialog(self, info, on_confirm=self._updater.apply_update)

    # ── lifecycle ─────────────────────────────────────────────────────────────

    def log(self, msg: str, level: str = "info"):

        """Public log used by main.py."""

        self._journey.log(msg, level)

    def show(self):

        self.deiconify()

        self.lift()

    def _on_close(self):

        self.withdraw()

