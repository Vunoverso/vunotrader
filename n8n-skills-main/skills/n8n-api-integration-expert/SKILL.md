---
name: n8n-api-integration-expert
description: Técnicas avançadas de integração de API no n8n, incluindo OAuth2 e paginação.
---

# n8n API Integration Expert

Domine a integração com qualquer serviço externo via HTTP Request.

## Autenticação e Segurança
- **OAuth2**: Siga o fluxo de autenticação do n8n para serviços que exigem tokens de acesso renováveis.
- **Header Auth**: Sempre prefira enviar chaves de API nos Headers em vez de Query Parameters.

## Paginação de Dados
- Muitos serviços limitam o número de itens por resposta (ex: 50 ou 100).
- Use loops e o nó **Code** para incrementar o número da página até que todos os dados sejam coletados.

## Manipulação de JSON
- Use **Expressions** para extrair dados profundos de objetos JSON complexos.
- Lembre-se que o n8n espera uma lista de objetos: `[{json: { ... }}]`.
