"""설명 가능한 ESG 다중 라벨 기준선.

이 분류는 사건의 ESG 관련성을 나타낸다. 주가 하락 확률이나 Pedersen 논문의
기업 ESG 점수와는 의도적으로 분리한다.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Mapping, Sequence


ESG_TAXONOMY_VERSION = "stockecho-esg-event-v1"

_RULES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("E", "climate_emissions", ("온실가스", "탄소배출", "탄소 배출", "기후변화", "배출권")),
    ("E", "pollution_waste", ("오염", "폐수", "폐기물", "유해물질", "환경 훼손")),
    ("E", "resources_biodiversity", ("산림", "생물다양성", "수자원", "자원 고갈")),
    ("S", "labor_human_rights", ("산재", "사망사고", "노동권", "인권", "강제노동", "직장 내 괴롭힘", "파업")),
    ("S", "product_customer_safety", ("리콜", "제품 결함", "안전성", "식중독", "고객 피해")),
    ("S", "privacy_cybersecurity", ("개인정보", "정보 유출", "데이터 유출", "해킹", "랜섬웨어")),
    ("S", "community_supply_chain", ("지역사회", "협력사 갑질", "공급망 인권", "하도급")),
    ("G", "board_control", ("이사회", "사외이사", "내부통제", "경영권", "승계")),
    ("G", "accounting_disclosure", ("회계 부정", "분식회계", "감사의견", "공시 위반", "허위 공시")),
    ("G", "bribery_compliance", ("횡령", "배임", "뇌물", "부패", "담합", "과징금", "제재")),
    ("G", "shareholder_rights", ("주주권", "소액주주", "자사주", "주주환원", "불공정 합병")),
)


def _event_text(event: Mapping[str, Any]) -> str:
    values = [
        str(event.get("name") or ""),
        str(event.get("summary") or ""),
        *[str(value) for value in event.get("keywords") or []],
    ]
    for article in event.get("articles") or []:
        if not isinstance(article, Mapping):
            continue
        values.extend(
            [
                str(article.get("title") or ""),
                str(article.get("summary") or ""),
            ]
        )
    return " ".join(values).casefold()


def classify_esg_event(
    event: Mapping[str, Any],
    *,
    minimum_matches: int = 1,
    maximum_labels: int = 4,
) -> dict[str, Any]:
    """근거 용어와 함께 ESG 관련 사건을 다중 라벨로 분류한다."""

    if minimum_matches < 1:
        raise ValueError("minimum_matches는 1 이상이어야 합니다.")
    if maximum_labels < 1:
        raise ValueError("maximum_labels는 1 이상이어야 합니다.")

    text = _event_text(event)
    matched: dict[tuple[str, str], set[str]] = defaultdict(set)
    for dimension, subtype, terms in _RULES:
        for term in terms:
            if term.casefold() in text:
                matched[(dimension, subtype)].add(term)

    labels = [
        {
            "dimension": dimension,
            "subtype": subtype,
            "score": round(min(0.55 + 0.15 * len(terms), 1.0), 4),
            "evidence_terms": sorted(terms),
        }
        for (dimension, subtype), terms in matched.items()
        if len(terms) >= minimum_matches
    ]
    labels.sort(
        key=lambda label: (
            -float(label["score"]),
            str(label["dimension"]),
            str(label["subtype"]),
        )
    )
    labels = labels[:maximum_labels]
    dimensions = sorted({str(label["dimension"]) for label in labels})
    return {
        "taxonomy_version": ESG_TAXONOMY_VERSION,
        "is_esg_related": bool(labels),
        "dimensions": dimensions,
        "labels": labels,
        "classification_method": "explainable-keyword-baseline",
        "disclaimer": (
            "사건의 ESG 관련성 분류이며 기업 ESG 점수나 주가 방향 예측이 아닙니다."
        ),
    }


def supported_esg_labels() -> Sequence[tuple[str, str]]:
    return tuple((dimension, subtype) for dimension, subtype, _terms in _RULES)
