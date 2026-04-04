Data: 2026-04-03

# Hardening do agente para exe desatualizado e snapshot bloqueado

## Objetivo

Eliminar a recorrência de erro no agente local quando o pacote distribuído ainda contém um executável antigo e quando o MT5 mantém um snapshot temporariamente bloqueado em disco.

## Situação encontrada

- o usuário estava iniciando o pacote em projeto/vuno-robo/agent-local
- o script de start priorizava sempre dist/vuno-agent.exe, mesmo quando o código-fonte local já estava mais novo que o binário
- ainda havia múltiplos agentes concorrendo na mesma bridge VunoBridge
- o script configure-mt5-bridge.ps1 do pacote espelhado falhava ao tentar escrever bridge_name em config legado sem a propriedade
- quando um snapshot ficava bloqueado pelo MT5, o agente tratava como snapshot inválido e em seguida tentava arquivar o mesmo arquivo, gerando erro adicional no loop principal

## Arquivos impactados

- agent-local/iniciar-vuno-robo.ps1
- projeto/vuno-robo/agent-local/iniciar-vuno-robo.ps1
- agent-local/app/main.py
- projeto/vuno-robo/agent-local/app/main.py
- projeto/vuno-robo/agent-local/configure-mt5-bridge.ps1

## Decisão tomada

- o start do agente agora evita usar o exe quando o código-fonte estiver mais novo, caindo automaticamente para Python
- também foi adicionado suporte explícito ao parâmetro ForcePython
- o script de configuração da bridge no pacote espelhado agora adiciona propriedades ausentes em configs legados em vez de falhar
- o loop do agente passou a distinguir arquivo bloqueado de snapshot realmente inválido
- snapshots e feedbacks bloqueados agora entram em retry e não geram erro inesperado do loop principal

## Validação executada

- análise estática sem erros nos scripts PowerShell e nos dois arquivos main.py alterados
- encerramento manual dos agentes duplicados que disputavam a mesma bridge
- reinicialização do pacote espelhado em modo Python com heartbeat e decisões normais
- validação do novo comportamento em log:
  - heartbeat ativo
  - runtime sincronizado
  - HOLD remoto normal
  - arquivo bloqueado tratado como retry, sem WinError 17 e sem loop quebrado

## Riscos e observações

- o exe antigo ainda existe no pacote espelhado; enquanto ele não for recompilado, o caminho mais seguro é usar a queda automática para Python ou ForcePython
- um snapshot específico pode continuar bloqueado enquanto o MT5 mantiver o handle aberto; o agente agora tolera isso, mas o arquivo preso ainda pode aparecer como retry no log

## Próximos passos

1. recompilar o executável do agente para alinhar o dist/vuno-agent.exe ao código atual
2. se o snapshot preso continuar aparecendo por muito tempo, revisar o EA/MT5 para entender por que esse arquivo não está sendo liberado
3. distribuir novo pacote quando o binário recompilado estiver pronto
