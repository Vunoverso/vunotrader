# Evolucao do Projeto Base

## Data

2026-03-29

## Contexto

Foi definido o direcionamento inicial do sistema Vuno Trader como plataforma SaaS com robo trader, cerebro Python, execucao MT5, dashboard web, autenticacao, planos e base de IA com aprendizado controlado.

## Decisoes consolidadas

- O robo deve operar com modos observer, demo e real.
- Demo e o ambiente principal de aprendizado.
- Real deve usar modelo aprovado e controlado.
- Toda entrada e saida de trade deve gerar registro auditavel.
- O sistema tera dashboard web, parametros do usuario, estudos com videos e PDFs e analise por IA.
- O sistema sera multi-tenant.
- Os dados de usuarios usados para IA interna devem ser anonimizados.

## Artefatos ja criados

- plano principal em [projeto/planotrader.md](../projeto/planotrader.md)
- schema inicial em [projeto/supabase_schema.sql](../projeto/supabase_schema.sql)
- migracao inicial em [supabase/migrations/20260329_000001_initial_trader_schema.sql](../supabase/migrations/20260329_000001_initial_trader_schema.sql)
- blueprint SaaS em [projeto/saas_blueprint.md](../projeto/saas_blueprint.md)
- politica de anonimização em [projeto/anonimizacao_ia.md](../projeto/anonimizacao_ia.md)
- setup Supabase em [projeto/supabase_setup.md](../projeto/supabase_setup.md)

## Risco atual

- Ainda nao existe implementacao do app SaaS em codigo.
- Ainda nao existe pipeline real de treinamento conectado ao Supabase.
- Ainda nao existe painel web operacional.

## Regra operacional registrada

Antes de novas alteracoes em codigo, revisar a pasta evolucao para evitar retrabalho e conflito entre plano e implementacao.

Quando houver multiplos caminhos tecnicos, o agente deve escolher o melhor caminho para o projeto e registrar as demais alternativas com justificativa, evitando indecisao e retrabalho.

## Proximos passos sugeridos

- iniciar backend com auth e multi-tenant
- iniciar frontend SaaS com dashboard e parametros
- integrar Python brain ao Supabase

## Atualizacao 2026-03-30 - Brain Python configurado

- Integracao opcional com pacote `brain-py` adicionada em `vunotrader_brain.py`.
- Chave `ENABLE_BRAINPY` controla ativacao sem quebrar o fluxo principal (fallback para engine local RF+GB).
- Adicionado arquivo `brain-requirements.txt` para facilitar setup do brain.
- Adicionado script `scripts/setup-brain-venv.ps1` para bootstrap automatico com Python 3.11, criacao de venv, instalacao de dependencias e validacao do import de `brain-py`.
- Observacao tecnica: em Windows + Python 3.12, `brain-py` pode falhar por compatibilidade de `jax/jaxlib`; preferir Python 3.10/3.11 para uso efetivo do pacote.

## Atualizacao 2026-03-30 - Onboarding de instalacao MT5

- Criada pagina dedicada de instrucoes em `web/src/app/app/instalacao/page.tsx`.
- Incluido item `Instalacao` no menu lateral em `web/src/components/app/app-sidebar.tsx`.
- Conteudo cobre fluxo do cliente: instalar MT5, copiar EA, gerar token, configurar EA e validar conexao no dashboard.
- Disponibilizado download direto do EA em `web/public/downloads/VunoTrader_v2.mq5` com CTA visivel na pagina de instalacao.
- Pagina de instalacao simplificada para reduzir ruido visual e deixar onboarding mais objetivo.