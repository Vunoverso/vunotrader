from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib import error
from urllib.request import Request, urlopen


CALENDAR_CACHE_LOCK = threading.Lock()
CALENDAR_CACHE: dict[str, object] = {
    "fetched_at": 0.0,
    "events": [],
    "error": None,
}

IMPACT_SCORES = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
SYMBOL_COUNTRY_OVERRIDES = {
    "XAUUSD": {"USD"},
    "US30": {"USD"},
    "NAS100": {"USD"},
    "SPX500": {"USD"},
    "GER40": {"EUR"},
    "UK100": {"GBP"},
}
KNOWN_CURRENCIES = {"USD", "EUR", "GBP", "JPY", "AUD", "NZD", "CAD", "CHF"}


def parse_csv(value: str | None) -> list[str]:
    if not value:
        return []

    seen: set[str] = set()
    payload: list[str] = []
    for raw in str(value).split(","):
        token = raw.strip().upper()
        if not token or token in seen:
            continue
        payload.append(token)
        seen.add(token)
    return payload


def _get_calendar_url() -> str:
    return os.getenv("ECONOMIC_CALENDAR_URL", "https://nfs.faireconomy.media/ff_calendar_thisweek.json").strip()


def _get_cache_seconds() -> int:
    try:
        return max(30, int(os.getenv("ECONOMIC_CALENDAR_CACHE_SECONDS", "900")))
    except ValueError:
        return 900


def _get_timeout_seconds() -> float:
    try:
        return max(1.0, float(os.getenv("ECONOMIC_CALENDAR_TIMEOUT_SECONDS", "8")))
    except ValueError:
        return 8.0


def _impact_score(value: str) -> int:
    return IMPACT_SCORES.get(value.upper().strip(), 0)


def _parse_event_datetime(raw: str) -> datetime | None:
    value = str(raw or "").strip()
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _normalize_event(item: object) -> dict[str, object] | None:
    if not isinstance(item, dict):
        return None

    event_at = _parse_event_datetime(str(item.get("date", "")))
    if event_at is None:
        return None

    title = str(item.get("title", "")).strip()
    country = str(item.get("country", "")).strip().upper()
    impact = str(item.get("impact", "")).strip().upper()
    if not title or not country or impact not in IMPACT_SCORES:
        return None

    return {
        "title": title,
        "country": country,
        "impact": impact,
        "date": event_at,
        "forecast": str(item.get("forecast", "")).strip(),
        "previous": str(item.get("previous", "")).strip(),
    }


def get_calendar_events(force: bool = False) -> tuple[list[dict[str, object]], str | None]:
    now_ts = time.time()

    with CALENDAR_CACHE_LOCK:
        cached_age = now_ts - float(CALENDAR_CACHE.get("fetched_at", 0.0) or 0.0)
        cached_events = list(CALENDAR_CACHE.get("events", []))
        cached_error = CALENDAR_CACHE.get("error")
        if not force and cached_events and cached_age < _get_cache_seconds():
            return cached_events, str(cached_error) if cached_error else None

    url = _get_calendar_url()
    request = Request(
        url,
        headers={
            "User-Agent": os.getenv("ECONOMIC_CALENDAR_USER_AGENT", "Mozilla/5.0"),
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=_get_timeout_seconds()) as response:
            payload = json.loads(response.read().decode("utf-8"))
        normalized = [event for item in payload for event in [_normalize_event(item)] if event is not None]
        error_message = None
    except (json.JSONDecodeError, error.HTTPError, error.URLError, TimeoutError) as exc:
        normalized = cached_events
        error_message = f"feed_indisponivel: {exc}"

    with CALENDAR_CACHE_LOCK:
        CALENDAR_CACHE["fetched_at"] = now_ts
        CALENDAR_CACHE["events"] = normalized
        CALENDAR_CACHE["error"] = error_message

    return normalized, error_message


def derive_countries_for_symbol(symbol: str, configured_countries: str | None = None) -> list[str]:
    configured = parse_csv(configured_countries)
    if configured:
        return configured

    normalized_symbol = str(symbol or "").strip().upper()
    if not normalized_symbol:
        return []

    if normalized_symbol in SYMBOL_COUNTRY_OVERRIDES:
        return sorted(SYMBOL_COUNTRY_OVERRIDES[normalized_symbol])

    candidates = set()
    if len(normalized_symbol) >= 6:
        for code in (normalized_symbol[:3], normalized_symbol[-3:]):
            if code in KNOWN_CURRENCIES:
                candidates.add(code)
    return sorted(candidates)


def active_news_events_for_symbol(
    symbol: str,
    configured_countries: str | None,
    minimum_impact: str,
    before_minutes: int,
    after_minutes: int,
    observed_at: datetime | None = None,
) -> dict[str, object]:
    events, error_message = get_calendar_events()
    current_time = observed_at or datetime.now(timezone.utc)
    countries = set(derive_countries_for_symbol(symbol, configured_countries))
    minimum_score = _impact_score(minimum_impact)

    active_events: list[dict[str, object]] = []
    for event in events:
        country = str(event["country"])
        if countries and country not in countries:
            continue
        if _impact_score(str(event["impact"])) < minimum_score:
            continue

        event_time = event["date"]
        if not isinstance(event_time, datetime):
            continue
        window_start = event_time - timedelta(minutes=before_minutes)
        window_end = event_time + timedelta(minutes=after_minutes)
        if window_start <= current_time <= window_end:
            active_events.append(
                {
                    "symbol": symbol.upper().strip(),
                    "title": str(event["title"]),
                    "country": country,
                    "impact": str(event["impact"]),
                    "date": event_time.isoformat(),
                }
            )

    return {
        "events": active_events,
        "countries": sorted(countries),
        "error": error_message,
    }