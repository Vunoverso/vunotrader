Data: 2026-04-03

# Planejamento documentado do motor de Price Action VPE

## Objetivo

Registrar a decisao de consolidar os PDFs de Price Action em um plano tecnico implantavel no robo, evitando perda de contexto antes da codificacao.

## Fontes consolidadas

- projeto/price_action_completo_vpe (1).pdf
- projeto/Ebook-Price-Action.pdf
- projeto/CURSO_PRICE_ACTION.pdf
- backend/app/decision_engine.py
- backend/app/models.py
- mt5/vuno-bridge/vuno-bridge-io.mqh

## Decisao tomada

- foi criado um documento novo em projeto com comparativo entre motor atual e motor desejado
- o documento define a rota de implantacao do VPE por fases, sem depender de memoria informal da conversa
- a prioridade escolhida foi OHLC estruturado + price action numerico, e nao leitura por imagem
- order blocks, SMC completo e auditoria visual pesada ficaram como etapas posteriores

## Arquivo criado

- projeto/2026-04-03-plano-implantacao-price-action-vpe.md

## Alternativas descartadas

- sair codando o motor novo sem documento-base: descartado por alto risco de retrabalho
- comecar por leitura de imagem do chart: descartado porque o motor ainda nem recebe a estrutura minima de candles
- misturar tudo no decision_engine atual de uma vez: descartado por risco de acoplamento e baixa explicabilidade

## Riscos e observacoes

- o PDF VPE da uma direcao muito mais completa que a base atual, mas parte das regras exatas ainda precisara ser fechada no codigo
- o primeiro passo obrigatorio continua sendo ampliar o snapshot do MT5
- o motor atual EMA+RSI pode continuar temporariamente como fallback durante a transicao

## Proximos passos

1. implementar o novo contrato de snapshot com serie de candles
2. criar o nucleo inicial de patterns, zones e structure no backend
3. expor setup, score e motivo do HOLD no painel
