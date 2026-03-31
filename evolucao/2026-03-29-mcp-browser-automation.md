# MCP Browser Automation

## Data

2026-03-29

## Objetivo

Habilitar automacao de browser via MCP para ampliar capacidade de teste e inspecao visual da aplicacao local.

## Caminho escolhido

- servidor MCP: browser-automation-mcp
- engine: Playwright MCP
- pacote: @playwright/mcp
- configurado no workspace e no escopo global do usuario
- navegador padrao ajustado para Chrome

## Arquivos atualizados

- [.vscode/mcp.json](../.vscode/mcp.json)
- [C:/Users/hause/AppData/Roaming/Code/User/mcp.json](../../../../c:/Users/hause/AppData/Roaming/Code/User/mcp.json)
- [scripts/start-edge-cdp.ps1](../scripts/start-edge-cdp.ps1)
- [scripts/start-chrome-cdp.ps1](../scripts/start-chrome-cdp.ps1)
- [scripts/check-cdp.ps1](../scripts/check-cdp.ps1)
- [scripts/start-playwright-mcp-extension.ps1](../scripts/start-playwright-mcp-extension.ps1)

## Correcao aplicada

- tentativa inicial com @modelcontextprotocol/server-playwright falhou (pacote inexistente no npm)
- configuracao corrigida para @playwright/mcp

## Observacoes

- para inspeção avançada no chat, tambem foi habilitado workbench.browser.enableChatTools no VS Code
- essa configuracao amplia automacao no browser integrado, nao no navegador externo do sistema
- endpoint CDP em 127.0.0.1:9222 validado com sucesso

## Proximos passos

- usar o browser integrado para smoke tests guiados por rota
- incluir roteiro de teste exploratorio com severidade no fluxo do agente

## Atualizacao 2026-03-30 - Remocao do MCP Supabase auto-start no workspace

### Objetivo

- Evitar mensagem recorrente de "Iniciando servidores MCP supabase" no inicio de cada conversa no VS Code.

### Arquivo impactado

- [.vscode/mcp.json](../.vscode/mcp.json)

### Decisao tomada

- Removida a entrada `supabase` da configuracao de servidores MCP do workspace.
- Mantidos os servidores MCP de browser (Playwright/Chrome CDP).

### Observacao

- Se o MCP Supabase estiver configurado no escopo global do usuario, a mensagem ainda pode aparecer em outros workspaces ate remover tambem no config global.

## Atualizacao 2026-03-30 - Correcao de lint PowerShell no launcher Chrome

### Objetivo

- Eliminar aviso do PSScriptAnalyzer no script de inicializacao do Chrome com CDP.

### Arquivo impactado

- [scripts/start-chrome-cdp.ps1](../scripts/start-chrome-cdp.ps1)

### Correcao aplicada

- Variavel local `$args` foi renomeada para `$chromeArgs` para evitar conflito com a variavel automatica do PowerShell.
- Chamada `Start-Process` atualizada para usar o novo nome, sem mudanca funcional.

### Resultado

- Removida qualquer atribuicao a variavel local com nome `args` no script.
- Em validacao pelo painel de problemas, o alerta pode permanecer por falso positivo/cache do analisador (mensagem fixa mesmo sem ocorrencia de atribuicao).