ALTER TABLE robot_instances ADD COLUMN broker_profile TEXT NOT NULL DEFAULT 'CUSTOM';

ALTER TABLE robot_instances ADD COLUMN selected_symbols_json TEXT NOT NULL DEFAULT '[]';

ALTER TABLE robot_instances ADD COLUMN bridge_name TEXT NOT NULL DEFAULT '';

UPDATE robot_instances
SET broker_profile = 'CUSTOM'
WHERE broker_profile IS NULL OR TRIM(broker_profile) = '';

UPDATE robot_instances
SET selected_symbols_json = '[]'
WHERE selected_symbols_json IS NULL OR TRIM(selected_symbols_json) = '';

UPDATE robot_instances
SET bridge_name = 'VunoBridge-' || id
WHERE bridge_name IS NULL OR TRIM(bridge_name) = '';