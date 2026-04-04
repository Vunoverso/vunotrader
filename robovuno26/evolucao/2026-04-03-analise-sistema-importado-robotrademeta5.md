Data: 2026-04-03

## Objetivo

Analisar o projeto importado `robotrademeta5` na raiz do workspace para decidir o que deve ser incorporado ao Vuno Trader atual, o que pode ser reaproveitado parcialmente e o que deve ficar apenas como referencia tecnica.

## Arquivos e modulos analisados

- robotrademeta5/README.md
- robotrademeta5/backend/app/main.py
- robotrademeta5/backend/app/api/routes/mt5.py
- robotrademeta5/backend/app/api/routes/auth.py
- robotrademeta5/backend/app/api/routes/account.py
- robotrademeta5/backend/app/api/routes/trading_profile.py
- robotrademeta5/backend/app/core/dependencies.py
- robotrademeta5/backend/app/core/security.py
- robotrademeta5/backend/app/core/supabase.py
- robotrademeta5/backend/app/services/auth.py
- robotrademeta5/backend/app/core/price_action.py
- robotrademeta5/vuno_core/decision_engine.py
- robotrademeta5/scripts/mt5_cmd_bot.py
- robotrademeta5/web/src/middleware.ts
- robotrademeta5/web/src/app/app/admin/page.tsx
- robotrademeta5/web/src/app/app/dashboard/page.tsx
- robotrademeta5/web/src/app/app/assinatura/page.tsx
- robotrademeta5/supabase/migrations/*
- robotrademeta5/render.yaml
- backend/app/decision_engine.py
- backend/app/runtime_policy.py
- backend/app/price_action_patterns.py
- backend/app/price_action_zones.py
- mt5/VunoRemoteBridge.mq5

## Decisao tomada

O projeto importado e util para o Vuno Trader atual, mas nao deve ser incorporado como bloco unico.

Rota adotada:

- incorporar agora a camada SaaS mais madura do projeto importado, principalmente auth, padroes de Supabase, middleware do web, telas administrativas, assinatura e estrutura de deploy
- reaproveitar parcialmente o bot Python direto do MT5 e a ideia de memoria local por ativo, mas reescrevendo o motor para usar o fluxo atual de Price Action VPE e runtime policy do Vuno
- manter apenas como referencia o core ML-first do `robotrademeta5`, porque ele conflita com a direcao atual do Vuno, que ja segue para Price Action explicavel com auditoria e gates operacionais

## Pontos fortes encontrados

- backend e web com stack aderente ao alvo atual: FastAPI + Next.js + Supabase
- auth, membership e onboarding SaaS mais avancados que a base atual
- painel admin e assinatura com leitura real de dados do banco
- organizacao maior de produto, cobrindo operacao, estudos, assinatura e administracao
- configuracao de deploy pronta com `render.yaml` e `backend/Dockerfile`
- schema Supabase mais rico, com historico de migracoes e entidades de auditoria e faturamento
- script `mt5_cmd_bot.py` com scanner multiativos, memoria local e operacao assistida via Python

## Riscos e observacoes

- o core de decisao do importado e ML-first e diverge da direcao atual do Vuno, que privilegia Price Action, explicabilidade e auditoria
- o endpoint MT5 do projeto importado valida `robot_id` e `organization_id`, mas aceita `user_id` vindo do payload para buscar parametros e gravar eventos; isso precisa endurecimento antes de qualquer reaproveitamento direto
- o backend importado usa service-role do Supabase em varios pontos; a integracao precisa revisar com cuidado onde a seguranca depende do backend e onde depende de RLS
- o `trading_profile.py` esta mais proximo de stub do que de persistencia real
- o projeto importado tem amplitude de features maior do que o escopo atual do MVP; se for absorvido sem corte, ele aumenta o custo de integracao e pode atrasar o nucleo operacional

## Divergencia relevante com o plano atual

O Vuno atual ja evoluiu em direcao a runtime policy, gate de performance, pausa por noticias, snapshot OHLC e modulos de Price Action. O `robotrademeta5` e mais maduro em SaaS e administracao, mas fica atras nessa direcao de motor decisorio explicavel e camada de seguranca operacional.

## Proximos passos

1. mapear quais rotas, telas e migrations do `robotrademeta5` valem extracao imediata para a base atual
2. portar apenas a camada SaaS e administrativa, sem substituir o motor de decisao atual
3. redesenhar o `mt5_cmd_bot.py` para usar o score do Vuno atual em vez do core ML do projeto importado
4. revisar seguranca dos payloads MT5 antes de reaproveitar qualquer rota diretamente