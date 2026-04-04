# 2026-04-04 - Fase de charts dedicados por simbolo para shadow visual multiativos

## Data

2026-04-04

## Objetivo

Desenhar a proxima fase do shadow visual para que o scanner multiativos tenha cobertura visual correta por simbolo, sem reutilizar o screenshot do chart anexado para ativos diferentes.

## Problema atual

- o Gate 0 captura screenshot apenas do chart onde o EA esta anexado
- o scanner pode decidir sobre varios simbolos no mesmo ciclo
- reaproveitar a mesma imagem para outro simbolo falseia a auditoria e mascara divergencia visual real

## Decisao de arquitetura

- manter o Gate 0 restrito ao chart anexado
- abrir uma fase dedicada para charts por simbolo quando a cobertura visual multiativos entrar em producao real
- o mapeamento visual deixa de ser implicito e passa a ser explicito: cada simbolo elegivel para shadow visual precisa de um `chart_id` proprio no terminal

## Escopo da fase

### 1. Cadastro operacional por instancia

- cada `robot_instance` passa a declarar um conjunto de simbolos visuais elegiveis
- cada simbolo elegivel guarda:
  - `symbol`
  - `chart_timeframe`
  - `chart_id` no terminal
  - estado (`attached`, `missing`, `stale`, `paused`)
  - horario da ultima confirmacao do chart

### 2. Contrato MT5 -> agent-local

- o snapshot passa a carregar `chart_symbol`, `chart_timeframe` e `chart_id`
- o bridge so anexa screenshot quando o ciclo vem do mesmo `chart_id`
- se o scanner decidir por simbolo sem chart dedicado ativo, o ciclo persiste como `skipped_non_chart_symbol`

### 3. Politica de abertura de charts

- abrir charts apenas para simbolos selecionados pelo usuario ou pela politica da instancia
- limitar o total por instancia para evitar degradacao do terminal
- sugerir teto inicial de 4 charts dedicados por instancia em Pro e 8 em Scale

### 4. Politica de saude e reciclagem

- chart sem heartbeat de catalogo vira `stale`
- chart com simbolo trocado manualmente invalida o mapeamento
- o agente local deve reconciliar simbolos detectados versus charts esperados a cada catalogo

## Persistencia sugerida

- adicionar metadados dedicados de chart na instancia ou em tabela filha `robot_instance_visual_charts`
- colunas minimas sugeridas:
  - `id`
  - `robot_instance_id`
  - `symbol`
  - `chart_timeframe`
  - `chart_id`
  - `status`
  - `last_seen_at`
  - `last_cycle_id`

## UX e painel

- a instalacao deve mostrar quais simbolos tem chart dedicado pronto
- dashboard e auditoria devem diferenciar:
  - screenshot real do simbolo
  - ciclo sem chart dedicado
  - chart dedicado stale ou ausente
- o painel de instancia deve permitir pausar ou remover charts dedicados sem revogar a instancia inteira

## Alternativas descartadas

- manter um unico chart e usar screenshot compartilhado: descartado por correlacao falsa
- abrir charts dinamicamente a cada ciclo candidato: descartado por latencia, flicker operacional e risco alto no terminal
- promover multiativos visual antes do mapeamento `symbol -> chart_id`: descartado por baixa auditabilidade

## Riscos

- mais charts abertos aumentam consumo de CPU e memoria do terminal
- corretoras com simbolos customizados exigem validacao do nome exato por instancia
- o catalogo de simbolos precisa detectar drift rapido para evitar screenshot do ativo errado

## Proximos passos

1. transformar o desenho em backlog tecnico com migration e contrato do catalogo
2. decidir se `robot_instance_visual_charts` entra na raiz atual ou vem junto da portabilidade do painel operacional do `robovuno26`
3. prototipar o limite operacional de charts por instancia em demo antes de liberar para cliente real