"""
Gerenciamento de configuração persistente em JSON — Schema v2.

Schema v2:
{
  "version": 2,
  "global": { "txt_file_path", "default_input_device_id", "default_input_device_name",
              "default_output_device_id", "default_output_device_name" },
  "sequences": [ { "id", "name", "keyword_trigger", "enabled", "steps": [...] } ]
}

Migração automática de v1 (keys planas) → v2 na primeira carga.
"""
import json
import os
import uuid

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_GLOBAL = {
    "txt_file_path": "",
    "default_input_device_id": "",
    "default_input_device_name": "",
    "default_output_device_id": "",
    "default_output_device_name": "",
}


def _new_id() -> str:
    return str(uuid.uuid4())[:8]


def _migrate_v1(old: dict) -> dict:
    """Converte config v1 (keys planas) → schema v2."""
    g = {
        "txt_file_path": old.get("txt_file_path", ""),
        "default_input_device_id": old.get("input_device_id", ""),
        "default_input_device_name": old.get("input_device_name", ""),
        "default_output_device_id": old.get("output_device_id", ""),
        "default_output_device_name": old.get("output_device_name", ""),
    }

    steps = []
    in_id = g["default_input_device_id"]
    in_name = g["default_input_device_name"]

    if in_id:
        steps.append({"type": "mute", "device_id": in_id,
                      "device_name": in_name, "label": "Mute Entrada"})
    if old.get("hotkey_stop"):
        steps.append({"type": "hotkey", "hotkey": old["hotkey_stop"], "label": "STOP"})
    if old.get("audio_file_1"):
        steps.append({"type": "play_audio", "file": old["audio_file_1"], "label": "Vinheta Entrada"})
    if old.get("stream_url"):
        steps.append({"type": "stream", "url": old["stream_url"],
                      "duration_seconds": old.get("stream_duration", 300), "label": "Streaming"})
    if old.get("audio_file_2"):
        steps.append({"type": "play_audio", "file": old["audio_file_2"], "label": "Vinheta Saída"})
    if old.get("hotkey_play"):
        steps.append({"type": "hotkey", "hotkey": old["hotkey_play"], "label": "PLAY"})
    if old.get("keyword_unmute"):
        steps.append({"type": "wait_keyword", "keyword": old["keyword_unmute"],
                      "label": f"Aguardar {old['keyword_unmute']}"})
    if old.get("hotkey_stop"):
        steps.append({"type": "hotkey", "hotkey": old["hotkey_stop"], "label": "STOP Retorno"})
    if in_id:
        steps.append({"type": "unmute", "device_id": in_id,
                      "device_name": in_name, "label": "Unmute Entrada"})

    return {
        "version": 2,
        "global": g,
        "sequences": [{
            "id": _new_id(),
            "name": "Jornada Esportiva",
            "keyword_trigger": old.get("keyword_start", "ESPORTE"),
            "enabled": True,
            "steps": steps,
        }],
    }


class Config:
    def __init__(self):
        self._data: dict = {
            "version": 2,
            "global": dict(DEFAULT_GLOBAL),
            "sequences": [],
        }
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                if loaded.get("version", 1) < 2:
                    loaded = _migrate_v1(loaded)
                    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                        json.dump(loaded, f, indent=2, ensure_ascii=False)
                    print("[Config] Migrado de v1 → v2.")
                self._data = loaded
            except Exception as exc:
                print(f"[Config] Erro ao carregar config.json: {exc}. Usando padrões.")

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            raise RuntimeError(f"Erro ao salvar configuração: {exc}") from exc

    # ── global ───────────────────────────────────────────────────────────────

    def get_global(self) -> dict:
        return self._data.get("global", {})

    def update_global(self, d: dict):
        self._data.setdefault("global", {}).update(d)

    # ── compat v1 API ────────────────────────────────────────────────────────

    def get(self, key: str, default=None):
        return self._data.get("global", {}).get(key, default)

    def set(self, key: str, value):
        self._data.setdefault("global", {})[key] = value

    def update(self, d: dict):
        self._data.setdefault("global", {}).update(d)

    # ── sequences ────────────────────────────────────────────────────────────

    def get_sequences(self) -> list:
        return self._data.get("sequences", [])

    def get_sequence_by_id(self, seq_id: str) -> dict | None:
        for s in self.get_sequences():
            if s["id"] == seq_id:
                return s
        return None

    def add_sequence(self, seq: dict) -> dict:
        if "id" not in seq:
            seq["id"] = _new_id()
        self._data.setdefault("sequences", []).append(seq)
        return seq

    def update_sequence(self, seq: dict):
        seqs = self._data.setdefault("sequences", [])
        for i, s in enumerate(seqs):
            if s["id"] == seq["id"]:
                seqs[i] = seq
                return
        seqs.append(seq)

    def delete_sequence(self, seq_id: str):
        self._data["sequences"] = [
            s for s in self._data.get("sequences", []) if s["id"] != seq_id
        ]

    def new_sequence_template(self) -> dict:
        return {
            "id": _new_id(),
            "name": "Nova Sequência",
            "keyword_trigger": "",
            "enabled": True,
            "steps": [],
        }
