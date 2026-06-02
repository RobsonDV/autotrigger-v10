"""
Envio e captura de hotkeys globais do sistema.
"""
import time


def send_hotkey(hotkey_str: str) -> bool:
    """
    Envia uma hotkey global para o sistema operacional.
    Exemplos: 'ctrl+f1', 'alt+f4', 'ctrl+shift+s'
    Retorna True se bem-sucedido.
    """
    if not hotkey_str:
        return False
    try:
        import keyboard
        time.sleep(0.15)  # Pequena pausa para garantir contexto de janela
        keyboard.send(hotkey_str)
        return True
    except Exception as exc:
        print(f"[HotkeySender] Erro ao enviar hotkey '{hotkey_str}': {exc}")
        return False


def capture_hotkey() -> str:
    """
    Aguarda e captura a próxima combinação de teclas pressionada.
    Retorna a string da hotkey (ex: 'ctrl+f1') ou string vazia em caso de erro.
    """
    try:
        import keyboard
        hk = keyboard.read_hotkey(suppress=False)
        return hk
    except Exception as exc:
        print(f"[HotkeySender] Erro ao capturar hotkey: {exc}")
        return ""
