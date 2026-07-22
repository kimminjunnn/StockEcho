"""Supabase 스키마를 적용하고 현재 로컬 분석 snapshot을 이전한다."""

from __future__ import annotations

import argparse
import json

from collector.repositories.supabase import apply_migrations, sync_stock_snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-code", action="append", default=[])
    args = parser.parse_args()
    apply_migrations()
    synced = [sync_stock_snapshot(code) for code in dict.fromkeys(args.stock_code)]
    print(json.dumps({"schema": "ready", "synced": [row["stockCode"] for row in synced]}))


if __name__ == "__main__":
    main()
