# 2026-03-31 - Bot CMD com scanner multiativos e autonomia adaptativa

## Objetivo

Implementar no conector local Python (`scripts/mt5_cmd_bot.py`) capacidade de:

- navegar por uma lista de ativos
- classificar contexto de mercado por ativo (tendencia/lateral/volatil)
- filtrar cenarios de baixo volume
- ranquear melhor candidato de entrada
- executar modo autonomo em loop com selecao do melhor ativo por ciclo
- aprender localmente por simbolo/timeframe com resultados reais de trades fechados

## Arquivos impactados

- `scripts/mt5_cmd_bot.py`
- `README.md`

## Implementacao

### 1) Memoria local de aprendizado por ativo

Foi criado `SymbolAutonomyMemory` com persistencia em `autonomy_symbol_memory.json`:

- armazena `trades`, `wins`, `losses`, `pnl` por `symbol::timeframe`
- calcula `win_rate` local
- gera `priority_multiplier` limitado a +/-20% para evitar overfitting agressivo

### 2) Scanner multiativos (`scan-markets`)

Novo comando:

- `python scripts/mt5_cmd_bot.py scan-markets --symbols EURUSD,GBPUSD,USDJPY,XAUUSD --timeframe M5 --top 3`

Fluxo:

1. roda `DecisionEngine` em cada ativo
2. coleta indicadores principais (`rsi`, `momentum_20`, `volume_ratio`, `atr_pct`)
3. aplica score por ativo com base em:
- confianca
- regime
- volume relativo
- volatilidade minima
- multiplicador da memoria local
4. filtra por confianca minima e volume minimo
5. exibe ranking de candidatos

### 3) Modo autonomo (`run-autonomy`)

Novo comando:

- `python scripts/mt5_cmd_bot.py run-autonomy --symbols EURUSD,GBPUSD,USDJPY,XAUUSD --timeframe M5 --volume 0.01 --dry-run`

Fluxo:

1. varre ativos a cada ciclo
2. seleciona melhor candidato por score
3. respeita guardrail de posicoes abertas (quando `--allow-multiple` nao for usado)
4. envia ordem (ou simula com `--dry-run`)
5. monitora tickets abertos e, no fechamento, atualiza memoria local por ativo

## Decisoes tecnicas

- O scoring foi mantido simples e interpretavel para facilitar calibracao inicial.
- O aprendizado por ativo usa persistencia local em arquivo para nao acoplar ao backend nesta fase.
- O ajuste por memoria foi limitado para reduzir risco de sobreajuste local.

## Riscos e observacoes

- Este modo e complementar ao fluxo principal EA + Brain + Supabase.
- Em producao real, o recomendado continua sendo iniciar em demo e validar consistencia.
- O scanner nao substitui validacao estatistica de EV por ativo; ele prioriza oportunidades em tempo real com heuristica controlada.

## Proximos passos

1. Integrar score de spread/custo de transacao no ranking.
2. Adicionar limite de exposicao por correlacao entre ativos.
3. Persistir auditoria do scanner no backend para relatorios de EV por simbolo.
4. Conectar com camada de noticias em shadow para comparacao de impacto por ativo.
