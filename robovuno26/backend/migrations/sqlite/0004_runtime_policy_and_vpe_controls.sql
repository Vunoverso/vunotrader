ALTER TABLE user_parameters
ADD COLUMN operational_timeframe TEXT NOT NULL DEFAULT 'M5';

ALTER TABLE user_parameters
ADD COLUMN confirmation_timeframe TEXT NOT NULL DEFAULT 'H1';

ALTER TABLE user_parameters
ADD COLUMN news_pause_enabled INTEGER NOT NULL DEFAULT 1;

ALTER TABLE user_parameters
ADD COLUMN news_pause_symbols TEXT NOT NULL DEFAULT 'XAUUSD';

ALTER TABLE user_parameters
ADD COLUMN news_pause_countries TEXT NOT NULL DEFAULT 'USD';

ALTER TABLE user_parameters
ADD COLUMN news_pause_before_minutes INTEGER NOT NULL DEFAULT 30;

ALTER TABLE user_parameters
ADD COLUMN news_pause_after_minutes INTEGER NOT NULL DEFAULT 30;

ALTER TABLE user_parameters
ADD COLUMN news_pause_impact TEXT NOT NULL DEFAULT 'HIGH';

ALTER TABLE user_parameters
ADD COLUMN performance_gate_enabled INTEGER NOT NULL DEFAULT 1;

ALTER TABLE user_parameters
ADD COLUMN performance_gate_min_profit_factor REAL NOT NULL DEFAULT 1.3;

ALTER TABLE user_parameters
ADD COLUMN performance_gate_min_trades INTEGER NOT NULL DEFAULT 100;

ALTER TABLE user_parameters
ADD COLUMN validated_backtest_profit_factor REAL NOT NULL DEFAULT 0;

ALTER TABLE user_parameters
ADD COLUMN validated_backtest_trades INTEGER NOT NULL DEFAULT 0;