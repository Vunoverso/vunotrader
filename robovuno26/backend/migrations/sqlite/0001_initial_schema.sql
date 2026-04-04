CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    slug TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    tenant_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'owner',
    is_default INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, tenant_id),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(tenant_id) REFERENCES tenants(id)
);

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS login_attempts (
    identifier TEXT PRIMARY KEY,
    attempts INTEGER NOT NULL DEFAULT 0,
    window_started_at TEXT NOT NULL,
    blocked_until TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS robot_instances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    token TEXT NOT NULL UNIQUE,
    mode TEXT NOT NULL DEFAULT 'DEMO',
    is_active INTEGER NOT NULL DEFAULT 1,
    last_status TEXT,
    last_heartbeat_at TEXT,
    last_heartbeat_payload TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(id)
);

CREATE TABLE IF NOT EXISTS user_parameters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL UNIQUE,
    risk_per_trade REAL NOT NULL DEFAULT 0.5,
    max_spread_points REAL NOT NULL DEFAULT 30,
    default_lot REAL NOT NULL DEFAULT 0.01,
    stop_loss_points INTEGER NOT NULL DEFAULT 180,
    take_profit_points INTEGER NOT NULL DEFAULT 360,
    max_positions_per_symbol INTEGER NOT NULL DEFAULT 1,
    max_command_age_seconds INTEGER NOT NULL DEFAULT 45,
    deviation_points INTEGER NOT NULL DEFAULT 20,
    execution_retries INTEGER NOT NULL DEFAULT 3,
    pause_new_orders INTEGER NOT NULL DEFAULT 0,
    use_local_fallback INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(id)
);

CREATE TABLE IF NOT EXISTS trade_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    robot_instance_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    snapshot_payload TEXT NOT NULL,
    decision_payload TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(id),
    FOREIGN KEY(robot_instance_id) REFERENCES robot_instances(id)
);

CREATE TABLE IF NOT EXISTS trade_results (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    robot_instance_id INTEGER NOT NULL,
    symbol TEXT NOT NULL,
    outcome TEXT NOT NULL,
    pnl REAL NOT NULL,
    payload TEXT NOT NULL,
    closed_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(id),
    FOREIGN KEY(robot_instance_id) REFERENCES robot_instances(id)
);

CREATE TABLE IF NOT EXISTS audit_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id INTEGER NOT NULL,
    user_id INTEGER,
    robot_instance_id INTEGER,
    event_type TEXT NOT NULL,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(tenant_id) REFERENCES tenants(id),
    FOREIGN KEY(user_id) REFERENCES users(id),
    FOREIGN KEY(robot_instance_id) REFERENCES robot_instances(id)
);

CREATE INDEX IF NOT EXISTS idx_profiles_user_default ON profiles(user_id, is_default);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id, expires_at);
CREATE INDEX IF NOT EXISTS idx_login_attempts_updated_at ON login_attempts(updated_at);
CREATE INDEX IF NOT EXISTS idx_robot_instances_tenant ON robot_instances(tenant_id);
CREATE INDEX IF NOT EXISTS idx_user_parameters_tenant ON user_parameters(tenant_id);
CREATE INDEX IF NOT EXISTS idx_trade_decisions_tenant ON trade_decisions(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_trade_results_tenant ON trade_results(tenant_id, created_at);
CREATE INDEX IF NOT EXISTS idx_audit_events_tenant ON audit_events(tenant_id, created_at);
