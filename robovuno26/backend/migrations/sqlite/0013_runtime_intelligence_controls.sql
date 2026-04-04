ALTER TABLE user_parameters
ADD COLUMN market_session_guard_enabled INTEGER NOT NULL DEFAULT 1;

ALTER TABLE user_parameters
ADD COLUMN daily_loss_limit REAL NOT NULL DEFAULT 0;

ALTER TABLE user_parameters
ADD COLUMN max_equity_drawdown_pct REAL NOT NULL DEFAULT 0;

ALTER TABLE user_parameters
ADD COLUMN break_even_trigger_points INTEGER NOT NULL DEFAULT 8;

ALTER TABLE user_parameters
ADD COLUMN trailing_trigger_points INTEGER NOT NULL DEFAULT 14;

ALTER TABLE user_parameters
ADD COLUMN position_time_stop_minutes INTEGER NOT NULL DEFAULT 90;

ALTER TABLE user_parameters
ADD COLUMN position_stagnation_window_candles INTEGER NOT NULL DEFAULT 6;

ALTER TABLE robot_instance_parameters
ADD COLUMN market_session_guard_enabled INTEGER NOT NULL DEFAULT 1;

ALTER TABLE robot_instance_parameters
ADD COLUMN daily_loss_limit REAL NOT NULL DEFAULT 0;

ALTER TABLE robot_instance_parameters
ADD COLUMN max_equity_drawdown_pct REAL NOT NULL DEFAULT 0;

ALTER TABLE robot_instance_parameters
ADD COLUMN break_even_trigger_points INTEGER NOT NULL DEFAULT 8;

ALTER TABLE robot_instance_parameters
ADD COLUMN trailing_trigger_points INTEGER NOT NULL DEFAULT 14;

ALTER TABLE robot_instance_parameters
ADD COLUMN position_time_stop_minutes INTEGER NOT NULL DEFAULT 90;

ALTER TABLE robot_instance_parameters
ADD COLUMN position_stagnation_window_candles INTEGER NOT NULL DEFAULT 6;