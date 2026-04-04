from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator

from .instrument_catalog import (
    merge_primary_symbol,
    normalize_broker_profile,
    normalize_catalog_symbols,
    normalize_primary_symbol,
    normalize_selected_symbols,
)


VALID_TIMEFRAMES = {"M1", "M5", "M15", "M30", "H1", "H4", "D1", "W1", "MN1"}
VALID_NEWS_IMPACTS = {"LOW", "MEDIUM", "HIGH"}
VALID_DECISION_ENGINE_MODES = {"LEGACY_ONLY", "HYBRID", "PRICE_ACTION_ONLY"}
VALID_POSITION_ACTIONS = {"NONE", "CLOSE", "PROTECT"}


def normalize_timeframe_value(value: str) -> str:
    timeframe = value.upper().strip()
    if timeframe not in VALID_TIMEFRAMES:
        raise ValueError("timeframe invalido")
    return timeframe


def normalize_decision_engine_mode_value(value: str) -> str:
    mode = str(value or "HYBRID").upper().strip()
    if mode not in VALID_DECISION_ENGINE_MODES:
        raise ValueError("modo do motor invalido")
    return mode


def normalize_position_action_value(value: str) -> str:
    action = str(value or "NONE").upper().strip()
    if action not in VALID_POSITION_ACTIONS:
        raise ValueError("acao de posicao invalida")
    return action


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)
    tenant_name: str | None = Field(default=None, min_length=3, max_length=100)


class LoginRequest(BaseModel):
    email: str
    password: str


class SessionUserResponse(BaseModel):
    user_id: int
    email: str
    tenant_id: int
    tenant_name: str
    role: str
    is_platform_admin: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_at: str
    user: SessionUserResponse


