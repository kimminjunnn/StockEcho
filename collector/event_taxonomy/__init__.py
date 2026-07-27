"""일반 사건 유형과 분리된 ESG 사건 taxonomy."""

from collector.event_taxonomy.classifier import (
    ESG_TAXONOMY_VERSION,
    classify_esg_event,
)

__all__ = ["ESG_TAXONOMY_VERSION", "classify_esg_event"]
