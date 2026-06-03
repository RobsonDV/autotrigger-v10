"""
Painel de Configurações Globais — inline (sem janela pop-up).

TXT monitorado + dispositivos padrão. Salva no Config e dispara on_saved().
"""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QComboBox, QPushButton, QFileDialog,
)

import audio_manager as _audio
from ui.theme import COLORS
from ui.widgets import hline

# Cache de dispositivos no nível do módulo (evita re-enumerar a cada abertura)
_DEV_CACHE = {"inputs": None, "outputs": None}


class GlobalSettings(QWidget):
    def __init__(self, config, on_saved: Callable):
        super().__init__()
        self._config = config
        self._on_saved = on_saved
        self._inputs: list = []
        self._outputs: list = []
        self._build()
        self._load()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        root.setSpacing(12)

        title = QLabel("⚙  Configurações Globais")
        title.setObjectName("h2")
        root.addWidget(title)
        root.addWidget(hline())

        form = QFormLayout()
        form.setHorizontalSpacing(14)
        form.setVerticalSpacing(12)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # TXT
        txt_host = QWidget(); txt_l = QHBoxLayout(txt_host)
        txt_l.setContentsMargins(0, 0, 0, 0)
        self._txt = QLineEdit()
        browse = QPushButton("📁"); browse.setObjectName("icon")
        browse.clicked.connect(self._browse_txt)
        txt_l.addWidget(self._txt, 1); txt_l.addWidget(browse)
        form.addRow(_lbl("Arquivo TXT"), txt_host)

        sec = QLabel("DISPOSITIVOS PADRÃO")
        sec.setObjectName("section")
        root.addLayout(form)
        root.addSpacing(6)
        root.addWidget(sec)

        form2 = QFormLayout()
        form2.setHorizontalSpacing(14)
        form2.setVerticalSpacing(12)
        self._in_combo = QComboBox()
        self._out_combo = QComboBox()
        refresh = QPushButton("↻  Recarregar dispositivos")
        refresh.setObjectName("ghost")
        refresh.clicked.connect(lambda: self._load_devices(force=True))
        form2.addRow(_lbl("Entrada (mic)"), self._in_combo)
        form2.addRow(_lbl("Saída (player)"), self._out_combo)
        root.addLayout(form2)
        root.addWidget(refresh, alignment=Qt.AlignLeft)

        root.addStretch(1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        save = QPushButton("Salvar configurações")
        save.setObjectName("primary")
        save.clicked.connect(self._save)
        btns.addWidget(save)
        root.addLayout(btns)

    def _load(self):
        g = self._config.get_global()
        self._txt.setText(g.get("txt_file_path", ""))
        self._load_devices()

    def _load_devices(self, force: bool = False):
        if force or _DEV_CACHE["inputs"] is None:
            try:
                _DEV_CACHE["inputs"] = _audio.list_input_devices()
                _DEV_CACHE["outputs"] = _audio.list_output_devices()
            except Exception:
                _DEV_CACHE["inputs"] = _DEV_CACHE["outputs"] = []
        self._inputs = _DEV_CACHE["inputs"] or []
        self._outputs = _DEV_CACHE["outputs"] or []

        g = self._config.get_global()
        self._fill_combo(self._in_combo, self._inputs, g.get("default_input_device_id", ""))
        self._fill_combo(self._out_combo, self._outputs, g.get("default_output_device_id", ""))

    @staticmethod
    def _fill_combo(combo: QComboBox, devices: list, cur_id: str):
        combo.clear()
        names = [d["name"] for d in devices] or ["(nenhum)"]
        combo.addItems(names)
        for i, d in enumerate(devices):
            if d["id"] == cur_id:
                combo.setCurrentIndex(i)
                break

    def _browse_txt(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Selecionar arquivo TXT", "",
            "Arquivos TXT (*.txt);;Todos (*.*)",
        )
        if path:
            self._txt.setText(path)

    def _save(self):
        g = self._config.get_global()
        g["txt_file_path"] = self._txt.text().strip()
        for d in self._inputs:
            if d["name"] == self._in_combo.currentText():
                g["default_input_device_id"] = d["id"]
                g["default_input_device_name"] = d["name"]
                break
        for d in self._outputs:
            if d["name"] == self._out_combo.currentText():
                g["default_output_device_id"] = d["id"]
                g["default_output_device_name"] = d["name"]
                break
        self._config.update_global(g)
        self._config.save()
        self._on_saved()


def _lbl(text: str) -> QLabel:
    lab = QLabel(text)
    lab.setObjectName("muted")
    lab.setFixedWidth(120)
    return lab
