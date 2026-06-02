# MaisNova Sport Trigger — Memória do Projeto

> **Arquivo vivo.** Atualizado a cada sessão de desenvolvimento.  
> Contém todo o histórico de decisões, tecnologias, bugs resolvidos e planos futuros.  
> Última atualização: 2026-06-02

---

## 1. Visão Geral do Produto

**Nome:** MaisNova Sport Trigger  
**Plataforma:** Windows (desktop, standalone .exe)  
**Propósito:** Automação do bloco esportivo em rádios ao vivo.

### O Problema que Resolve
Durante a Jornada Esportiva ao vivo, o operador de áudio precisa:
- Mutar o microfone (para não vazar áudio da rádio esportiva parceira)
- Parar a programação local (hotkey no software de rádio)
- Tocar uma vinheta de entrada
- Ligar o stream da rádio esportiva por tempo fixo
- Tocar uma vinheta de encerramento
- Retomar a programação local (hotkey PLAY)
- Aguardar sinal de retorno no arquivo TXT
- Parar o stream esportivo e desmutar o microfone

O app faz **tudo isso automaticamente** monitorando um arquivo TXT que o software de rádio atualiza com o nome da mídia em exibição.

### Contexto de Uso
- **Rádio:** MaisNova / Terra FM (97,7 MHz – região amazônica)
- **Hardware de áudio:** RODECaster Pro Stereo
  - Input device: `Microfone (RODECaster Pro Stereo)` — ID: `{0.0.1.00000000}.{2a24c533-249e-4725-8743-197ba474ac03}`
  - Output device: `Alto-falantes (RODECaster Pro Stereo)` — ID: `{0.0.0.00000000}.{26e07ddf-8bb3-415e-835b-a63ee090dfba}`
- **Stream da jornada:** `https://8033.brasilstream.com.br/stream.m3u`
- **Hotkeys configuradas:** F11 (STOP) e F9 (PLAY)
- **Arquivo TXT monitorado:** `C:/Users/User/Downloads/MidiaAtual.txt`
- **Keywords:** `ESPORTE` (início) e `FIM_ESPORTE` (retorno)

---

## 2. Stack Tecnológica

| Biblioteca | Versão | Função |
|---|---|---|
| Python | 3.11 | Linguagem principal |
| CustomTkinter | ≥ 5.2.0 | UI moderna (tema dark) |
| pycaw | ≥ 20230407 | Windows Core Audio API — mute/unmute |
| comtypes | ≥ 1.4.1 | COM initialization (necessário para pycaw) |
| python-vlc | ≥ 3.0.21203 | Reprodução de áudio (arquivos + streams M3U) |
| watchdog | ≥ 4.0.0 | Monitoramento em tempo real do arquivo TXT |
| keyboard | ≥ 0.13.5 | Envio e captura de hotkeys globais |
| pystray | ≥ 0.19.5 | Ícone na bandeja do sistema |
| Pillow | ≥ 10.0.0 | Geração programática do ícone da bandeja |
| PyInstaller | ≥ 6.0.0 | Empacotamento em .exe standalone |

### Por que VLC (python-vlc) e não pygame/simpleaudio?
- VLC suporta nativamente M3U, HLS e streams HTTP
- Permite selecionar dispositivo de saída por ID (Windows MMDevice)
- Mais estável para streams de rádio ao vivo com buffering configurável

### Por que pycaw?
- Única biblioteca Python que acessa a API de áudio do Windows (WASAPI/MMDevice) para mutar dispositivos individuais
- Alternativas como sounddevice não permitem mute/unmute de dispositivos do sistema

---

## 3. Estrutura de Arquivos

```
Jornada_Maisnova/
├── main.py               # Entry point — inicializa tudo, tray icon, lifecycle
├── config.py             # Carrega/salva config.json; DEFAULT_CONFIG; classe Config
├── config.json           # Configuração persistida pelo usuário
├── audio_manager.py      # Mute/unmute via pycaw (list_input/output_devices)
├── player.py             # AudioPlayer — reprodução VLC (arquivo + stream M3U)
├── sequence.py           # Máquina de estados da Jornada Esportiva (8 estados)
├── file_monitor.py       # Watchdog — monitora TXT e dispara triggers
├── hotkey_sender.py      # send_hotkey() e capture_hotkey() via keyboard lib
├── requirements.txt      # Dependências pip
├── run.bat               # Atalho para rodar em dev
├── build.bat             # Script PyInstaller para gerar .exe
├── memory.md             # Este arquivo — documentação viva do projeto
├── assets/
│   └── icon.ico          # Ícone da aplicação
└── ui/
    ├── __init__.py
    ├── main_window.py    # Janela principal CTk + abas + header + statusbar
    ├── config_tab.py     # Aba de configurações completa
    └── log_tab.py        # Aba de log + painel visual da sequência
```

