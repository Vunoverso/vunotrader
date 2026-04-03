# Vuno Trader - Versao Melhorada, Mais Simples e Mais Objetiva

## Objetivo

Criar uma versao mais enxuta do projeto, com foco em operacao SaaS segura, auditavel e facil de manter.

O produto deve continuar sendo um motor de decisao e controle operacional para MT5, e nao uma promessa de lucro automatico.

## Direcao do Produto

1. Priorizar clareza operacional.
2. Reduzir modulos paralelos e features nao essenciais.
3. Manter multi-tenant desde o inicio.
4. Trabalhar com demo-first como regra de seguranca.
5. Garantir rastreabilidade de cada decisao e cada execucao.

## Escopo da Versao Simplificada

### Entram no MVP

- autenticacao
- cadastro de tenant e usuario
- dashboard operacional
- pagina de operacoes
- pagina de auditoria
- pagina de parametros
- pagina de instalacao do robo
- integracao basica com MT5
- brain Python com decisao e logs

### Ficam Fora da Primeira Versao

- estudos com PDF e video
- recommendation engine
- retreinamento automatico
- cobranca avancada
- API publica externa
- automacoes complexas de admin

## Arquitetura Recomendada

### 1. Frontend Web

- Next.js com App Router
- React 19
- TypeScript sem any
- Tailwind v4

### 2. Backend

- FastAPI para endpoints protegidos e integracoes server-side
- Supabase para banco, auth e RLS

### 3. Brain de Decisao

- Python separado da web
- recebe contexto, calcula signal, confidence, rationale e risco
- registra decisao e resultado no banco

### 4. Execucao MT5

- EA envia eventos para backend ou brain
- motor responde BUY, SELL ou HOLD
- heartbeat simples para indicar conexao ativa

## Modulos Obrigatorios

### 1. Auth e Tenant

- login
- cadastro
- recuperacao de sessao
- tenant_id em toda entidade sensivel

### 2. Dashboard

- status do motor
- ultimas decisoes
- resumo de operacoes
- comparativo demo vs real quando houver dados

### 3. Operacoes

- lista de trades
- status
- resultado
- horario
- ativo

### 4. Auditoria

- sinal emitido
- confidence
- rationale
- regime
- custo de IA se existir
- motivo do HOLD quando houver

### 5. Parametros

- risco por operacao
- modo demo ou real
- stop e take
- limite de perdas consecutivas
- pausa automatica por drawdown

### 6. Instalacao

- gerar token do robo
- instrucoes de conexao
- status do heartbeat

## Modelo de Dados Simplificado

Manter poucas tabelas no inicio:

- tenants
- profiles
- robot_instances
- user_parameters
- trade_decisions
- trade_results
- ai_usage_logs
- audit_events

Se algum dado puder ser derivado, nao criar nova tabela no MVP.

## Seguranca Obrigatoria

1. Toda leitura e escrita com tenant_id.
2. RLS ativo em todas as tabelas multi-tenant.
3. Frontend nunca usa service role.
4. Chaves sensiveis so no backend e no ambiente seguro.
5. Logs sem senha, token, account ou segredo exposto.
6. Endpoints com validacao de input e rate limit.
7. Modo real protegido por regra explicita e auditavel.
8. Dados usados para IA devem ser anonimizados antes de qualquer reuso analitico.

## Semantica e UX Obrigatorias

1. HTML semantico em todas as paginas principais.
2. Button para acao, link apenas para navegacao.
3. Formularios com label clara e mensagens de erro objetivas.
4. Estados de loading, empty e error em todas as telas criticas.
5. Texto do produto sempre orientado a controle operacional e auditoria.

## Regra de Codigo

1. Arquivos com no maximo 200 linhas.
2. Se passou de 200 linhas, extrair componente, hook, schema ou service.
3. Nomes em kebab-case para arquivos e PascalCase para componentes.
4. Sem any e sem log solto em producao.
5. Comentarios apenas para decisao tecnica nao obvia.

## Padrao para Tailwind

1. Usar utilitarios direto no JSX.
2. Evitar CSS solto sem necessidade.
3. Reutilizar tokens visuais consistentes.
4. Mobile-first.
5. Componentes pequenos e focados.

## Fluxo Funcional Minimo

1. Usuario cria conta.
2. Usuario entra no app.
3. Gera token da instancia MT5.
4. Robo conecta e envia heartbeat.
5. Brain recebe contexto e responde decisao.
6. Sistema grava decisao e resultado.
7. Dashboard e auditoria exibem tudo por tenant.

## Plano de Implementacao

### Fase 1 - Base Segura

- auth
- tenant
- schema minimo
- RLS
- layout autenticado

### Fase 2 - Operacao Principal

- dashboard
- operacoes
- auditoria
- parametros

### Fase 3 - Integracao Real

- token do robo
- heartbeat
- decisao BUY SELL HOLD
- persistencia de resultados

### Fase 4 - Refinos

- comparativo demo vs real
- alertas simples
- melhoria de onboarding

## O Que Simplificar de Verdade

1. Um backend claro em vez de muitas camadas intermediarias.
2. Um brain com contrato pequeno e previsivel.
3. Poucas tabelas, com nomes diretos.
4. Poucas paginas, cada uma com papel claro.
5. Menos marketing de IA, mais explicacao de decisao.

## Definicao de Pronto

1. Usuario autentica e acessa somente seus dados.
2. Robo conecta com token valido.
3. Sistema registra heartbeat, decisao e resultado.
4. Dashboard mostra status e resumo real.
5. Auditoria mostra por que o motor decidiu.
6. Parametros de risco podem bloquear operacao insegura.

## Resumo Executivo

A melhor versao simplificada do projeto nao e a que tem mais modulos.

E a que entrega um nucleo muito bem feito: autenticacao, tenant, decisao, auditoria, parametros e integracao MT5.

Se essa base estiver limpa, segura e objetiva, o restante pode crescer sem virar um sistema confuso.