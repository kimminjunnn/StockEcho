"""현재 이슈와 키워드가 겹치는 과거 Event 검색."""

from collector.historical_events.search import (
    load_topic_records,
    search_historical_events,
)

__all__ = ["load_topic_records", "search_historical_events"]
