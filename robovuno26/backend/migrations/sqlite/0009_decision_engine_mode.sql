ALTER TABLE user_parameters
ADD COLUMN decision_engine_mode TEXT NOT NULL DEFAULT 'HYBRID';

ALTER TABLE robot_instance_parameters
ADD COLUMN decision_engine_mode TEXT NOT NULL DEFAULT 'HYBRID';