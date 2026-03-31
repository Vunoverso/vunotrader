# 2026-03-31 - Auditoria: indicador shadow global (agreement)

## Objetivo
Exibir na auditoria web se a decisao local do brain estava alinhada ou divergente da recomendacao da memoria global, sem alterar execucao.

## Arquivos impactados
- `vunotrader_brain.py`
- `web/src/components/app/auditoria-table.tsx`

## Implementacao
1. **Persistencia sem migration**
- O brain passou a anexar um marcador tecnico no `rationale` quando houver dado de shadow global:
  - `| SHADOW:agree|diverge;global=BUY|SELL;wr=xx.x%;n=NN`
- Isso permitiu leitura no frontend sem mudar schema de `trade_decisions`.

2. **Auditoria web**
- Nova leitura de marcador em `parseShadowFromRationale()`.
- Badge por linha:
  - `Global alinhado` (ciano)
  - `Global divergente` (laranja)
- No detalhe expandido, exibe:
  - status (alinhado/divergente)
  - lado global sugerido
  - win rate agregado
  - tamanho de amostra
- Funcoes de limpeza removem sufixo tecnico da justificativa para manter UX legivel.

## Seguranca
- Nenhuma alteracao na execucao de ordens.
- Modo continua estritamente shadow/observabilidade.

## Proximos passos
1. Levar filtro "Global divergente" para o select de auditoria.
2. Exibir estatistica consolidada de agreement no topo da pagina.
3. Se validado por periodo, usar apenas para ajuste de risco (nao sinal) em fase assistida.
