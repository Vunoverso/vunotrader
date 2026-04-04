ALTER TABLE user_parameters
ADD COLUMN IF NOT EXISTS market_session_guard_enabled BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE user_parameters
ADD COLUMN IF NOT EXISTS daily_loss_limit DOUBLE PRECISION NOT NULL DEFAULT 0;

ALTER TABLE user_parameters
ADD COLUMN IF NOT EXISTS max_equity_drawdown_pct DOUBLE PRECISION NOT NULL DEFAULT 0;

ALTER TABLE user_parameters
ADD COLUMN IF NOT EXISTS break_even_trigger_points INTEGER NOT NULL DEFAULT 8;

ALTER TABLE user_parameters
ADD COLUMN IF NOT EXISTS trailing_trigger_points INTEGER NOT NULL DEFAULT 14;

ALTER TABLE user_parameters
ADD COLUMN IF NOT EXISTS position_time_stop_minutes INTEGER NOT NULL DEFAULT 90;

ALTER TABLE user_parameters
ADD COLUMN IF NOT EXISTS position_stagnation_window_candles INTEGER NOT NULL DEFAULT 6;

ALTER TABLE robot_instance_parameters
ADD COLUMN IF NOT EXISTS market_session_guard_enabled BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE robot_instance_parameters
ADD COLUMN IF NOT EXISTS daily_loss_limit DOUBLE PRECISION NOT NULL DEFAULT 0;

ALTER TABLE robot_instance_parameters
ADD COLUMN IF NOT EXISTS max_equity_drawdown_pct DOUBLE PRECISION NOT NULL DEFAULT 0;

ALTER TABLE robot_instance_parameters
ADD COLUMN IF NOT EXISTS break_even_trigger_points INTEGER NOT NULL DEFAULT 8;

ALTER TABLE robot_instance_parameters
ADD COLUMN IF NOT EXISTS trailing_trigger_points INTEGER NOT NULL DEFAULT 14;

ALTER TABLE robot_instance_parameters
ADD COLUMN IF NOT EXISTS position_time_stop_minutes INTEGER NOT NULL DEFAULT 90;

ALTER TABLE robot_instance_parameters
ADD COLUMN IF NOT EXISTS position_stagnation_window_candles INTEGER NOT NULL DEFAULT 6;