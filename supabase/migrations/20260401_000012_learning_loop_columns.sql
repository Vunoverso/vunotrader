-- Adiciona colunas para o Ciclo de Aprendizado Autônomo na tabela trade_decisions
ALTER TABLE trade_decisions 
ADD COLUMN IF NOT EXISTS entry_price numeric(14,6),
ADD COLUMN IF NOT EXISTS outcome_status text DEFAULT 'pending',
ADD COLUMN IF NOT EXISTS outcome_pips numeric(14,2);

-- Índices para otimizar a busca de decisões pendentes
CREATE INDEX IF NOT EXISTS idx_trade_decisions_pending 
ON trade_decisions (symbol, outcome_status) 
WHERE (outcome_status = 'pending');
