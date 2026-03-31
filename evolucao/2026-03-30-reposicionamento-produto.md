# 2026-03-30 — Reposicionamento de produto: Motor de Decisão

## Objetivo

Remover o framing "IA que opera trader" de todos os pontos de contato do produto
e substituir por "motor de decisão e controle operacional".

Motivo: framing anterior gerava expectativa de lucro automático, risco jurídico
e churn alto na primeira perda. O diferencial real do Vuno é a rastreabilidade
de decisão ponta-a-ponta, não a promessa de operação autônoma.

## Arquivos impactados

- `projeto/saas_blueprint.md` — visão de produto reescrita
- `web/src/lib/marketing-content.ts` — heroMetrics, featureCards, workflowSteps, planCards, faqItems
- `web/src/app/page.tsx` — hero badge e descrição do produto
- `web/src/app/app/dashboard/page.tsx` — subtítulo, painel motor de decisão, card "Motor de decisão"
- `web/src/app/app/layout.tsx` — topbar: "Robô inativo" → "Motor desconectado"
- `web/src/components/app/auditoria-table.tsx` — subtítulo da auditoria

## Mudanças na UI do dashboard

Adicionado painel **"Última decisão do motor"** que exibe:
- score de confiança (0-100)
- sinal (BUY/SELL/HOLD) com badge colorido
- ativo e timeframe
- modo (demo/real) com badge colorido
- justificativa textual (rationale) truncada
- risco sugerido
- data/hora + link para auditoria
- custo de IA do dia (quando > 0)

Painel usa queries reais ao Supabase (`trade_decisions` + `ai_usage_logs`).
Quando não há dados, exibe EmptyState explicando que o motor registra até HOLDs.

## Mudanças de framing (resumo)

| Antes | Depois |
|---|---|
| SaaS de robô trader com IA controlada | Motor de decisão e controle de operação |
| Resumo rápido do seu robô hoje | Painel de controle operacional |
| Inteligência (card) | Motor de decisão (card) |
| Trilha de decisões, resultados e motivos do robô | Motor de decisão — trilha auditável de cada sinal |
| Robô inativo (topbar) | Motor desconectado (topbar) |
| "IA que opera" | "sistema que explica por que operou" |

## Marketing-content — novos eixos de comunicação

1. **Decisão explicável** — cada sinal tem motivo registrado, não é caixa preta
2. **Proteção demo-first** — a política de modo real é da plataforma, não do usuário
3. **Trilha auditável** — confiança, risco calculado, custo de IA e resultado vinculados
4. **Flywheel anonimizado** — dados agregados melhoram o motor para todos os clientes

FAQ atualizado com: "O sistema garante lucro automático?" = Não, deixando explícito.

## Decisão sobre FAQ item "estudos"

Feature de estudos (PDF/vídeo) foi mantida na sidebar mas removida dos featureCards
do marketing. Nao é diferencial principal — é upsell. Registrado como referência futura.

## Sem breaking changes

Nenhuma query nova foi adicionada ao servidor sem fallback.
`lastDecision` e `aiLogs` queries usam `?? null` e `?? []` — dashboard funciona
normalmente mesmo quando tabelas estão vazias ou migration 000005 não aplicada.

## Próximos passos

- Aplicar migration 000005 para ativar `robot_instances`
- Conectar badge de status do topbar a query real de `robot_instances` (status ao vivo)
- Adicionar score de decisão como coluna na tabela da auditoria (não só no expanded)
