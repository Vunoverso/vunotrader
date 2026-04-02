-- Migração Auditoria 2.0: Colunas de Performance e Rastreio Real
-- Adiciona campos para armazenar o lucro financeiro, pontos e tempo de operação

ALTER TABLE trade_decisions 
ADD COLUMN IF NOT EXISTS outcome_profit numeric(14,2),
ADD COLUMN IF NOT EXISTS outcome_pips numeric(14,2),
ADD COLUMN IF NOT EXISTS entry_price real,
ADD COLUMN IF NOT EXISTS stop_loss real,
ADD COLUMN IF NOT EXISTS take_profit real,
ADD COLUMN IF NOT EXISTS closed_at timestamptz,
ADD COLUMN IF NOT EXISTS duration_seconds int;

-- Comentários para documentação
COMMENT ON COLUMN trade_decisions.outcome_profit IS 'Lucro financeiro final da operação (informado pelo MT5)';
COMMENT ON COLUMN trade_decisions.outcome_pips IS 'Resultado em pips/pontos da operação';
COMMENT ON COLUMN trade_decisions.closed_at IS 'Data e hora em que a operação foi finalizada (real ou virtual)';
COMMENT ON COLUMN trade_decisions.duration_seconds IS 'Duração total da operação em segundos';

-- Índices para performance em filtros de data
CREATE INDEX IF NOT EXISTS idx_trade_decisions_outcome_status ON trade_decisions (outcome_status);
CREATE INDEX IF NOT EXISTS idx_trade_decisions_created_at_desc ON trade_decisions (created_at DESC);
