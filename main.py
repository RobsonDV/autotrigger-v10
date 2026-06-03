"""
AutoTrigger V10 — Entry point.
Inicializa todas as dependencias e inicia a UI.
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
from sequence_engine import SequenceEngine
from ui.main_window import MainWindow


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

    return pystray.Icon("autotrigger_v10", img, "AutoTrigger V10", menu)


def _make_icon():
    """Gera o icone de automacao do AutoTrigger V10 via create_icon."""
    try:
        from create_icon import draw_icon
        return draw_icon(64)
    except Exception:
        # Fallback minimo
        from PIL import Image, ImageDraw
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([2, 2, size - 2, size - 2], fill="#0e1634")
        d.ellipse([8, 8, size - 8, size - 8], outline="#00b4ff", width=4)
        return img
    return img


# ── Main ─────────────────────────────────────────────────────────────────────

def main():
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    config = Config()
    player = AudioPlayer()
    file_monitor = FileMonitor()
    engine = SequenceEngine(config, player, file_monitor)

    window = MainWindow(config=config, engine=engine, player=player)

    # ── Cleanup ──
    def _quit():
        file_monitor.stop()
        engine.cancel_all()
        engine.stop_monitor()
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
