"""
Dialog de notificação de atualização disponível.
"""
import threading
import customtkinter as ctk


class UpdateDialog(ctk.CTkToplevel):
    def __init__(self, parent, update_info, on_confirm, **kwargs):
        super().__init__(parent, **kwargs)

        self._info = update_info
        self._on_confirm = on_confirm
        self._downloading = False

        # Janela modal
        self.title("Atualização Disponível")
        self.geometry("480x360")
        self.resizable(False, False)
        self.grab_set()
        self.lift()
        self.focus()

        # Centralizar sobre o parent
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() // 2) - 240
        py = parent.winfo_y() + (parent.winfo_height() // 2) - 180
        self.geometry(f"+{px}+{py}")

        self._build()

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        # Cabeçalho
        ctk.CTkLabel(
            self,
            text="🚀  Nova versão disponível!",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#4fc3f7",
        ).grid(row=0, column=0, padx=20, pady=(20, 4), sticky="w")

        ctk.CTkLabel(
            self,
            text=f"v{self._info.version} está pronta para instalar.",
            font=ctk.CTkFont(size=13),
            text_color="#aaaaaa",
        ).grid(row=1, column=0, padx=20, pady=(0, 8), sticky="w")

        # Notas de versão
        notes_frame = ctk.CTkFrame(self, fg_color=("#111128", "#0a0a1a"), corner_radius=8)
        notes_frame.grid(row=2, column=0, padx=20, pady=4, sticky="nsew")

        notes_text = ctk.CTkTextbox(
            notes_frame,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="transparent",
            state="normal",
        )
        notes_text.pack(fill="both", expand=True, padx=8, pady=8)
        notes_text.insert("end", self._info.notes or "Sem notas de versão.")
        notes_text.configure(state="disabled")

        # Barra de progresso (oculta até clicar em Atualizar)
        self._progress_label = ctk.CTkLabel(
            self, text="", font=ctk.CTkFont(size=11), text_color="#888888"
        )
        self._progress_label.grid(row=3, column=0, padx=20, pady=(8, 0), sticky="w")

        self._progress = ctk.CTkProgressBar(self, height=10)
        self._progress.set(0)
        self._progress.grid(row=4, column=0, padx=20, pady=(2, 8), sticky="ew")
        self._progress.grid_remove()  # oculta por enquanto

        # Botões
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=5, column=0, padx=20, pady=(4, 16), sticky="e")

        ctk.CTkButton(
            btn_frame, text="Agora não", width=120,
            fg_color="#333344", hover_color="#444455",
            command=self.destroy,
        ).pack(side="left", padx=(0, 8))

        self._update_btn = ctk.CTkButton(
            btn_frame, text="⬇  Baixar e Instalar", width=180,
            fg_color="#1565c0", hover_color="#0d47a1",
            command=self._start_update,
        )
        self._update_btn.pack(side="left")

    def _start_update(self):
        if self._downloading:
            return
        self._downloading = True
        self._update_btn.configure(state="disabled", text="Baixando...")
        self._progress.grid()

        def _progress_cb(pct: int):
            self.after(0, lambda: self._progress.set(pct / 100))
            self.after(0, lambda: self._progress_label.configure(
                text=f"Baixando... {pct}%"
            ))

        threading.Thread(
            target=self._on_confirm,
            args=(self._info, _progress_cb),
            daemon=True,
            name="updater-apply",
        ).start()
