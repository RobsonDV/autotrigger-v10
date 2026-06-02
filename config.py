"""
Gerenciamento de configuração persistente em JSON.
"""
import json
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "txt_file_path": "",
    "keyword_start": "ESPORTE",
    "keyword_unmute": "FIM_ESPORTE",
    "input_device_id": "",
    "input_device_name": "",
    "output_device_id": "",
    "output_device_name": "",
    "audio_file_1": "",
    "audio_file_2": "",
    "stream_url": "",
    "stream_duration": 300,
    "hotkey_stop": "",
    "hotkey_play": "",
}


class Config:
    def __init__(self):
        self.data: dict = dict(DEFAULT_CONFIG)
        self.load()

    def load(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self.data.update(loaded)
            except Exception as exc:
                print(f"[Config] Erro ao carregar config.json: {exc}. Usando padrões.")

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            raise RuntimeError(f"Erro ao salvar configuração: {exc}") from exc

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def set(self, key: str, value):
        self.data[key] = value

    def update(self, d: dict):
        self.data.update(d)
