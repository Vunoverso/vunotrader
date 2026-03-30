# Backend Auth Base

## Data

2026-03-29

## Objetivo

Criar a base do backend SaaS com auth, recuperacao de senha, seguranca inicial e integracao com Supabase.

## Caminho escolhido

- FastAPI como backend de dominio.
- Supabase Auth como provedor principal de autenticacao.
- Supabase Postgres como banco principal.
- RLS multi-tenant no banco para isolamento de dados.

## Motivo da escolha

- reduz complexidade de auth e recuperacao de senha
- aproveita a infraestrutura do Supabase ja definida no projeto
- acelera entrega do SaaS sem criar auth custom desnecessario
- melhora seguranca ao manter sessao e identidade no provedor adequado

## Alternativas analisadas e nao adotadas agora

### Auth proprio com JWT local

Nao adotado neste momento porque aumentaria custo tecnico, risco de seguranca e tempo de entrega.

### Sessao stateful propria no backend

Nao adotada porque duplicaria responsabilidades que o Supabase Auth ja cobre bem.

## Arquivos criados

- [backend/requirements.txt](../backend/requirements.txt)
- [backend/.env.example](../backend/.env.example)
- [backend/app/main.py](../backend/app/main.py)
- [backend/app/core/config.py](../backend/app/core/config.py)
- [backend/app/core/security.py](../backend/app/core/security.py)
- [backend/app/core/supabase.py](../backend/app/core/supabase.py)
- [backend/app/core/dependencies.py](../backend/app/core/dependencies.py)
- [backend/app/services/auth.py](../backend/app/services/auth.py)
- [backend/app/api/router.py](../backend/app/api/router.py)
- [backend/app/api/routes/auth.py](../backend/app/api/routes/auth.py)
- [backend/app/api/routes/account.py](../backend/app/api/routes/account.py)
- [backend/app/api/routes/health.py](../backend/app/api/routes/health.py)
- [backend/app/schemas/auth.py](../backend/app/schemas/auth.py)
- [backend/app/schemas/account.py](../backend/app/schemas/account.py)
- [backend/README.md](../backend/README.md)
- [projeto/auth_flow.md](../projeto/auth_flow.md)
- [projeto/supabase_auth_security.sql](../projeto/supabase_auth_security.sql)
- [supabase/migrations/20260329_000002_auth_security.sql](../supabase/migrations/20260329_000002_auth_security.sql)

## Entrega funcional desta etapa

- signup
- login
- refresh de sessao
- recuperacao de senha
- update de senha
- endpoint de sessao autenticada
- middlewares basicos de seguranca
- trigger de criacao de perfil
- RLS multi-tenant inicial
- migracoes aplicadas no Supabase remoto com sucesso
- ambiente local do backend preparado com .env fora de versionamento

## Riscos e observacoes

- Ainda faltam endpoints de administracao, assinatura e faturamento.
- Ainda falta integrar frontend de login e dashboard.
- Ainda falta configurar envio e callback de recuperacao de senha no frontend.

## Proximos passos

- aplicar migracoes no Supabase
- implementar endpoints de administracao da organizacao
- implementar parametros do robo e dashboard de trades