class CreateRobotInstanceRequest(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    mode: str = Field(default="DEMO")
    broker_profile: str = Field(default="CUSTOM", min_length=3, max_length=40)
    primary_symbol: str = Field(default="", max_length=40)
    chart_timeframe: str = Field(default="M5", min_length=2, max_length=4)
    selected_symbols: list[str] = Field(default_factory=list)

    @field_validator("mode")
    @classmethod
    def normalize_mode(cls, value: str) -> str:
        mode = value.upper().strip()
        if mode not in {"DEMO", "REAL"}:
            raise ValueError("mode deve ser DEMO ou REAL")
        return mode

    @field_validator("broker_profile")
    @classmethod
    def validate_broker_profile(cls, value: str) -> str:
        return normalize_broker_profile(value)

    @field_validator("primary_symbol")
    @classmethod
    def validate_primary_symbol(cls, value: str) -> str:
        return normalize_primary_symbol(value)

    @field_validator("chart_timeframe")
    @classmethod
    def validate_chart_timeframe(cls, value: str) -> str:
        return normalize_timeframe_value(value)

    @field_validator("selected_symbols", mode="before")
    @classmethod
    def validate_selected_symbols(cls, value: Any) -> list[str]:
        return normalize_selected_symbols(value)

    @model_validator(mode="after")
    def normalize_symbol_setup(self) -> "CreateRobotInstanceRequest":
        primary_symbol, selected_symbols = merge_primary_symbol(self.primary_symbol, self.selected_symbols)
        self.primary_symbol = primary_symbol
        self.selected_symbols = selected_symbols
        return self


class UpdateRobotInstanceRequest(BaseModel):
    name: str = Field(min_length=3, max_length=80)
    mode: str = Field(default="DEMO")
    broker_profile: str = Field(default="CUSTOM", min_length=3, max_length=40)
    primary_symbol: str = Field(default="", max_length=40)
    chart_timeframe: str = Field(default="M5", min_length=2, max_length=4)
    selected_symbols: list[str] = Field(default_factory=list)

    @field_validator("mode")
    @classmethod
    def normalize_mode(cls, value: str) -> str:
        mode = value.upper().strip()
        if mode not in {"DEMO", "REAL"}:
            raise ValueError("mode deve ser DEMO ou REAL")
        return mode

    @field_validator("broker_profile")
    @classmethod
    def validate_broker_profile(cls, value: str) -> str:
        return normalize_broker_profile(value)

    @field_validator("primary_symbol")
    @classmethod
    def validate_primary_symbol(cls, value: str) -> str:
        return normalize_primary_symbol(value)

    @field_validator("chart_timeframe")
    @classmethod
    def validate_chart_timeframe(cls, value: str) -> str:
        return normalize_timeframe_value(value)

    @field_validator("selected_symbols", mode="before")
    @classmethod
    def validate_selected_symbols(cls, value: Any) -> list[str]:
        return normalize_selected_symbols(value)

    @model_validator(mode="after")
    def normalize_symbol_setup(self) -> "UpdateRobotInstanceRequest":
        primary_symbol, selected_symbols = merge_primary_symbol(self.primary_symbol, self.selected_symbols)
        self.primary_symbol = primary_symbol
        self.selected_symbols = selected_symbols
        return self


class RobotInstanceResponse(BaseModel):
    robot_instance_id: int
    name: str
    token: str
    mode: str
    broker_profile: str
    primary_symbol: str = ""
    chart_timeframe: str = "M5"
    selected_symbols: list[str] = Field(default_factory=list)
    bridge_name: str
    discovered_symbols: list[str] = Field(default_factory=list)
    symbols_detected_at: str | None = None


class RobotInstanceStatusResponse(BaseModel):
    robot_instance_id: int
    name: str
    mode: str
    broker_profile: str = "CUSTOM"
    primary_symbol: str = ""
    chart_timeframe: str = "M5"
    selected_symbols: list[str] = Field(default_factory=list)
    bridge_name: str = "VunoBridge"
    discovered_symbols: list[str] = Field(default_factory=list)
    symbols_detected_at: str | None = None
    is_active: bool
    last_status: str | None = None
    last_heartbeat_at: str | None = None
    last_heartbeat_details: dict[str, Any] | None = None
    package_delivery_mode: str = "python"
    is_online: bool = False
    heartbeat_age_seconds: int | None = None
    runtime_pause_new_orders: bool = False
    runtime_pause_reasons: list[str] = Field(default_factory=list)
    operational_timeframe: str = "M5"
    confirmation_timeframe: str = "H1"
    performance_gate_passed: bool = True
    news_pause_active: bool = False


class InstrumentProfileResponse(BaseModel):
    profile_id: str
    label: str
    description: str
    suggested_symbols: list[str] = Field(default_factory=list)
    note: str = ""


class SnapshotCandle(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float
    tick_volume: int | None = None


class SnapshotRequest(BaseModel):
    symbol: str
    timeframe: str
    bid: float
    ask: float
    spread_points: float
    close: float
    ema_fast: float
    ema_slow: float
    rsi: float
    balance: float
    equity: float
    open_positions: int
    captured_at: str
    candles: list[SnapshotCandle] = Field(default_factory=list)
    htf_timeframe: str | None = None
    htf_candles: list[SnapshotCandle] = Field(default_factory=list)
    local_memory: dict[str, Any] | None = None
    open_position_ticket: int | None = None
    open_position_direction: str | None = None
    open_position_volume: float | None = None
    open_position_entry_price: float | None = None
    open_position_current_price: float | None = None
    open_position_stop_loss: float | None = None
    open_position_take_profit: float | None = None
    open_position_opened_at: str | None = None
    open_position_profit: float | None = None
    open_position_profit_points: float | None = None

    @field_validator("timeframe", "htf_timeframe")
    @classmethod
    def validate_snapshot_timeframes(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_timeframe_value(value)

    @field_validator("open_position_ticket", mode="before")
    @classmethod
    def normalize_position_ticket(cls, value: Any) -> int | None:
        if value in {None, "", 0, "0"}:
            return None
        try:
            ticket = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError("ticket da posicao invalido") from exc
        return ticket if ticket > 0 else None

    @field_validator("open_position_direction")
    @classmethod
    def normalize_position_direction(cls, value: str | None) -> str | None:
        if value is None:
            return None
        direction = str(value).upper().strip()
        if not direction:
            return None
        if direction not in {"BUY", "SELL"}:
            raise ValueError("direcao da posicao invalida")
        return direction


class DecisionResponse(BaseModel):
    signal: str
    confidence: float
    risk: float
    stop_loss_points: int
    take_profit_points: int
    rationale: str
    reason: str
    analysis: dict[str, Any] | None = None
    position_action: str = "NONE"
    position_ticket: int | None = None
    position_stop_loss: float | None = None
    position_take_profit: float | None = None

    @field_validator("signal")
    @classmethod
    def normalize_signal(cls, value: str) -> str:
        signal = str(value).upper().strip()
        if signal not in {"BUY", "SELL", "HOLD"}:
            raise ValueError("sinal invalido")
        return signal

    @field_validator("position_action")
    @classmethod
    def normalize_position_action(cls, value: str) -> str:
        return normalize_position_action_value(value)


class TradeFeedbackRequest(BaseModel):
    symbol: str
    outcome: str
    pnl: float
    closed_at: str
    ticket: int
    volume: float


class AgentSymbolCatalogRequest(BaseModel):
    bridge_name: str | None = Field(default=None, max_length=120)
    chart_symbol: str = Field(default="", max_length=40)
    chart_timeframe: str = Field(default="M5", min_length=2, max_length=4)
    available_symbols: list[str] = Field(default_factory=list)
    market_watch_symbols: list[str] = Field(default_factory=list)
    tracked_symbols: list[str] = Field(default_factory=list)
    exported_at: str
    account_login: int | None = None
    server: str | None = Field(default=None, max_length=120)
    company: str | None = Field(default=None, max_length=120)
    terminal_name: str | None = Field(default=None, max_length=120)

    @field_validator("chart_symbol")
    @classmethod
    def validate_chart_symbol(cls, value: str) -> str:
        return normalize_primary_symbol(value)

    @field_validator("chart_timeframe")
    @classmethod
    def validate_chart_timeframe(cls, value: str) -> str:
        return normalize_timeframe_value(value)

    @field_validator("available_symbols", "market_watch_symbols", "tracked_symbols", mode="before")
    @classmethod
    def validate_catalog_symbols(cls, value: Any) -> list[str]:
        return normalize_catalog_symbols(value)


class HeartbeatRequest(BaseModel):
    status: str = Field(default="ACTIVE", min_length=3, max_length=40)
    observed_at: str
    details: dict[str, Any] | None = None


class HeartbeatResponse(BaseModel):
    status: str
    last_heartbeat_at: str


class UserParametersPayload(BaseModel):
    risk_per_trade: float = Field(default=0.5, ge=0.0, le=1.0)
    max_spread_points: float = Field(default=30.0, ge=0.0)
    default_lot: float = Field(default=0.01, gt=0.0)
    stop_loss_points: int = Field(default=180, ge=0)
    take_profit_points: int = Field(default=360, ge=0)
    max_positions_per_symbol: int = Field(default=1, ge=1)
    reentry_cooldown_seconds: int = Field(default=60, ge=0)
    max_command_age_seconds: int = Field(default=45, ge=5)
    deviation_points: int = Field(default=20, ge=0)
    execution_retries: int = Field(default=3, ge=1, le=10)
    pause_new_orders: bool = False
    use_local_fallback: bool = True
    market_session_guard_enabled: bool = True
    decision_engine_mode: str = Field(default="HYBRID", min_length=6, max_length=20)
    operational_timeframe: str = Field(default="M5", min_length=2, max_length=4)
    confirmation_timeframe: str = Field(default="H1", min_length=2, max_length=4)
    daily_loss_limit: float = Field(default=0.0, ge=0.0, le=1000000.0)
    max_equity_drawdown_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    break_even_trigger_points: int = Field(default=8, ge=0, le=100000)
    trailing_trigger_points: int = Field(default=14, ge=0, le=100000)
    position_time_stop_minutes: int = Field(default=90, ge=0, le=10080)
    position_stagnation_window_candles: int = Field(default=6, ge=3, le=50)
    news_pause_enabled: bool = True
    news_pause_symbols: str = Field(default="*", max_length=120)
    news_pause_countries: str = Field(default="", max_length=120)
    news_pause_before_minutes: int = Field(default=30, ge=0, le=240)
    news_pause_after_minutes: int = Field(default=30, ge=0, le=240)
    news_pause_impact: str = Field(default="HIGH", min_length=3, max_length=10)
    performance_gate_enabled: bool = True
    performance_gate_min_profit_factor: float = Field(default=1.3, ge=0.0, le=99.0)
    performance_gate_min_trades: int = Field(default=100, ge=0, le=100000)
    validated_backtest_profit_factor: float = Field(default=0.0, ge=0.0, le=99.0)
    validated_backtest_trades: int = Field(default=0, ge=0, le=100000)

    @field_validator("operational_timeframe", "confirmation_timeframe")
    @classmethod
    def normalize_timeframe(cls, value: str) -> str:
        return normalize_timeframe_value(value)

    @field_validator("decision_engine_mode")
    @classmethod
    def normalize_decision_engine_mode(cls, value: str) -> str:
        return normalize_decision_engine_mode_value(value)

    @field_validator("news_pause_symbols", "news_pause_countries")
    @classmethod
    def normalize_csv_tokens(cls, value: str) -> str:
        tokens: list[str] = []
        seen: set[str] = set()
        for raw in value.split(","):
            token = raw.strip().upper()
            if not token or token in seen:
                continue
            tokens.append(token)
            seen.add(token)
        return ",".join(tokens)

    @field_validator("news_pause_impact")
    @classmethod
    def normalize_news_impact(cls, value: str) -> str:
        impact = value.upper().strip()
        if impact not in VALID_NEWS_IMPACTS:
            raise ValueError("impacto de noticia invalido")
        return impact


class UserParametersResponse(UserParametersPayload):
    tenant_id: int
    updated_at: str
    parameter_scope: str = "tenant"
    scope_robot_instance_id: int | None = None
    scope_robot_name: str | None = None
    scope_inherited: bool = False
    runtime_pause_new_orders: bool = False
    runtime_pause_reasons: list[str] = Field(default_factory=list)
    news_pause_active: bool = False
    performance_gate_passed: bool = True


class AuditEventResponse(BaseModel):
    event_id: int
    event_type: str
    payload: dict[str, Any]
    robot_instance_id: int | None = None
    robot_name: str | None = None
    user_id: int | None = None
    created_at: str


class RuntimeConfigResponse(BaseModel):
    robot_instance_id: int
    robot_name: str
    robot_mode: str
    parameters: UserParametersResponse
    runtime_pause_new_orders: bool = False
    runtime_pause_reasons: list[str] = Field(default_factory=list)
    operational_timeframe: str = "M5"
    confirmation_timeframe: str = "H1"
    news_pause_active: bool = False
    performance_gate_passed: bool = True


class OperationalSummaryResponse(BaseModel):
    tenant_id: int
    robot_instance_id: int | None = None
    decisions_total: int
    buy_signals: int
    sell_signals: int
    hold_signals: int
    results_total: int
    wins: int
    losses: int
    win_rate_pct: float
    pnl_total: float
    pnl_average: float
    profit_factor: float
    instances_total: int
    instances_online: int
    last_decision_at: str | None = None
    last_result_at: str | None = None


class LogoutResponse(BaseModel):
    status: str
