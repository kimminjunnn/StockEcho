"""시간·종목·사건유형 기준의 재현 가능한 검증 분할."""

from __future__ import annotations

from datetime import date
from typing import Any, Mapping, Sequence


def walk_forward_splits(
    rows: Sequence[Mapping[str, Any]],
    *,
    minimum_train_events: int,
    validation_events: int,
    test_events: int,
    step_events: int | None = None,
) -> list[dict[str, list[dict[str, Any]]]]:
    if min(minimum_train_events, validation_events, test_events) < 1:
        raise ValueError("각 분할 크기는 1 이상이어야 합니다.")
    step = step_events or test_events
    if step < 1:
        raise ValueError("step_events는 1 이상이어야 합니다.")
    ordered = sorted(
        (dict(row) for row in rows),
        key=lambda row: (str(row["event_date"]), str(row["event_id"])),
    )
    result = []
    train_end = minimum_train_events
    while train_end + validation_events + test_events <= len(ordered):
        validation_end = train_end + validation_events
        test_end = validation_end + test_events
        split = {
            "train": ordered[:train_end],
            "validation": ordered[train_end:validation_end],
            "test": ordered[validation_end:test_end],
        }
        if date.fromisoformat(str(split["train"][-1]["event_date"])) >= date.fromisoformat(
            str(split["validation"][0]["event_date"])
        ):
            raise ValueError("동일 날짜 Event가 train/validation 경계를 넘습니다.")
        if date.fromisoformat(str(split["validation"][-1]["event_date"])) >= date.fromisoformat(
            str(split["test"][0]["event_date"])
        ):
            raise ValueError("동일 날짜 Event가 validation/test 경계를 넘습니다.")
        result.append(split)
        train_end += step
    return result


def leave_one_group_out_splits(
    rows: Sequence[Mapping[str, Any]],
    *,
    group_key: str,
    minimum_test_events: int = 1,
) -> list[dict[str, Any]]:
    groups = sorted({str(row.get(group_key) or "unknown") for row in rows})
    results = []
    for group in groups:
        test = [dict(row) for row in rows if str(row.get(group_key) or "unknown") == group]
        train = [dict(row) for row in rows if str(row.get(group_key) or "unknown") != group]
        if len(test) < minimum_test_events or not train:
            continue
        results.append({"held_out_group": group, "train": train, "test": test})
    return results
