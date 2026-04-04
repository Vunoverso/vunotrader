CREATE TABLE IF NOT EXISTS saas_plans (
    id BIGSERIAL PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    monthly_price DOUBLE PRECISION NOT NULL DEFAULT 0,
    yearly_price DOUBLE PRECISION,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS saas_subscriptions (
    id BIGSERIAL PRIMARY KEY,
    tenant_id BIGINT NOT NULL,
    plan_id BIGINT NOT NULL,
    status TEXT NOT NULL,
    billing_cycle TEXT NOT NULL,
    current_period_start TEXT,
    current_period_end TEXT,
    trial_ends_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(id),
    FOREIGN KEY(plan_id) REFERENCES saas_plans(id)
);

CREATE INDEX IF NOT EXISTS idx_saas_subscriptions_tenant_status
    ON saas_subscriptions(tenant_id, status);

INSERT INTO saas_plans (
    code,
    name,
    description,
    monthly_price,
    yearly_price,
    is_active,
    created_at
) VALUES
    ('starter', 'Starter', 'Plano inicial com trial e ativacao manual.', 99.0, 990.0, 1, CURRENT_TIMESTAMP),
    ('pro', 'Pro', 'Plano para operacao continua com mais capacidade.', 249.0, 2490.0, 1, CURRENT_TIMESTAMP),
    ('scale', 'Scale', 'Plano para operacao ampliada e gestao de varias instancias.', 599.0, 5990.0, 1, CURRENT_TIMESTAMP)
ON CONFLICT (code) DO NOTHING;