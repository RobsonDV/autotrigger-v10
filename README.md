# ⚡ AutoTrigger V10

Automação de blocos de áudio/comandos para rádio ao vivo, no Windows. O app
monitora um arquivo TXT que o software de rádio atualiza com a mídia em exibição;
quando uma **palavra-chave** aparece no TXT, ele dispara uma **sequência** de
etapas configuráveis (mutar microfone, enviar hotkey, tocar vinheta, ligar stream,
aguardar retorno, etc.).

> Interface PySide6/Qt (estética "console de broadcast"). Backend Python para
> integração nativa com o Windows (áudio, hotkeys, monitoramento de arquivo, VLC).

---

## ✨ Principais recursos

- **Motor de sequências genérico** — cada sequência tem uma keyword de gatilho e
  uma lista de etapas, editável na interface (não é mais fluxo fixo).
- **Tipos de etapa:** mutar/desmutar dispositivo, abrir/fechar canal, enviar
  hotkey, tocar áudio, streaming (M3U/HLS/HTTP), aguardar tempo, aguardar keyword.
- **Atraso após gatilho** — espera configurável (h/m/s) antes de executar.
- **Calendário** — a sequência só fica armada nos dias definidos (sempre / dias da
  semana / datas específicas).
- **Hotkey com janela alvo** — foca a janela do software de rádio, envia a tecla e
  devolve o foco (não precisa estar em primeiro plano manualmente).
- **Unmute seguro ao fechar** — só desmuta dispositivos que o próprio app mutou.
- **Ferramentas de teste** — testar uma etapa isolada, **Ensaio** (dry-run, sem
  efeitos reais) e **Rodar agora** (disparo manual sem TXT).
- **Auto-update** via GitHub Releases.
- **VLC embutido** — não precisa instalar o VLC no PC do cliente.

---

## 🖥️ Interface

Janela única (mestre-detalhe), sem pop-ups:

- **Top bar:** logo · estado do Monitor · botão Iniciar/Parar · versão/atualização.
- **Sidebar:** lista de sequências (estado e marca "fora de agenda") · Nova
  sequência · Configurações Globais.
- **Detalhe:** edição inline de nome, keyword, atraso, agenda e etapas; a lista de
  etapas também é o fluxo visual da execução (ativa/concluída/erro).
- **Rodapé:** log em tempo real.

---

## 🚀 Uso rápido

1. Em **Configurações Globais**, defina o **arquivo TXT** monitorado e os
   **dispositivos** de entrada (mic) e saída (player) padrão.
2. Crie uma **sequência**, defina a **keyword** de gatilho e adicione as **etapas**.
3. (Opcional) Configure **atraso após gatilho** e **agenda** (dias).
4. Clique em **Iniciar Monitor**. Quando o TXT contiver a keyword, a sequência roda.
5. Use **🧪 Ensaio** para validar o fluxo sem mutar/disparar de verdade, ou **▶**
   numa etapa para testá-la isoladamente.

---

## 🧩 Arquitetura (resumo)

```
main.py              Entry point Qt: logging, backend, ponte de threads, tray
config.py            Config schema v2 (global + sequences); persistência atômica
timeparse.py         Parse/format de tempo (h/m/s) + agenda (is_armed_today)
applog.py            Logging em arquivo + excepthooks
audio_manager.py     Mute/unmute (pycaw) + ledger de mutes do app
player.py            Reprodução via python-vlc (arquivos + streams)
hotkey_sender.py     Envio de hotkey (global / janela alvo via pywin32)
file_monitor.py      Watchdog do TXT (keyword_map dinâmico)
step_runner.py       Executa uma etapa (suporta dry-run / prévia limitada)
sequence_runner.py   Executa uma sequência em thread (aplica o atraso)
sequence_engine.py   Orquestra N sequências; arma triggers conforme a agenda
updater.py           Auto-update via GitHub Releases
ui/                  PySide6/Qt: theme, qt_bridge, widgets, main_window,
                     sequence_detail, step_editor, global_settings, update_dialog
```

A documentação técnica viva e o histórico de decisões estão em [memory.md](memory.md).

---

## 🛠️ Desenvolvimento

Requisitos: Windows, Python 3.11, VLC instalado (apenas em dev; no .exe ele é
embutido).

```bat
pip install -r requirements.txt
python main.py
```

Verificar sintaxe de todos os módulos:

```bat
python -c "import py_compile; [py_compile.compile(f, doraise=True) for f in ['main.py','config.py','timeparse.py','applog.py','audio_manager.py','player.py','file_monitor.py','hotkey_sender.py','step_runner.py','sequence_runner.py','sequence_engine.py','ui/theme.py','ui/qt_bridge.py','ui/widgets.py','ui/step_editor.py','ui/global_settings.py','ui/sequence_detail.py','ui/main_window.py','ui/update_dialog.py']]"
```

---

## 📦 Build & Release

`build.bat` compila o `.exe` (onefile, com libVLC embutido) e publica a release no
GitHub via `gh`:

```bat
build.bat
```

- Embute o libVLC a partir de `C:\Program Files\VideoLAN\VLC` (ou defina `VLC_DIR`).
- Gera `dist\AutoTriggerV10.exe` (asset usado pelo auto-update).
- O instalador opcional é gerado por `installer.iss` (Inno Setup).

O auto-update compara a tag da última release do GitHub com `version.py`
(`__version__`) e baixa o `AutoTriggerV10.exe` da release mais recente.

---

## 🔧 Stack

Python · PySide6 (Qt 6) · pycaw · comtypes · python-vlc · watchdog · keyboard ·
pywin32 · requests · PyInstaller.

---

## 📍 Contexto de uso original

Rádio MaisNova / Terra FM — automação da Jornada Esportiva (mutar mic, parar
programação local, tocar vinheta, ligar stream da rádio esportiva por tempo fixo,
tocar vinheta de saída, retomar a programação, aguardar retorno no TXT, parar o
stream e desmutar).
