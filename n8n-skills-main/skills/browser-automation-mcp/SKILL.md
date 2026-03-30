---
name: browser-automation-mcp
description: Automação web avançada utilizando MCP Server (Puppeteer/Playwright) para controle total de navegador, manipulação de DOM e capturas de tela.
---

# Browser Automation via MCP

Esta habilidade (Skill) ensina a IA e agentes a utilizarem um Servidor MCP de Automação de Navegador (como o `server-puppeteer` oficial ou soluções em Playwright). Isso concede "mãos" e "olhos" reais para a IA operar na web, driblando barreiras de requisições simples via HTTP/RAG.

## 🚀 O que essa habilidade engloba?

### 1. Interação e Navegação
- `navigate(url)`: Abre abas em um Chrome/Chromium real.
- `click(selector)`: Localiza elementos no DOM com precisão cirúrgica e dispara eventos de clique reais.
- `type(selector, text)`: Preenche inputs, campos de login ou pesquisas simulando a digitação humana.

### 2. Leitura e Monitoramento 
- Lê o **DOM real renderizado**, contornando proteções de Single Page Applications (React, Vue, Angular) onde web scrapers convencionais falham.
- Avaliação e execução de Javascript local pelo método `evaluate()`.

### 3. Visão e Debug
- `takeScreenshot()`: Extração de prints do navegador, permitindo repassar a imagem para a IA analisar visualmente a página atual e tomar decisões (ex: resolver CAPTCHAs básicos, verificar layout).

---

## 🛠️ Configuração Exata (Setup MCP)

Para dar essas habilidades ao seu Agente AI (seja no `n8n` ou localmente no Claude/Cursor), configure o servidor da seguinte forma no seu arquivo de gerência de MCP Servers (ex: `.mcp.json` ou `claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "browser-mcp": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-puppeteer"
      ]
    }
  }
}
```

### Orquestração no n8n
1. **Importação via n8n-mcp**: Cadastre o servidor `browser-mcp` através da sua extensão MCP no n8n.
2. **Loop de Agente**: Use um AI Agent node.
3. No prompt do Agent, inclua as seguintes instruções operacionais:
   > *"Sempre que precisar extrair dados de um site protegido, navegue na aba usando as ferramentas do 'browser-mcp'. Se um seletor falhar, tire um screenshot para analisar visualmente, reavalie o DOM e tente um XPath ou seletor CSS alternativo."*

## 💡 Cenários de Uso (Casos de Sucesso)
- Fazer auto-login em portais corporativos (que não tenham API pública).
- Extrair PDFs gerados dinamicamente em botões ("Download Fatura").
- Testes end-to-end de fluxos criados dentro dos próprios pipelines.
