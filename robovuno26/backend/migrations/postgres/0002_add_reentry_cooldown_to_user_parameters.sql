ALTER TABLE user_parameters
ADD COLUMN IF NOT EXISTS reentry_cooldown_seconds INTEGER NOT NULL DEFAULT 60;