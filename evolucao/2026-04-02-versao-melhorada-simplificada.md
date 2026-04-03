# 2026-04-02 - Plano de versao melhorada e simplificada

## Data

2026-04-02

## Objetivo

Registrar a consolidacao de uma versao mais simples e objetiva do Vuno Trader, mantendo seguranca, multi-tenant, auditoria e integracao MT5 como nucleo do produto.

## Arquivos impactados

- projeto/versao-melhorada-simples.md

## Decisao

Foi definido um recorte mais enxuto do produto, com foco em:

- auth e tenant
- dashboard operacional
- operacoes
- auditoria
- parametros
- instalacao do robo
- integracao MT5 com heartbeat
- brain Python com signal, confidence e rationale

O escopo inicial exclui modulos secundarios e de maior custo de entrega, como estudos, retreinamento automatico, billing avancado e API publica externa.

## Alternativas descartadas

- Manter o escopo amplo atual desde o inicio: descartado por elevar complexidade, custo de manutencao e risco de produto sem consolidar o nucleo operacional.
- Reforcar framing de IA autonoma como proposta principal: descartado por conflito com o reposicionamento do produto e por aumentar risco de expectativa incorreta.

## Riscos ou observacoes

- O recorte simplificado depende de disciplina para nao reintroduzir features paralelas antes da consolidacao do nucleo.
- A seguranca multi-tenant continua sendo requisito estrutural, mesmo em versao simplificada.

## Proximos passos

- Usar o arquivo TXT como referencia de execucao para novas instrucoes e refinamentos.
- Se necessario, desdobrar esse plano em checklist tecnico por fase.