"""종목 수익률과 같은 거래일의 벤치마크 수익률을 비교한다."""

from __future__ import annotations

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Sequence

from collector.historical_events.price_reaction import (
    HORIZONS,
    calculate_trading_day_returns,
)


def _date_value(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _price_map(rows: Sequence[dict[str, Any]]) -> dict[date, Decimal]:
    result: dict[date, Decimal] = {}
    for row in rows:
        trading_date = _date_value(row.get("trading_date"))
        try:
            close = Decimal(str(row.get("close_price")))
        except Exception:
            continue
        if trading_date and close > 0:
            result[trading_date] = close
    return result


def _percent(base: Decimal, comparison: Decimal) -> float:
    value = ((comparison / base) - Decimal("1")) * Decimal("100")
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def calculate_market_adjusted_reaction(
    stock_rows: Sequence[dict[str, Any]],
    benchmark_rows: Sequence[dict[str, Any]],
    *,
    event_date: date,
    representative_published_at: str | None,
) -> dict[str, Any]:
    """종목과 벤치마크를 동일한 기준일·비교일에 맞춰 계산한다.

    비정상수익률은 MVP에서 시장조정 수익률
    ``stock return - benchmark return``으로 정의한다. 회귀형 시장모형은
    충분한 사전 추정구간이 확보되는 연구 단계에서 별도 버전으로 추가한다.
    """

    stock = calculate_trading_day_returns(
        stock_rows,
        event_date=event_date,
        representative_published_at=representative_published_at,
    )
    benchmark_prices = _price_map(benchmark_rows)
    base_date = _date_value(stock.get("baseDate"))
    benchmark_base = benchmark_prices.get(base_date) if base_date else None

    benchmark_returns: dict[str, float | None] = {}
    abnormal_returns: dict[str, float | None] = {}
    for horizon in HORIZONS:
        key = f"d{horizon}"
        comparison_date = _date_value(stock["comparisonDates"].get(key))
        comparison = (
            benchmark_prices.get(comparison_date) if comparison_date else None
        )
        if benchmark_base is None or comparison is None:
            benchmark_return = None
        else:
            benchmark_return = _percent(benchmark_base, comparison)
        benchmark_returns[key] = benchmark_return

        stock_return = stock["returns"].get(key)
        abnormal_returns[key] = (
            round(float(stock_return) - benchmark_return, 2)
            if stock_return is not None and benchmark_return is not None
            else None
        )

    benchmark_complete = all(
        value is not None for value in benchmark_returns.values()
    )
    return {
        **stock,
        "benchmarkCode": "KOSPI",
        "benchmarkReturns": benchmark_returns,
        "abnormalReturns": abnormal_returns,
        "benchmarkStatus": (
            "complete"
            if benchmark_complete
            else "partial" if benchmark_prices else "unavailable"
        ),
        "abnormalReturnMethod": "market-adjusted-v1",
    }
