"""저장 Event에 설명 가능한 ESG 다중 라벨을 기록한다."""

from __future__ import annotations

import argparse
import json

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from collector.event_taxonomy import classify_esg_event
from collector.repositories.supabase import connect


def backfill(*, only_missing: bool = True) -> dict[str, int]:
    with connect() as connection:
        with connection.cursor(row_factory=dict_row) as cursor:
            cursor.execute(
                """
                select event_id, name, keywords, representative_article, articles
                from public.historical_events
                where (%s = false or esg_classification is null)
                order by event_id
                """,
                (only_missing,),
            )
            events = list(cursor.fetchall())
        related = 0
        with connection.cursor() as cursor:
            for event in events:
                classification = classify_esg_event(event)
                related += int(classification["is_esg_related"])
                cursor.execute(
                    """
                    update public.historical_events
                    set esg_classification = %s, updated_at = now()
                    where event_id = %s
                    """,
                    (Jsonb(classification), event["event_id"]),
                )
        connection.commit()
    return {"updated": len(events), "esgRelated": related}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    print(json.dumps(backfill(only_missing=not args.all), ensure_ascii=False))


if __name__ == "__main__":
    main()
