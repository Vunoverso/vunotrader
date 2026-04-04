ALTER TABLE user_parameters
ADD COLUMN reentry_cooldown_seconds INTEGER NOT NULL DEFAULT 60;