"""
MaisNova Sport Trigger — Entry point.
Inicializa todas as dependências e inicia a UI.
"""
import sys
import os
import threading

# Compatibilidade com PyInstaller (recursos bundled)
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS  # type: ignore[attr-defined]
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Inicializar COM antes de qualquer import de pycaw
import comtypes
try:
    comtypes.CoInitialize()
except OSError:
    pass

import customtkinter as ctk

from config import Config
import audio_manager as _audio
import hotkey_sender as _hotkey
from player import AudioPlayer
from file_monitor import FileMonitor
from sequence import Sequence
from ui.main_window import MainWindow


# ── Proxy classes ─────────────────────────────────────────────────────────────

class _AudioManagerProxy:
    """Adapta as funções do módulo audio_manager para a interface esperada por Sequence/ConfigTab."""
    def mute_device(self, device_id: str) -> bool:
        return _audio.mute_device(device_id)

    def unmute_device(self, device_id: str) -> bool:
        return _audio.unmute_device(device_id)

    def list_input_devices(self) -> list:
        return _audio.list_input_devices()

    def list_output_devices(self) -> list:
        return _audio.list_output_devices()


class _HotkeyProxy:
    def send_hotkey(self, hk: str) -> bool:
        return _hotkey.send_hotkey(hk)


# ── Tray icon ─────────────────────────────────────────────────────────────────

def _build_tray_icon(window: MainWindow, on_quit):
    """Cria o ícone da bandeja do sistema."""
    try:
        import pystray
        from PIL import Image, ImageDraw
    except ImportError:
        print("[Tray] pystray/Pillow não disponível. Ícone na bandeja desabilitado.")
        return None

    # Tentar carregar icon.ico; gerar programaticamente caso não exista
    icon_path = os.path.join(BASE_DIR, "assets", "icon.ico")
    if os.path.exists(icon_path):
        try:
            img = Image.open(icon_path)
        except Exception:
            img = _make_icon()
    else:
        img = _make_icon()

    def _show(icon, _item):
        icon.stop()
        window.after(0, window.show)

    def _quit(icon, _item):
        icon.stop()
        window.after(0, on_quit)

    menu = pystray.Menu(
        pystray.MenuItem("Abrir", _show, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Sair", _quit),
    )

    return pystray.Icon("sport_trigger", img, "MaisNova Sport Trigger", menu)


def _make_icon():
    """Gera um ícone simples programaticamente com Pillow."""
    from PIL import Image, ImageDraw
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    # Círculo externo azul
    d.ellipse([2, 2, size - 2, size - 2], fill="#2979ff")
    # Círculo interno branco (microfone estilizado)
    d.ellipse([20, 16, size - 20, size - 16], fill="#ffffff")
    d.rectangle([28, 16, size - 28, size - 16], fill="#2979ff")
    # Base do microfone
    d.rectangle([30, 44, size - 30, 48], fill="#ffffff")
    d.rectangle([size // 2 - 1, 48, size // 2 + 1, 54], fill="#ffffff")
    d.rectangle([24, 54, size - 24, 57], fill="#ffffff")
    return img


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    config = Config()
    player = AudioPlayer()
    file_monitor = FileMonitor()
    audio_mgr = _AudioManagerProxy()
    hotkey_mgr = _HotkeyProxy()

    # Configura o dispositivo de saída do player
    player.set_output_device(config.get("output_device_id", ""))

    sequence = Sequence(
        config=config,
        audio_manager=audio_mgr,
        player=player,
        hotkey_sender=hotkey_mgr,
    )

    window = MainWindow(
        config=config,
        audio_manager=audio_mgr,
        sequence=sequence,
        file_monitor=file_monitor,
        player=player,
    )
    # Mantém referência ao player para cleanup
    window._player = player

    # ── Cleanup ──
    def _quit():
        file_monitor.stop()
        sequence.cancel()
        try:
            player.release()
        except Exception:
            pass
        window.destroy()

    window._quit_fn = _quit

    # ── Tray ──
    tray = _build_tray_icon(window, _quit)
    if tray:
        tray_thread = threading.Thread(target=tray.run, daemon=True, name="tray")
        tray_thread.start()

    # ── Verificação VLC ──
    if not player.is_vlc_available():
        window.log(
            "AVISO: VLC não encontrado. Instale o VLC (https://www.videolan.org) para habilitar o player.",
            "error",
        )

    window.mainloop()

    # Cleanup ao fechar pela janela (quando não usa tray)
    file_monitor.stop()
    try:
        player.release()
    except Exception:
        pass


if __name__ == "__main__":
    main()
