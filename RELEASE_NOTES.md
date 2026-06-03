## AutoTrigger V10 — v2.2.4

Desenvolvido por **RobsonDV**.

### Instalação por usuário → fim dos erros de atualização
- O app agora instala em **%LocalAppData%** (por usuário, **sem precisar de admin**).
- Como a pasta é gravável, o **auto-update funciona sozinho, sem UAC e sem erro de
  permissão**.

> ⚠️ **Troca única (importante):** esta versão usa um novo modo de instalação.
> No PC do cliente:
> 1. **Desinstale** a versão antiga "AutoTrigger V10" (a que estava em Arquivos de Programas).
> 2. Instale o **AutoTriggerV10_Setup_v2.2.4.exe** (não pede admin).
>
> A partir daqui, **todas as próximas atualizações são automáticas e silenciosas**.
> Suas sequências/configurações são preservadas (ficam em %APPDATA%).

### Inclui tudo das 2.2.x
- Excluir/duplicar sequência, ✕ de etapa destacado, tooltips.
- Interface PySide6/Qt, seletor de janela alvo, captura de hotkey.
- Ferramentas de teste (testar etapa, Ensaio, Rodar agora).
- Atraso após gatilho, calendário, unmute seguro, VLC embutido.