---

## 4. Arquitetura e Padrões de Design

### Máquina de Estados (sequence.py)
```
IDLE → MUTING → AUDIO1 → STREAMING → AUDIO2 → PLAY_CMD → WAITING_NEXT
                                                                  ↓
                                                           STOP_RETURN → IDLE
```

| Estado | O que acontece |
|---|---|
| `IDLE` | Aguardando keyword no TXT |
| `MUTING` | Muta input device + envia hotkey STOP |
| `AUDIO1` | Toca Vinheta 1 (aguarda terminar) |
| `STREAMING` | Toca stream M3U por `stream_duration` segundos |
| `AUDIO2` | Toca Vinheta 2 (aguarda terminar) |
| `PLAY_CMD` | Envia hotkey PLAY |
| `WAITING_NEXT` | Aguarda keyword de retorno no TXT |
| `STOP_RETURN` | Envia hotkey STOP + desmuta input → IDLE |

### Threading
- Sequência roda em daemon thread `sport-sequence`
- Retorno roda em daemon thread `sport-return`
- FileMonitor roda o Watchdog em thread própria
- `threading.Event` para sincronização entre steps
- `cancel_event` para interrupção segura a qualquer momento
- `comtypes.CoInitialize()` chamado em cada thread que usa pycaw

### VLC e Dispositivos de Saída
- Instância VLC com `--network-caching=8000 --live-caching=8000`
- Arquivos locais → `vlc.MediaPlayer`
- Playlists/streams (`.m3u`, `.m3u8`, `.pls`, `.xspf`, `.asx`) → `vlc.MediaListPlayer`
- Output device configurado via `audio_output_set("mmdevice")` + `audio_output_device_set()`
- Aplicado em thread separada após VLC inicializar (aguarda até 5s)

### UI (CustomTkinter)
- Tema escuro fixo (`set_appearance_mode("dark")`)
- Janela principal com 2 abas: **Configurações** e **Log / Status**
- Fecha para a bandeja (não encerra o processo)
- `_STATE_DISPLAY` dict mapeia State → (texto, cor) para o header
- Painel visual `SequencePanel` no log_tab com 7 boxes animados

---

## 5. Fases de Desenvolvimento

### Fase 1 — Concepção (Sessão inicial)
- Definição do problema e do fluxo completo
- Escolha de tecnologias
- Scaffolding inicial de todos os arquivos
- Instalação de dependências

### Fase 2 — Core Funcional
- `audio_manager.py` implementado e testado (3 dispositivos encontrados)
- `file_monitor.py` com watchdog funcionando
- `hotkey_sender.py` com send + capture
- `player.py` versão inicial (só arquivos locais)
- `sequence.py` versão inicial (fluxo básico)

### Fase 3 — Bug Fixes Críticos
**Bug 1 — pycaw API mismatch:**  
`CLSID_MMDeviceEnumerator` não exportado em pycaw ≥20230407.  
→ Fix: usar `AudioUtilities.GetDeviceEnumerator()` + `AudioUtilities.CreateDevice()`

**Bug 2 — device_id não salvo no config:**  
`_save()` salvava só o nome, não o ID.  
→ Fix: iterar `_input_devices`/`_output_devices` para buscar ID por nome

**Bug 3 — M3U stream reportando Ended imediatamente:**  
VLC parseava o container M3U rápido e disparava Ended antes do áudio.  
→ Fix: usar `MediaListPlayer` para extensões de playlist + sleep-based timer

**Bug 4 — Substring match incorreta:**  
`"ESPORTE"` era encontrado dentro de `"FIM_ESPORTE"`.  
→ Fix: checar `keyword_unmute` PRIMEIRO em `file_monitor.py`

**Bug 5 — Sem áudio no stream:**  
VLC não usava o dispositivo de saída configurado.  
→ Fix: `audio_output_set("mmdevice")` + `audio_output_device_set()` após inicialização VLC

### Fase 4 — Major Update (Fluxo Completo + UI)
- Renomeado `hotkey` → `hotkey_stop` + novo `hotkey_play`
- Sequência reescrita com 8 estados (MUTING antes da Vinheta 1)
- UI atualizada: dois campos de hotkey com botões "Capturar" independentes
- Painel visual `SequencePanel` com 7 etapas (azul=ativo, verde=concluído)
- `main_window.py` atualizado com novos estados no `_STATE_DISPLAY`
- `main.py` passa `player` para `MainWindow`, aplica `set_output_device()` na init
- Log do player conectado à UI via `set_log()`

