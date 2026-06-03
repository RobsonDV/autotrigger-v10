## AutoTrigger V10 — v2.2.3

Desenvolvido por **RobsonDV**.

### Correção do auto-update (importante)
- Corrigido o erro **"Permission denied"** ao atualizar com o app instalado em
  *Program Files*: a nova versão é baixada numa pasta temporária e a troca do
  executável é feita com **elevação (UAC)**, reiniciando o app sem privilégios.
- Configurações agora ficam sempre em **%APPDATA%\AutoTriggerV10** (sem conflito
  de permissão).

> ⚠️ Como as versões anteriores (≤ 2.2.2) têm o updater antigo, **esta versão
> precisa ser instalada manualmente uma vez** (rode o instalador
> AutoTriggerV10_Setup_v2.2.3.exe). A partir dela, as próximas atualizações são
> automáticas.

### Inclui tudo das 2.2.x
- Excluir/duplicar sequência, ✕ de etapa destacado, tooltips.
- Interface PySide6/Qt, seletor de janela alvo, captura de hotkey.
- Ferramentas de teste (testar etapa, Ensaio, Rodar agora).
- Atraso após gatilho, calendário, unmute seguro, VLC embutido.
