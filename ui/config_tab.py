"""
Aba de Configuração — formulário completo com todos os parâmetros do app.
"""
import os
import threading

import customtkinter as ctk
from tkinter import filedialog, messagebox


class ConfigTab(ctk.CTkScrollableFrame):
    def __init__(self, parent, config, audio_manager, on_save=None, on_test=None, **kwargs):
        super().__init__(parent, **kwargs)
        self._config = config
        self._audio_mgr = audio_manager
        self._on_save = on_save
        self._on_test = on_test

        self._input_devices: list = []   # [{'id': ..., 'name': ...}]
        self._output_devices: list = []
        self._vars: dict = {}            # StringVar / IntVar por campo

        self._build_ui()
        self._load_from_config()

        # Carregar dispositivos em background ao abrir
        threading.Thread(target=self._refresh_devices, daemon=True, name="dev-refresh").start()

    # ── layout ──────────────────────────────────────────────────────────────

    def _build_ui(self):
        self.columnconfigure(1, weight=1)
        row = 0

        # ──── Monitoramento ────────────────────────────────────────────────
        row = self._section("Monitoramento do TXT", row)

        row = self._row_file(
            row, "Arquivo TXT:", "txt_file_path",
            [("Arquivos de texto", "*.txt"), ("Todos os arquivos", "*.*")],
        )
        row = self._row_entry(row, "Keyword Início:", "keyword_start",
                              placeholder="ex: ESPORTE")
        row = self._row_entry(row, "Keyword Desmute:", "keyword_unmute",
                              placeholder="ex: FIM_ESPORTE")

        # ──── Dispositivos de Áudio ────────────────────────────────────────
        row = self._section("Dispositivos de Áudio", row)

        # Entrada (mutar)
        ctk.CTkLabel(self, text="Entrada (mutar):", anchor="w").grid(
            row=row, column=0, sticky="w", padx=14, pady=(4, 2))
        self._vars["input_device_name"] = ctk.StringVar(value="Aguardando...")
        self._input_menu = ctk.CTkOptionMenu(
            self,
            variable=self._vars["input_device_name"],
            values=["Aguardando..."],
            width=310,
            command=self._on_select_input,
        )
        self._input_menu.grid(row=row, column=1, sticky="ew", padx=(4, 4), pady=(4, 2))
        ctk.CTkButton(
            self, text="↺", width=34, font=ctk.CTkFont(size=14),
            command=lambda: threading.Thread(target=self._refresh_devices, daemon=True).start(),
        ).grid(row=row, column=2, padx=(0, 8))
        row += 1

        # Saída
        ctk.CTkLabel(self, text="Saída (áudio):", anchor="w").grid(
            row=row, column=0, sticky="w", padx=14, pady=(4, 2))
        self._vars["output_device_name"] = ctk.StringVar(value="Aguardando...")
        self._output_menu = ctk.CTkOptionMenu(
            self,
            variable=self._vars["output_device_name"],
            values=["Aguardando..."],
            width=310,
            command=self._on_select_output,
        )
        self._output_menu.grid(row=row, column=1, sticky="ew", padx=(4, 4), pady=(4, 2))
        row += 1

        # ──── Arquivos de Áudio e Streaming ───────────────────────────────
        row = self._section("Áudio — Vinhetas e Streaming", row)

        row = self._row_file(
            row, "Vinheta 1 (entrada):", "audio_file_1",
            [("Áudio", "*.mp3 *.wav *.ogg *.flac *.aac"), ("Todos", "*.*")],
        )

        row = self._row_entry(row, "URL do Streaming:", "stream_url",
                              placeholder="http://stream.radio.com/live")

        # Duração do streaming
        ctk.CTkLabel(self, text="Duração (segundos):", anchor="w").grid(
            row=row, column=0, sticky="w", padx=14, pady=(4, 2))
        dur_frame = ctk.CTkFrame(self, fg_color="transparent")
        dur_frame.grid(row=row, column=1, sticky="w", padx=(4, 4), pady=(4, 2))
        self._vars["stream_duration"] = ctk.StringVar()
        ctk.CTkEntry(dur_frame, textvariable=self._vars["stream_duration"], width=100).pack(side="left")
        ctk.CTkLabel(dur_frame, text=" = ", width=20).pack(side="left")
        self._dur_label = ctk.CTkLabel(dur_frame, text="5min 0s", text_color="#888888")
        self._dur_label.pack(side="left")
        self._vars["stream_duration"].trace_add("write", self._update_dur_label)
        row += 1

        row = self._row_file(
            row, "Vinheta 2 (saída):", "audio_file_2",
            [("Áudio", "*.mp3 *.wav *.ogg *.flac *.aac"), ("Todos", "*.*")],
        )

        # ──── Hotkeys ─────────────────────────────────────────────────
        row = self._section("Comandos de Atalho (Hotkeys)", row)

        # STOP
        ctk.CTkLabel(self, text="Hotkey STOP:", anchor="w").grid(
            row=row, column=0, sticky="w", padx=14, pady=(4, 2))
        stop_frame = ctk.CTkFrame(self, fg_color="transparent")
        stop_frame.grid(row=row, column=1, sticky="w", padx=(4, 4), pady=(4, 2))
        self._vars["hotkey_stop"] = ctk.StringVar()
        self._stop_entry = ctk.CTkEntry(
            stop_frame, textvariable=self._vars["hotkey_stop"], width=160,
            placeholder_text="ex: ctrl+f1",
        )
        self._stop_entry.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(stop_frame, text="← Para a programação", text_color="#888888",
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 8))
        self._stop_capture_btn = ctk.CTkButton(
            stop_frame, text="⌨ Capturar", width=110,
            fg_color="#7f0000", hover_color="#560000",
            command=lambda: self._start_capture_hotkey("hotkey_stop", self._stop_entry,
                                                        self._stop_capture_btn),
        )
        self._stop_capture_btn.pack(side="left")
        row += 1

        # PLAY
        ctk.CTkLabel(self, text="Hotkey PLAY:", anchor="w").grid(
            row=row, column=0, sticky="w", padx=14, pady=(4, 2))
        play_frame = ctk.CTkFrame(self, fg_color="transparent")
        play_frame.grid(row=row, column=1, sticky="w", padx=(4, 4), pady=(4, 2))
        self._vars["hotkey_play"] = ctk.StringVar()
        self._play_entry = ctk.CTkEntry(
            play_frame, textvariable=self._vars["hotkey_play"], width=160,
            placeholder_text="ex: ctrl+f2",
        )
        self._play_entry.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(play_frame, text="← Retoma a programação", text_color="#888888",
                     font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 8))
        self._play_capture_btn = ctk.CTkButton(
            play_frame, text="⌨ Capturar", width=110,
            fg_color="#1b5e20", hover_color="#0a3d12",
            command=lambda: self._start_capture_hotkey("hotkey_play", self._play_entry,
                                                        self._play_capture_btn),
        )
        self._play_capture_btn.pack(side="left")
        row += 1

        # ──── Botões de ação ──────────────────────────────────────────────
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=row, column=0, columnspan=3, sticky="ew", padx=12, pady=16)

        ctk.CTkButton(
            btn_frame, text="💾  Salvar Configuração", width=200,
            command=self._save,
        ).pack(side="left", padx=(0, 12))

        if self._on_test:
            ctk.CTkButton(
                btn_frame, text="▶  Testar Fluxo", width=160,
                fg_color="#1b5e20", hover_color="#0a3d12",
                command=self._on_test,
            ).pack(side="left")

    # ── helpers de layout ────────────────────────────────────────────────────

    def _section(self, title: str, row: int) -> int:
        sep = ctk.CTkFrame(self, height=2, fg_color=("#333355", "#222244"))
        sep.grid(row=row, column=0, columnspan=3, sticky="ew", padx=8, pady=(14, 2))
        row += 1
        ctk.CTkLabel(
            self, text=title,
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
        ).grid(row=row, column=0, columnspan=3, sticky="w", padx=12, pady=(2, 4))
        return row + 1

    def _row_entry(self, row: int, label: str, key: str, placeholder: str = "") -> int:
        ctk.CTkLabel(self, text=label, anchor="w").grid(
            row=row, column=0, sticky="w", padx=14, pady=(4, 2))
        self._vars[key] = ctk.StringVar()
        ctk.CTkEntry(
            self, textvariable=self._vars[key],
            placeholder_text=placeholder,
        ).grid(row=row, column=1, sticky="ew", padx=(4, 4), pady=(4, 2))
        return row + 1

    def _row_file(self, row: int, label: str, key: str, filetypes: list) -> int:
        ctk.CTkLabel(self, text=label, anchor="w").grid(
            row=row, column=0, sticky="w", padx=14, pady=(4, 2))
        self._vars[key] = ctk.StringVar()
        ctk.CTkEntry(self, textvariable=self._vars[key]).grid(
            row=row, column=1, sticky="ew", padx=(4, 4), pady=(4, 2))
        ctk.CTkButton(
            self, text="📂", width=34,
            command=lambda k=key, ft=filetypes: self._pick_file(k, ft),
        ).grid(row=row, column=2, padx=(0, 8))
        return row + 1

    # ── lógica ──────────────────────────────────────────────────────────────

    def _pick_file(self, var_key: str, filetypes: list):
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            self._vars[var_key].set(path)

    def _refresh_devices(self):
        """Carrega listas de dispositivos em thread separada e atualiza UI."""
        try:
            inputs = self._audio_mgr.list_input_devices()
            outputs = self._audio_mgr.list_output_devices()
        except Exception as exc:
            print(f"[ConfigTab] Erro ao listar dispositivos: {exc}")
            inputs, outputs = [], []

        self._input_devices = inputs
        self._output_devices = outputs

        input_names = [d["name"] for d in inputs] or ["Nenhum dispositivo encontrado"]
        output_names = [d["name"] for d in outputs] or ["Nenhum dispositivo encontrado"]

        def _update():
            self._input_menu.configure(values=input_names)
            self._output_menu.configure(values=output_names)

            saved_in = self._config.get("input_device_name", "")
            saved_out = self._config.get("output_device_name", "")

            if saved_in in input_names:
                self._vars["input_device_name"].set(saved_in)
            elif input_names:
                self._vars["input_device_name"].set(input_names[0])

            if saved_out in output_names:
                self._vars["output_device_name"].set(saved_out)
            elif output_names:
                self._vars["output_device_name"].set(output_names[0])

        self.after(0, _update)

    def _on_select_input(self, name: str):
        for d in self._input_devices:
            if d["name"] == name:
                self._config.set("input_device_id", d["id"])
                self._config.set("input_device_name", name)
                return

    def _on_select_output(self, name: str):
        for d in self._output_devices:
            if d["name"] == name:
                self._config.set("output_device_id", d["id"])
                self._config.set("output_device_name", name)
                return

    def _update_dur_label(self, *_):
        try:
            secs = int(self._vars["stream_duration"].get())
            m, s = divmod(secs, 60)
            self._dur_label.configure(text=f"{m}min {s}s")
        except ValueError:
            self._dur_label.configure(text="—")

    def _start_capture_hotkey(self, var_key: str, entry_widget, btn_widget):
        """Inicia captura da hotkey em thread separada para o campo indicado."""
        btn_widget.configure(text="Pressione...", state="disabled")
        entry_widget.configure(state="disabled")

        def _listen():
            from hotkey_sender import capture_hotkey
            hk = capture_hotkey()

            def _done():
                if hk:
                    self._vars[var_key].set(hk)
                btn_widget.configure(text="⌨ Capturar", state="normal")
                entry_widget.configure(state="normal")

            self.after(0, _done)

        threading.Thread(target=_listen, daemon=True, name="hotkey-capture").start()

    def _load_from_config(self):
        """Preenche campos com valores do config (exceto dropdowns de device)."""
        skip_keys = {"input_device_name", "output_device_name",
                     "input_device_id", "output_device_id"}
        for key, var in self._vars.items():
            if key in skip_keys:
                continue
            val = self._config.get(key, "")
            var.set(str(val) if val is not None else "")

    def _save(self):
        """Coleta campos e persiste no config.json."""
        skip_keys = {"input_device_name", "output_device_name",
                     "input_device_id", "output_device_id"}
        for key, var in self._vars.items():
            if key in skip_keys:
                continue
            val = var.get()
            if key == "stream_duration":
                try:
                    val = int(val)
                except ValueError:
                    val = 300
            self._config.set(key, val)

        # Sincroniza nomes E IDs de dispositivo a partir da seleção atual
        selected_in_name = self._vars["input_device_name"].get()
        selected_out_name = self._vars["output_device_name"].get()

        self._config.set("input_device_name", selected_in_name)
        self._config.set("output_device_name", selected_out_name)

        # Busca o ID pelo nome para salvar
        input_id = ""
        for d in self._input_devices:
            if d["name"] == selected_in_name:
                input_id = d["id"]
                break
        self._config.set("input_device_id", input_id)

        output_id = ""
        for d in self._output_devices:
            if d["name"] == selected_out_name:
                output_id = d["id"]
                break
        self._config.set("output_device_id", output_id)

        try:
            self._config.save()
            if self._on_save:
                self._on_save("Configuração salva com sucesso!")
        except Exception as exc:
            messagebox.showerror("Erro ao Salvar", str(exc))
            if self._on_save:
                self._on_save(f"Erro ao salvar: {exc}", error=True)
