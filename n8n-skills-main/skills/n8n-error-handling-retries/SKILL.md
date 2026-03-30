---
name: n8n-error-handling-retries
description: Estratégias para tratamento robusto de erros e fluxos de trabalho auto-corrigíveis no n8n.
---

# n8n Error Handling & Retries

Aprenda a tornar seus fluxos de trabalho resilientes a falhas externas.

## Estratégias de Recuperação

### 1. On Error (No Nó)
- Configure a opção **On Error** para "Continue" se quiser tratar o erro manualmente no próximo nó.
- Use o nó **Error Trigger** para capturar falhas em qualquer lugar do fluxo e enviar alertas (Slack/E-mail).

### 2. Retry On Fail
- Ative o "Retry On Fail" em nós que dependem de APIs instáveis.
- Configure o intervalo (Wait Between Tries) e o número máximo de tentativas (Max Tries).

### 3. Fluxos de "Self-Healing"
- Se um serviço falhar, tente uma rota alternativa ou use dados em cache para manter o sistema rodando.

## Monitoramento
- Crie um fluxo dedicado para logar erros em uma planilha ou banco de dados externo para auditoria futura.
