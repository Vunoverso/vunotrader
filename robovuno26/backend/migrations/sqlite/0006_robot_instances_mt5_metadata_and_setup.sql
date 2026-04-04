ALTER TABLE robot_instances ADD COLUMN primary_symbol TEXT NOT NULL DEFAULT '';

ALTER TABLE robot_instances ADD COLUMN chart_timeframe TEXT NOT NULL DEFAULT 'M5';

ALTER TABLE robot_instances ADD COLUMN discovered_symbols_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE robot_instances ADD COLUMN symbols_detected_at TEXT;

UPDATE robot_instances
SET chart_timeframe = 'M5'
WHERE chart_timeframe IS NULL OR TRIM(chart_timeframe) = '';

UPDATE robot_instances
SET discovered_symbols_json = '[]'
WHERE discovered_symbols_json IS NULL OR TRIM(discovered_symbols_json) = '';

UPDATE robot_instances
SET primary_symbol = ''
WHERE primary_symbol IS NULL;