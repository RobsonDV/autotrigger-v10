"""
Janela de configurações — CTkToplevel modal.

Abas:
  Global     — TXT path + dispositivos padrão
  Sequências — lista CRUD de sequências
"""
from __future__ import annotations

import os
import customtkinter as ctk
import audio_manager as _audio
from typing import Callable, Optional


class SettingsWindow(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        config,
        on_saved: Callable,
        on_edit_sequence: Callable,  # (seq_dict, is_new: bool) -> None
    ):
        super().__init__(parent)
        self._config = config
        self._on_saved = on_saved
        self._on_edit = on_edit_sequence

        self.title("Configurações")
        self.geometry("640x520")
        self.minsize(580, 440)
        self.grab_set()
        self.focus_set()

        self._build()
        self._load_values()

    # ── build ─────────────────────────────────────────────────────────────────

    def _build(self):
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=0)
        self.columnconfigure(0, weight=1)

        tabs = ctk.CTkTabview(self, corner_radius=8)
        tabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        tabs.add("🌐  Global")
        tabs.add("🔗  Sequências")

        self._build_global_tab(tabs.tab("🌐  Global"))
        self._build_seq_tab(tabs.tab("🔗  Sequências"))

        # Bottom buttons
        btns = ctk.CTkFrame(self, fg_color="transparent")
        btns.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        ctk.CTkButton(btns, text="Fechar", width=100,
                      fg_color="#2a2a3a", hover_color="#3a3a4a",
                      command=self.destroy).pack(side="right", padx=4)
        ctk.CTkButton(btns, text="Salvar", width=100,
                      fg_color="#1565c0", hover_color="#0d47a1",
                      command=self._save).pack(side="right", padx=4)

    def _build_global_tab(self, parent):
        parent.columnconfigure(1, weight=1)

        row = 0

        # TXT file path
        ctk.CTkLabel(parent, text="Arquivo TXT:", anchor="w").grid(
            row=row, column=0, padx=12, pady=(14, 6), sticky="w"
        )
        txt_frame = ctk.CTkFrame(parent, fg_color="transparent")
        txt_frame.grid(row=row, column=1, sticky="ew", padx=(0, 12), pady=(14, 6))
        txt_frame.columnconfigure(0, weight=1)

        self._txt_var = ctk.StringVar()
        ctk.CTkEntry(txt_frame, textvariable=self._txt_var).grid(
            row=0, column=0, sticky="ew"
        )
        ctk.CTkButton(
            txt_frame, text="📁", width=32,
            command=self._browse_txt,
        ).grid(row=0, column=1, padx=(4, 0))
        row += 1

        # Separator
        ctk.CTkLabel(parent, text="Dispositivos padrão",
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="#445577").grid(
            row=row, column=0, columnspan=2, padx=12, pady=(16, 4), sticky="w"
        )
        row += 1

        # Input device
        ctk.CTkLabel(parent, text="Entrada (mic):", anchor="w").grid(
            row=row, column=0, padx=12, pady=6, sticky="w"
        )
        self._input_var = ctk.StringVar(value="Carregando...")
        self._input_combo = ctk.CTkComboBox(
            parent, variable=self._input_var, values=["Carregando..."],
            width=360, state="readonly",
        )
        self._input_combo.grid(row=row, column=1, padx=(0, 12), pady=6, sticky="ew")
        row += 1

        # Output device
        ctk.CTkLabel(parent, text="Saída (player):", anchor="w").grid(
            row=row, column=0, padx=12, pady=6, sticky="w"
        )
        self._output_var = ctk.StringVar(value="Carregando...")
        self._output_combo = ctk.CTkComboBox(
            parent, variable=self._output_var, values=["Carregando..."],
            width=360, state="readonly",
        )
        self._output_combo.grid(row=row, column=1, padx=(0, 12), pady=6, sticky="ew")
        row += 1

        # Load devices after window is shown
        self.after(200, self._load_devices)

    def _build_seq_tab(self, parent):
        parent.rowconfigure(0, weight=1)
        parent.columnconfigure(0, weight=1)

        # Sequence list
        list_frame = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        list_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        list_frame.columnconfigure(0, weight=1)
        self._seq_list_frame = list_frame

        # Toolbar
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.grid(row=1, column=0, sticky="ew", padx=4, pady=(0, 4))
        ctk.CTkButton(bar, text="＋  Nova", width=90,
                      fg_color="#1b5e20", hover_color="#0a3d12",
                      command=self._new_seq).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="✎  Editar", width=90,
                      command=self._edit_selected).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="⎘  Duplicar", width=90,
                      command=self._dup_selected).pack(side="left", padx=4)
        ctk.CTkButton(bar, text="✕  Excluir", width=90,
                      fg_color="#7f0000", hover_color="#560000",
                      command=self._del_selected).pack(side="left", padx=4)

        self._selected_seq_id: Optional[str] = None
        self._seq_rows: list = []

    # ── load ──────────────────────────────────────────────────────────────────

    def _load_values(self):
        g = self._config.get_global()
        self._txt_var.set(g.get("txt_file_path", ""))
        self._refresh_seq_list()

    def _load_devices(self):
        try:
            inputs = _audio.list_input_devices()
            outputs = _audio.list_output_devices()
        except Exception:
            inputs, outputs = [], []

        self._input_devices = inputs
        self._output_devices = outputs

        in_names = [f"{d['name']}" for d in inputs] or ["(nenhum)"]
        out_names = [f"{d['name']}" for d in outputs] or ["(nenhum)"]

        self._input_combo.configure(values=in_names)
        self._output_combo.configure(values=out_names)

        g = self._config.get_global()
        cur_in = g.get("default_input_device_id", "")
        cur_out = g.get("default_output_device_id", "")

        for d in inputs:
            if d["id"] == cur_in:
                self._input_var.set(d["name"])
                break
        else:
            self._input_var.set(in_names[0])

        for d in outputs:
            if d["id"] == cur_out:
                self._output_var.set(d["name"])
                break
        else:
            self._output_var.set(out_names[0])

    def _refresh_seq_list(self):
        for w in self._seq_list_frame.winfo_children():
            w.destroy()
        self._seq_rows.clear()
        self._selected_seq_id = None

        seqs = self._config.get_sequences()
        if not seqs:
            ctk.CTkLabel(
                self._seq_list_frame,
                text="Nenhuma sequência. Clique em '+ Nova' para criar.",
                text_color="#445566",
            ).pack(pady=20)
            return

        for seq in seqs:
            row = self._make_seq_row(seq)
            self._seq_rows.append((seq["id"], row))

    def _make_seq_row(self, seq: dict) -> ctk.CTkFrame:
        f = ctk.CTkFrame(
            self._seq_list_frame, corner_radius=6,
            fg_color="transparent",
        )
        f.pack(fill="x", padx=4, pady=3)
        f.columnconfigure(1, weight=1)

        dot = ctk.CTkLabel(f, text="○", text_color="#445566",
                           font=ctk.CTkFont(size=14), width=20)
        dot.grid(row=0, column=0, padx=(8, 4), pady=6, sticky="ns")

        info = ctk.CTkFrame(f, fg_color="transparent")
        info.grid(row=0, column=1, sticky="ew")
        enabled = "✓" if seq.get("enabled", True) else "✗"
        kw = seq.get("keyword_trigger", "—")
        n_steps = len(seq.get("steps", []))
        ctk.CTkLabel(info,
                     text=f"{seq.get('name', '')}",
                     font=ctk.CTkFont(size=13, weight="bold"),
                     anchor="w").pack(anchor="w")
        ctk.CTkLabel(info,
                     text=f"Keyword: {kw}  ·  {n_steps} etapa(s)  ·  {enabled}",
                     text_color="#666688",
                     font=ctk.CTkFont(size=11),
                     anchor="w").pack(anchor="w")

        sid = seq["id"]
        for w in (f, dot, info):
            w.bind("<Button-1>", lambda _e, _id=sid: self._select_seq(_id, f))

        ctk.CTkButton(f, text="✎", width=28, height=28,
                      command=lambda _id=sid: self._edit_seq(_id)).grid(
            row=0, column=2, padx=4, pady=6
        )
        return f

    def _select_seq(self, seq_id: str, frame: ctk.CTkFrame):
        # Deselect previous
        for _, row in self._seq_rows:
            row.configure(fg_color="transparent")
        frame.configure(fg_color="#142a4a")
        self._selected_seq_id = seq_id

    # ── actions ───────────────────────────────────────────────────────────────

    def _browse_txt(self):
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            title="Selecionar arquivo TXT",
            filetypes=[("Arquivos TXT", "*.txt"), ("Todos", "*.*")],
        )
        if path:
            self._txt_var.set(path)

    def _save(self):
        g = self._config.get_global()
        g["txt_file_path"] = self._txt_var.get()

        # Resolve device id from selected name
        in_name = self._input_var.get()
        for d in getattr(self, "_input_devices", []):
            if d["name"] == in_name:
                g["default_input_device_id"] = d["id"]
                g["default_input_device_name"] = d["name"]
                break

        out_name = self._output_var.get()
        for d in getattr(self, "_output_devices", []):
            if d["name"] == out_name:
                g["default_output_device_id"] = d["id"]
                g["default_output_device_name"] = d["name"]
                break

        self._config.update_global(g)
        self._config.save()
        self._on_saved()
        self.destroy()

    def _new_seq(self):
        seq = self._config.new_sequence_template()
        self._on_edit(seq, True)
        self.destroy()

    def _edit_selected(self):
        if self._selected_seq_id:
            self._edit_seq(self._selected_seq_id)

    def _edit_seq(self, seq_id: str):
        seq = self._config.get_sequence_by_id(seq_id)
        if seq:
            self._on_edit(seq, False)
            self.destroy()

    def _dup_selected(self):
        if not self._selected_seq_id:
            return
        import copy
        import uuid
        orig = self._config.get_sequence_by_id(self._selected_seq_id)
        if orig:
            dup = copy.deepcopy(orig)
            dup["id"] = str(uuid.uuid4())[:8]
            dup["name"] = orig["name"] + " (cópia)"
            self._config.add_sequence(dup)
            self._config.save()
            self._refresh_seq_list()

    def _del_selected(self):
        if not self._selected_seq_id:
            return
        self._config.delete_sequence(self._selected_seq_id)
        self._config.save()
        self._refresh_seq_list()
        self._on_saved()