### Fase 5 — Documentação e Repositório (atual)
- Criação deste `memory.md`
- `.gitignore` configurado
- Repositório GitHub criado e código publicado

---

## 6. Bugs Conhecidos / Pendências

| # | Descrição | Status |
|---|---|---|
| 1 | VLC requer instalação separada no sistema (não bundled no .exe) | Aberto |
| 2 | PyInstaller `.exe` ainda não gerado/testado | Aberto |
| 3 | `run.bat` / `build.bat` — verificar se estão corretos | Aberto |
| 4 | Teste end-to-end completo com hardware real | Pendente |
| 5 | Stream sem áudio (parcialmente resolvido — aguarda teste real) | Em acompanhamento |

---

## 7. Planos Futuros (Ideias Discutidas)

### Alta Prioridade
- **Build PyInstaller (.exe):** Empacotar como executável único para distribuição sem precisar de Python instalado
- **Incluir VLC no bundle:** Investigar `vlc.dll` + libs dentro do .exe (ou instruir instalação separada com um `check_dependencies()` na inicialização)
- **Teste end-to-end:** Validar todo o fluxo com o RODECaster Pro e o software de rádio real

### Média Prioridade
- **Múltiplos perfis:** Salvar/carregar diferentes configurações (ex: perfil "Jornada Esportiva", perfil "Debate", etc.)
- **Histórico de jornadas:** Log persistido em arquivo com data/hora de cada execução
- **Notificação sonora de alerta:** Beep ou som curto se a keyword demorar demais
- **Timeout configurável para WAITING_NEXT:** Hoje não tem limite — se o TXT nunca tiver `FIM_ESPORTE`, fica esperando para sempre

### Futuro / Nice-to-have
- **Interface de teste de cada passo individualmente:** Botões "Testar Vinheta 1", "Testar Stream", "Testar Hotkey STOP" na aba de config
- **Integração com OBS/vMix:** Enviar cenas por WebSocket quando a jornada iniciar/encerrar
- **Suporte a múltiplas rádios esportivas:** Selecionar qual stream tocar por palavra-chave diferente
- **Modo "ensaio":** Simula toda a sequência sem realmente mutar/enviar hotkeys
- **Watchdog de saúde do stream:** Reiniciar automaticamente se o stream cair durante a transmissão
- **Auto-update:** Verificar GitHub por novas versões ao iniciar
- **Versão web (Electron/Tauri):** Tornar multiplataforma para Mac/Linux

---

## 8. Configuração de Referência

```json
{
  "txt_file_path": "C:/Users/User/Downloads/MidiaAtual.txt",
  "keyword_start": "ESPORTE",
  "keyword_unmute": "FIM_ESPORTE",
  "input_device_id": "{0.0.1.00000000}.{2a24c533-249e-4725-8743-197ba474ac03}",
  "input_device_name": "Microfone (RODECaster Pro Stereo)",
  "output_device_id": "{0.0.0.00000000}.{26e07ddf-8bb3-415e-835b-a63ee090dfba}",
  "output_device_name": "Alto-falantes (RODECaster Pro Stereo)",
  "audio_file_1": "E:/Playlist Pajé/VHT TERRA FM/VHT TERRA FM - 97,7 CARIMBO_4 (ACCAPELA).mp3",
  "audio_file_2": "E:/Playlist Pajé/VHT TERRA FM/VHT TERRA FM - A MELHOR DA REGIAO (FEM).mp3",
  "stream_url": "https://8033.brasilstream.com.br/stream.m3u",
  "stream_duration": 30,
  "hotkey_stop": "f11",
  "hotkey_play": "f9"
}
```

---

## 9. Comandos Úteis

```bash
# Rodar em desenvolvimento
python main.py

# Verificar sintaxe de todos os arquivos
python -c "import py_compile; [py_compile.compile(f, doraise=True) or print('OK', f) for f in ['main.py','config.py','audio_manager.py','player.py','sequence.py','file_monitor.py','hotkey_sender.py','ui/config_tab.py','ui/log_tab.py','ui/main_window.py']]"

# Instalar dependências
pip install -r requirements.txt

# Gerar .exe (após PyInstaller configurado)
build.bat

# Listar dispositivos de áudio disponíveis
python -c "import audio_manager; print(audio_manager.list_input_devices()); print(audio_manager.list_output_devices())"
```

---

## 10. Histórico de Atualizações deste Arquivo

| Data | Descrição |
|---|---|
| 2026-06-02 | Criação inicial — documentação completa das fases 1-5 |

