CREATE TABLE IF NOT EXISTS plan_changes (
    id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT NOT NULL,
    change_type TEXT NOT NULL,
    field_name TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT NOT NULL,
    changed_by BIGINT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(plan_id) REFERENCES saas_plans(id),
    FOREIGN KEY(changed_by) REFERENCES users(id)
);

CREATE INDEX IF NOT EXISTS idx_plan_changes_plan_created_at
    ON plan_changes(plan_id, created_at);

CREATE TABLE IF NOT EXISTS billing_events (
    id BIGSERIAL PRIMARY KEY,
    subscription_id BIGINT,
    tenant_id BIGINT NOT NULL,
    event_type TEXT NOT NULL,
    amount DOUBLE PRECISION NOT NULL DEFAULT 0,
    currency TEXT NOT NULL DEFAULT 'BRL',
    status TEXT NOT NULL DEFAULT 'recorded',
    provider TEXT NOT NULL DEFAULT 'internal',
    provider_event_id TEXT,
    payload TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(subscription_id) REFERENCES saas_subscriptions(id),
    FOREIGN KEY(tenant_id) REFERENCES tenants(id)
);

CREATE INDEX IF NOT EXISTS idx_billing_events_tenant_created_at
    ON billing_events(tenant_id, created_at);

INSERT INTO billing_events (
    subscription_id,
    tenant_id,
    event_type,
    amount,
    currency,
    status,
    provider,
    provider_event_id,
    payload,
    created_at
)
SELECT
    saas_subscriptions.id,
    saas_subscriptions.tenant_id,
    'subscription_created',
    0,
    'BRL',
    'recorded',
    'internal',
    'seed-subscription-' || saas_subscriptions.id::text,
    NULL,
    saas_subscriptions.created_at
FROM saas_subscriptions
WHERE NOT EXISTS (
    SELECT 1
    FROM billing_events
    WHERE billing_events.provider_event_id = 'seed-subscription-' || saas_subscriptions.id::text
);