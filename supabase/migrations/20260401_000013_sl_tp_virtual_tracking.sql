-- Adiciona campos sugeridos de Stop Loss e Take Profit para o monitoramento virtual
ALTER TABLE trade_decisions 
ADD COLUMN IF NOT EXISTS stop_loss numeric(14,6),
ADD COLUMN IF NOT EXISTS take_profit numeric(14,6),
ADD COLUMN IF NOT EXISTS post_analysis text;

-- Comentários para documentação
COMMENT ON COLUMN trade_decisions.stop_loss IS 'Preço de Stop Loss sugerido pelo motor de análise no momento do sinal';
COMMENT ON COLUMN trade_decisions.take_profit IS 'Preço de Take Profit sugerido pelo motor de análise no momento do sinal';
COMMENT ON COLUMN trade_decisions.post_analysis IS 'Explicação técnica gerada pela IA para o resultado deste sinal';
COMMENT ON COLUMN trade_decisions.outcome_status IS 'Status do resultado (pending, win, loss, canceled) - Atualizado via Virtual Tracking';
