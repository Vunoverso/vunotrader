ALTER TABLE robot_instances ADD COLUMN IF NOT EXISTS primary_symbol TEXT NOT NULL DEFAULT '';

ALTER TABLE robot_instances ADD COLUMN IF NOT EXISTS chart_timeframe TEXT NOT NULL DEFAULT 'M5';

ALTER TABLE robot_instances ADD COLUMN IF NOT EXISTS discovered_symbols_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE robot_instances ADD COLUMN IF NOT EXISTS symbols_detected_at TEXT;

UPDATE robot_instances
SET chart_timeframe = 'M5'
WHERE chart_timeframe IS NULL OR BTRIM(chart_timeframe) = '';

UPDATE robot_instances
SET discovered_symbols_json = '[]'
WHERE discovered_symbols_json IS NULL OR BTRIM(discovered_symbols_json) = '';

UPDATE robot_instances
SET primary_symbol = ''
WHERE primary_symbol IS NULL;