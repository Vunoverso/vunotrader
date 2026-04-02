-- Adiciona coluna de motivo de saída para auditoria de Smart Exit
ALTER TABLE trade_decisions 
ADD COLUMN IF NOT EXISTS exit_reason text;

-- Comentários (opcional)
COMMENT ON COLUMN trade_decisions.exit_reason IS 'Motivo do fechamento: SL, TP, SMART_EXIT_VPE ou MANUAL';
