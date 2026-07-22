"""Supabase Queue의 종목 분석 작업을 처리한다."""

from __future__ import annotations

import argparse
import json
import sys
import time

from collector.jobs.analyze_companies import analyze_existing_company
from collector.repositories.supabase import QUEUE_NAME, connect, sync_stock_snapshot


def process_one(*, visibility_timeout: int, device: str | None) -> bool:
    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                "select msg_id, read_ct, message from pgmq.read(%s, %s, 1)",
                (QUEUE_NAME, visibility_timeout),
            )
            message = cursor.fetchone()
            if not message:
                connection.commit()
                return False
            message_id, read_count, payload = message
            if isinstance(payload, str):
                payload = json.loads(payload)
            stock_code = payload["stock_code"]
            cursor.execute(
                """
                update public.stock_analysis_state
                set status = 'running', retry_count = %s, updated_at = now()
                where stock_code = %s
                """,
                (max(int(read_count) - 1, 0), stock_code),
            )
        connection.commit()

    try:
        analyze_existing_company(stock_code=stock_code, device=device)
        sync_stock_snapshot(stock_code)
    except Exception as error:
        with connect() as connection:
            with connection.cursor() as cursor:
                if int(read_count) >= 3:
                    cursor.execute("select pgmq.archive(%s, %s)", (QUEUE_NAME, message_id))
                cursor.execute(
                    """
                    update public.stock_analysis_state
                    set status = 'failed', retry_count = %s,
                        error_message = %s, updated_at = now()
                    where stock_code = %s
                    """,
                    (int(read_count), str(error)[:1000], stock_code),
                )
            connection.commit()
        raise

    with connect() as connection:
        with connection.cursor() as cursor:
            cursor.execute("select pgmq.archive(%s, %s)", (QUEUE_NAME, message_id))
        connection.commit()
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--visibility-timeout", type=int, default=3600)
    parser.add_argument("--poll-interval", type=float, default=5.0)
    parser.add_argument("--device")
    args = parser.parse_args()
    while True:
        try:
            processed = process_one(
                visibility_timeout=args.visibility_timeout,
                device=args.device,
            )
        except Exception as error:
            print(
                json.dumps(
                    {"worker_error": type(error).__name__, "message": str(error)},
                    ensure_ascii=False,
                ),
                file=sys.stderr,
            )
            processed = True
        if args.once:
            break
        if not processed:
            time.sleep(max(args.poll_interval, 0.1))


if __name__ == "__main__":
    main()
