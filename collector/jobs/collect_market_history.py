"""지원 종목 수정주가 OHLCV와 KOSPI 벤치마크를 기간별 수집한다."""

from __future__ import annotations

import argparse
import json
import time
from datetime import date, timedelta
from typing import Any, Iterator, Sequence

from collector.clients.kis import KisApiError, load_kis_client
from collector.companies import SUPPORTED_COMPANIES, get_company
from collector.repositories.supabase import connect, upsert_supported_stocks


def _windows(
    start_date: date,
    end_date: date,
    *,
    calendar_days: int = 90,
) -> Iterator[tuple[date, date]]:
    cursor = start_date
    while cursor <= end_date:
        window_end = min(cursor + timedelta(days=calendar_days - 1), end_date)
        yield cursor, window_end
        cursor = window_end + timedelta(days=1)


def _upsert_stock_rows(
    connection,
    *,
    stock_code: str,
    rows: Sequence[dict[str, Any]],
) -> None:
    if not rows:
        return
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into public.market_daily (
              stock_code, trading_date, open_price, high_price, low_price,
              close_price, volume, adjusted, source, fetched_at
            ) values (%s, %s, %s, %s, %s, %s, %s, %s, 'KIS', now())
            on conflict (stock_code, trading_date) do update set
              open_price = excluded.open_price,
              high_price = excluded.high_price,
              low_price = excluded.low_price,
              close_price = excluded.close_price,
              volume = excluded.volume,
              adjusted = excluded.adjusted,
              source = excluded.source,
              fetched_at = now()
            """,
            [
                (
                    stock_code,
                    row["trading_date"],
                    row.get("open_price"),
                    row.get("high_price"),
                    row.get("low_price"),
                    row["close_price"],
                    row.get("volume"),
                    bool(row.get("adjusted", True)),
                )
                for row in rows
            ],
        )


def _upsert_index_rows(
    connection,
    *,
    rows: Sequence[dict[str, Any]],
) -> None:
    if not rows:
        return
    with connection.cursor() as cursor:
        cursor.executemany(
            """
            insert into public.market_index_daily (
              index_code, trading_date, open_price, high_price, low_price,
              close_price, volume, source, fetched_at
            ) values ('KOSPI', %s, %s, %s, %s, %s, %s, 'KIS', now())
            on conflict (index_code, trading_date) do update set
              open_price = excluded.open_price,
              high_price = excluded.high_price,
              low_price = excluded.low_price,
              close_price = excluded.close_price,
              volume = excluded.volume,
              source = excluded.source,
              fetched_at = now()
            """,
            [
                (
                    row["trading_date"],
                    row.get("open_price"),
                    row.get("high_price"),
                    row.get("low_price"),
                    row["close_price"],
                    row.get("volume"),
                )
                for row in rows
            ],
        )


def collect_market_history(
    *,
    stock_codes: Sequence[str],
    start_date: date,
    end_date: date,
    request_interval: float = 1.1,
    collect_stocks: bool = True,
) -> dict[str, Any]:
    if start_date > end_date:
        raise ValueError("start_date는 end_date보다 늦을 수 없습니다.")
    codes = list(dict.fromkeys(stock_codes))
    for code in codes:
        get_company(code)

    client = load_kis_client()
    stock_counts: dict[str, int] = {}
    failures: list[dict[str, str]] = []
    with connect() as connection:
        upsert_supported_stocks(connection)
        for code in codes if collect_stocks else []:
            unique: dict[date, dict[str, Any]] = {}
            for window_start, window_end in _windows(start_date, end_date):
                try:
                    window_rows = client.daily_prices(
                        code,
                        start_date=window_start,
                        end_date=window_end,
                    )
                except KisApiError as error:
                    failures.append(
                        {
                            "asset": code,
                            "start": window_start.isoformat(),
                            "end": window_end.isoformat(),
                            "error": str(error),
                        }
                    )
                    continue
                for row in window_rows:
                    unique[row["trading_date"]] = row
                _upsert_stock_rows(
                    connection,
                    stock_code=code,
                    rows=window_rows,
                )
                connection.commit()
                time.sleep(max(request_interval, 0))
            rows = [unique[key] for key in sorted(unique)]
            stock_counts[code] = len(rows)

        benchmark: dict[date, dict[str, Any]] = {}
        # 지수 endpoint는 한 요청에서 약 50개 행만 반환하므로 60 calendar day
        # 이하로 잘라 거래일 누락을 방지한다.
        for window_start, window_end in _windows(
            start_date,
            end_date,
            calendar_days=60,
        ):
            try:
                window_rows = client.daily_index_prices(
                    index_code="0001",
                    start_date=window_start,
                    end_date=window_end,
                )
            except KisApiError as error:
                failures.append(
                    {
                        "asset": "KOSPI",
                        "start": window_start.isoformat(),
                        "end": window_end.isoformat(),
                        "error": str(error),
                    }
                )
                continue
            for row in window_rows:
                benchmark[row["trading_date"]] = row
            _upsert_index_rows(connection, rows=window_rows)
            connection.commit()
            time.sleep(max(request_interval, 0))
        benchmark_rows = [benchmark[key] for key in sorted(benchmark)]
    return {
        "startDate": start_date.isoformat(),
        "endDate": end_date.isoformat(),
        "stockRows": stock_counts,
        "benchmarkRows": len(benchmark_rows),
        "failureCount": len(failures),
        "failures": failures,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--stock-code", action="append")
    selection.add_argument("--all-supported", action="store_true")
    selection.add_argument("--benchmark-only", action="store_true")
    parser.add_argument("--start", type=date.fromisoformat, required=True)
    parser.add_argument("--end", type=date.fromisoformat, required=True)
    parser.add_argument("--request-interval", type=float, default=1.1)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stock_codes = (
        [company.stock_code for company in SUPPORTED_COMPANIES]
        if args.all_supported
        else args.stock_code or []
    )
    print(
        json.dumps(
            collect_market_history(
                stock_codes=stock_codes,
                start_date=args.start,
                end_date=args.end,
                request_interval=args.request_interval,
                collect_stocks=not args.benchmark_only,
            ),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
