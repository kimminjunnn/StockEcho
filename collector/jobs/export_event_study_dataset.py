"""Supabase Event·가격을 버전 Event Study Parquet로 export한다."""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from psycopg.rows import dict_row

from collector.event_study.dataset import (
    DATASET_SCHEMA_VERSION,
    build_event_study_rows,
    dataset_hash,
    temporal_split,
)
from collector.repositories.local import write_json_atomic, write_jsonl_atomic
from collector.repositories.supabase import PROJECT_ROOT, connect


def _load_inputs(connection) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], list[dict[str, Any]]]:
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(
            """
            select event_id, stock_code, topic_id, event_date, name,
                   event_category, impact_direction, article_count,
                   source_count, representative_article, articles,
                   feature_cutoff_at
            from public.historical_events
            order by event_date, event_id
            """
        )
        events = list(cursor.fetchall())
        cursor.execute(
            """
            select stock_code, trading_date, close_price
            from public.market_daily
            order by stock_code, trading_date
            """
        )
        market_rows = list(cursor.fetchall())
        cursor.execute(
            """
            select trading_date, close_price
            from public.market_index_daily
            where index_code = 'KOSPI'
            order by trading_date
            """
        )
        benchmark_rows = list(cursor.fetchall())

    stock_prices: dict[str, list[dict[str, Any]]] = {}
    for row in market_rows:
        stock_prices.setdefault(str(row["stock_code"]), []).append(row)
    return events, stock_prices, benchmark_rows


def export_dataset(
    *,
    output_dir: Path,
    train_end: date,
    validation_end: date,
) -> dict[str, Any]:
    with connect() as connection:
        events, stock_prices, benchmark_prices = _load_inputs(connection)
    rows = build_event_study_rows(
        events,
        stock_prices=stock_prices,
        benchmark_prices=benchmark_prices,
    )
    split_rows = temporal_split(
        rows,
        train_end=train_end,
        validation_end=validation_end,
    )
    flattened = [
        row
        for split_name in ("train", "validation", "test")
        for row in split_rows[split_name]
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = output_dir / "events.jsonl"
    parquet_path = output_dir / "events.parquet"
    manifest_path = output_dir / "manifest.json"
    write_jsonl_atomic(jsonl_path, flattened)

    try:
        import pandas as pd
    except ImportError as error:
        raise RuntimeError(
            "Parquet export에는 pandas와 pyarrow가 필요합니다."
        ) from error
    pd.DataFrame(flattened).to_parquet(parquet_path, index=False)

    digest = dataset_hash(flattened)
    manifest = {
        "datasetSchemaVersion": DATASET_SCHEMA_VERSION,
        "datasetHash": digest,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "trainEnd": train_end.isoformat(),
        "validationEnd": validation_end.isoformat(),
        "rowCount": len(flattened),
        "splitCounts": {
            split: len(values) for split, values in split_rows.items()
        },
        "files": {
            "jsonl": jsonl_path.name,
            "parquet": parquet_path.name,
        },
    }
    write_json_atomic(manifest_path, manifest)
    return manifest


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "data" / "features" / DATASET_SCHEMA_VERSION,
    )
    parser.add_argument("--train-end", type=date.fromisoformat, required=True)
    parser.add_argument(
        "--validation-end", type=date.fromisoformat, required=True
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    print(
        json.dumps(
            export_dataset(
                output_dir=args.output_dir,
                train_end=args.train_end,
                validation_end=args.validation_end,
            ),
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
