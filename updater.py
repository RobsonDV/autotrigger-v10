"""
Auto-updater via GitHub Releases.

Fluxo:
  1. Consulta https://api.github.com/repos/{owner}/{repo}/releases/latest
  2. Compara tag_name com __version__ atual
  3. Se mais recente: baixa o asset .exe para pasta temporária
  4. Escreve update.bat que espera o processo atual fechar,
     substitui o .exe e reinicia o app
  5. Executa update.bat e encerra o processo atual

Uso:
    from updater import Updater
    u = Updater(log_callback=window.log)
    u.check_async(on_update_available=callback)
"""

import os
import sys
import threading
import subprocess
import tempfile
from typing import Callable, Optional

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from version import __version__, GITHUB_REPO, GITHUB_ASSET_NAME

_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
_HEADERS = {
    "User-Agent": f"MaisNovaSportTrigger/{__version__}",
    "Accept": "application/vnd.github.v3+json",
}


def _parse_version(tag: str) -> tuple:
    """Converte 'v1.2.3' ou '1.2.3' em (1, 2, 3) para comparação."""
    tag = tag.lstrip("v").strip()
    try:
        return tuple(int(x) for x in tag.split("."))
    except ValueError:
        return (0, 0, 0)


class UpdateInfo:
    def __init__(self, tag: str, notes: str, download_url: str, size: int):
        self.tag = tag
        self.version = tag.lstrip("v")
        self.notes = notes
        self.download_url = download_url
        self.size = size

    def __repr__(self):
        return f"<UpdateInfo v{self.version}>"


class Updater:
    def __init__(self, log_callback: Optional[Callable] = None):
        self._log = log_callback or (lambda msg, level="info": print(f"[Updater][{level}] {msg}"))
        self._checking = False

    # ── public API ──────────────────────────────────────────────────────────

    def check_async(
        self,
        on_update_available: Callable[[UpdateInfo], None],
        on_up_to_date: Optional[Callable] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        """Verifica atualizações em thread de background. Não bloqueia a UI."""
        if not REQUESTS_AVAILABLE:
            self._log("Módulo 'requests' não instalado — auto-update desabilitado.", "warn")
            return

        if self._checking:
            return

        self._checking = True

        def _task():
            try:
                info = self._fetch_latest()
                if info is None:
                    # sem asset compatível
                    if on_up_to_date:
                        on_up_to_date()
                    return

                current = _parse_version(__version__)
                latest = _parse_version(info.tag)

                if latest > current:
                    self._log(f"Nova versão disponível: v{info.version} (atual: v{__version__})", "info")
                    on_update_available(info)
                else:
                    self._log(f"Aplicativo atualizado (v{__version__}).", "info")
                    if on_up_to_date:
                        on_up_to_date()
            except Exception as exc:
                msg = f"Erro ao verificar atualizações: {exc}"
                self._log(msg, "warn")
                if on_error:
                    on_error(msg)
            finally:
                self._checking = False

        threading.Thread(target=_task, daemon=True, name="updater-check").start()

    def apply_update(self, info: UpdateInfo, progress_callback: Optional[Callable[[int], None]] = None):
        """
        Baixa o novo .exe e instala via script batch.
        Encerra o processo atual após lançar o batch.
        """
        if not REQUESTS_AVAILABLE:
            return

        self._log(f"Baixando atualização v{info.version}...", "info")

        # Pasta do executável atual (funciona tanto em dev quanto em .exe)
        if getattr(sys, "frozen", False):
            app_dir = os.path.dirname(sys.executable)
            exe_path = sys.executable
        else:
            app_dir = os.path.dirname(os.path.abspath(__file__))
            exe_path = os.path.join(app_dir, GITHUB_ASSET_NAME)

        new_exe = os.path.join(app_dir, f"_{GITHUB_ASSET_NAME}.new")
        bat_path = os.path.join(app_dir, "_update.bat")
        pid = os.getpid()

        # ── Download ──────────────────────────────────────────────────────
        try:
            resp = requests.get(info.download_url, stream=True, timeout=60)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0

            with open(new_exe, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total:
                        progress_callback(int(downloaded * 100 / total))

        except Exception as exc:
            self._log(f"Erro no download: {exc}", "error")
            if os.path.exists(new_exe):
                os.remove(new_exe)
            return

        self._log("Download concluído. Preparando instalação...", "info")

        # ── Script batch que substitui o .exe enquanto o app está fechado ──
        bat_content = f"""@echo off
echo Aguardando o aplicativo fechar...
:wait
tasklist /FI "PID eq {pid}" 2>NUL | find /I "{pid}" >NUL
if not errorlevel 1 (
    timeout /t 1 /nobreak >NUL
    goto wait
)
echo Instalando atualização...
move /Y "{new_exe}" "{exe_path}"
if %ERRORLEVEL% NEQ 0 (
    echo ERRO: nao foi possivel substituir o executavel.
    pause
    exit /b 1
)
echo Iniciando versão atualizada...
start "" "{exe_path}"
del "%~f0"
"""
        with open(bat_path, "w", encoding="ascii") as f:
            f.write(bat_content)

        self._log(f"Instalando v{info.version}... O aplicativo será reiniciado.", "success")

        # Lança o batch em janela oculta e encerra este processo
        subprocess.Popen(
            ["cmd.exe", "/c", bat_path],
            creationflags=subprocess.CREATE_NO_WINDOW,
            close_fds=True,
        )
        sys.exit(0)

    # ── private ─────────────────────────────────────────────────────────────

    def _fetch_latest(self) -> Optional[UpdateInfo]:
        """Consulta a API GitHub e retorna UpdateInfo ou None."""
        resp = requests.get(_API_URL, headers=_HEADERS, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        tag = data.get("tag_name", "")
        notes = data.get("body", "")

        # Procura o asset .exe com o nome esperado
        for asset in data.get("assets", []):
            if asset["name"].lower() == GITHUB_ASSET_NAME.lower():
                return UpdateInfo(
                    tag=tag,
                    notes=notes,
                    download_url=asset["browser_download_url"],
                    size=asset.get("size", 0),
                )

        return None
