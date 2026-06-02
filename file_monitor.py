"""
Monitora um arquivo TXT em tempo real usando watchdog.
Detecta palavras-chave no conteúdo e dispara callbacks correspondentes.
"""
import os
import threading

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler


class _TxtHandler(FileSystemEventHandler):
    def __init__(
        self,
        filepath: str,
        keyword_start: str,
        keyword_unmute: str,
        on_start,
        on_unmute,
        log_callback,
    ):
        super().__init__()
        self._filepath = os.path.abspath(filepath)
        self._keyword_start = keyword_start.strip().upper()
        self._keyword_unmute = keyword_unmute.strip().upper()
        self._on_start = on_start
        self._on_unmute = on_unmute
        self._log = log_callback or (lambda msg: print(f"[Monitor] {msg}"))
        self._last_content = ""
        self._lock = threading.Lock()

    def on_modified(self, event):
        if event.is_directory:
            return
        if os.path.abspath(event.src_path) != self._filepath:
            return
        self._check_file()

    # Alguns sistemas disparam on_created em vez de on_modified ao reescrever
    def on_created(self, event):
        self.on_modified(event)

    def _check_file(self):
        with self._lock:
            try:
                with open(self._filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip().upper()
            except Exception as exc:
                self._log(f"Erro ao ler TXT: {exc}")
                return

            if content == self._last_content:
                return
            self._last_content = content

            self._log(f"TXT atualizado: '{content}'")

            # Checa unmute PRIMEIRO (evita que keyword_start seja substring de keyword_unmute)
            if self._keyword_unmute and self._keyword_unmute in content:
                self._log(f"🔊 Keyword de DESMUTE detectada: '{self._keyword_unmute}'")
                if self._on_unmute:
                    threading.Thread(target=self._on_unmute, daemon=True, name="seq-unmute").start()
            elif self._keyword_start and self._keyword_start in content:
                self._log(f"▶ Keyword de INÍCIO detectada: '{self._keyword_start}'")
                if self._on_start:
                    threading.Thread(target=self._on_start, daemon=True, name="seq-start").start()


class FileMonitor:
    def __init__(self):
        self._observer: Observer | None = None

    def start(
        self,
        filepath: str,
        keyword_start: str,
        keyword_unmute: str,
        on_start,
        on_unmute,
        log_callback=None,
    ) -> bool:
        """
        Inicia o monitoramento do arquivo TXT.
        Retorna True se iniciou corretamente.
        """
        self.stop()

        if not filepath:
            print("[Monitor] Caminho do TXT não configurado.")
            return False

        if not os.path.isfile(filepath):
            print(f"[Monitor] Arquivo não encontrado: '{filepath}'")
            return False

        folder = os.path.dirname(os.path.abspath(filepath))
        handler = _TxtHandler(
            filepath, keyword_start, keyword_unmute,
            on_start, on_unmute, log_callback,
        )

        self._observer = Observer()
        self._observer.schedule(handler, folder, recursive=False)
        self._observer.start()
        return True

    def stop(self):
        """Para o monitoramento."""
        if self._observer and self._observer.is_alive():
            self._observer.stop()
            self._observer.join(timeout=3)
        self._observer = None

    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()
