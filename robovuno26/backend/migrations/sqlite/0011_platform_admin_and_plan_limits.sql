ALTER TABLE users ADD COLUMN is_platform_admin INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS saas_plan_limits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    plan_id INTEGER NOT NULL UNIQUE,
    max_users INTEGER,
    max_trades_per_month INTEGER,
    max_ai_tokens_per_day INTEGER,
    max_storage_gb REAL,
    max_bots INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY(plan_id) REFERENCES saas_plans(id)
);

INSERT OR IGNORE INTO saas_plan_limits (
    plan_id, max_users, max_trades_per_month, max_ai_tokens_per_day, max_storage_gb, max_bots, created_at
)
SELECT id, 1, 200, 50000, 1.0, 1, CURRENT_TIMESTAMP FROM saas_plans WHERE code = 'starter';

INSERT OR IGNORE INTO saas_plan_limits (
    plan_id, max_users, max_trades_per_month, max_ai_tokens_per_day, max_storage_gb, max_bots, created_at
)
SELECT id, 3, 1500, 250000, 5.0, 3, CURRENT_TIMESTAMP FROM saas_plans WHERE code = 'pro';

INSERT OR IGNORE INTO saas_plan_limits (
    plan_id, max_users, max_trades_per_month, max_ai_tokens_per_day, max_storage_gb, max_bots, created_at
)
SELECT id, 10, 10000, 1000000, 20.0, 10, CURRENT_TIMESTAMP FROM saas_plans WHERE code = 'scale';