"""과거 Event 이후 거래일 기준 D+1·D+5·D+15·D+30 수익률."""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Sequence
from zoneinfo import ZoneInfo


KST = ZoneInfo("Asia/Seoul")
MARKET_CLOSE_CUTOFF = time(15, 20)
HORIZONS = (1, 5, 15, 30)


def _published_before_close(value: str | None, event_date: date) -> bool:
    if not value:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    local = parsed.astimezone(KST)
    return local.date() == event_date and local.time() < MARKET_CLOSE_CUTOFF


def _return_percent(base: Decimal, comparison: Decimal) -> float:
    value = ((comparison / base) - Decimal("1")) * Decimal("100")
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculate_trading_day_returns(
    rows: Sequence[dict[str, Any]],
    *,
    event_date: date,
    representative_published_at: str | None,
) -> dict[str, Any]:
    """휴일·거래정지로 비어 있는 달력일을 건너뛰어 거래일 순번으로 계산한다."""

    prices_by_date: dict[date, Decimal] = {}
    for row in rows:
        trading_date = row.get("trading_date")
        if isinstance(trading_date, str):
            trading_date = date.fromisoformat(trading_date)
        try:
            close_price = Decimal(str(row.get("close_price")))
        except Exception:
            continue
        if not isinstance(trading_date, date) or close_price <= 0:
            continue
        prices_by_date[trading_date] = close_price
    normalized = sorted(prices_by_date.items(), key=lambda value: value[0])

    use_event_day = _published_before_close(
        representative_published_at, event_date
    )
    base_index = next(
        (
            index
            for index, (trading_date, _close) in enumerate(normalized)
            if (
                trading_date >= event_date
                if use_event_day
                else trading_date > event_date
            )
        ),
        None,
    )
    if base_index is None:
        return {
            "status": "unavailable",
            "reason": "Event 이후 기준 거래일 가격이 없습니다.",
            "baseDate": None,
            "baseClose": None,
            "returns": {f"d{horizon}": None for horizon in HORIZONS},
            "comparisonDates": {f"d{horizon}": None for horizon in HORIZONS},
        }

    base_date, base_close = normalized[base_index]
    returns: dict[str, float | None] = {}
    comparison_dates: dict[str, str | None] = {}
    for horizon in HORIZONS:
        comparison_index = base_index + horizon
        key = f"d{horizon}"
        if comparison_index >= len(normalized):
            returns[key] = None
            comparison_dates[key] = None
            continue
        comparison_date, comparison_close = normalized[comparison_index]
        returns[key] = _return_percent(base_close, comparison_close)
        comparison_dates[key] = comparison_date.isoformat()

    complete = all(value is not None for value in returns.values())
    return {
        "status": "complete" if complete else "partial",
        "reason": (
            None
            if complete
            else "아직 도달하지 않았거나 가격이 누락된 거래일 구간이 있습니다."
        ),
        "baseDate": base_date.isoformat(),
        "baseClose": float(base_close),
        "returns": returns,
        "comparisonDates": comparison_dates,
        "baselinePolicy": (
            "장 마감 전 보도이므로 Event 당일 종가를 기준가로 사용"
            if use_event_day and base_date == event_date
            else "휴일·장 마감 후·시각 불확실 보도는 다음 거래일 종가를 기준가로 사용"
        ),
    }
