"""현재 주요 Event에서 NAVER 검색과 유사도 비교에 쓸 핵심어를 고른다."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Sequence


TOKEN_PATTERN = re.compile(r"[가-힣a-z0-9]+", re.IGNORECASE)
STOPWORDS = {
    "관련",
    "사업",
    "시장",
    "기업",
    "회사",
    "전망",
    "확대",
    "본격화",
    "공개",
    "발표",
    "추진",
    "대응",
    "대한",
    "통해",
    "위한",
    "이번",
}


def extract_core_keywords(
    *,
    name: str,
    topic_label: str,
    keywords: Sequence[str],
    company_name: str,
    limit: int = 6,
) -> list[str]:
    """제목·Topic·키프레이즈에서 설명력 있는 토큰을 결정적으로 선택한다."""

    if limit < 1:
        raise ValueError("limit은 1 이상이어야 합니다.")

    company_tokens = {
        token.casefold() for token in TOKEN_PATTERN.findall(company_name)
    }
    weighted_values = [
        (name, 4),
        (topic_label, 3),
        *((keyword, 2) for keyword in keywords),
    ]
    scores: Counter[str] = Counter()
    first_seen: dict[str, int] = {}
    position = 0
    for value, weight in weighted_values:
        for token in TOKEN_PATTERN.findall(value or ""):
            normalized = token.casefold()
            if (
                len(normalized) < 2
                or normalized in STOPWORDS
                or normalized in company_tokens
                or any(character.isdigit() for character in normalized)
            ):
                continue
            scores[normalized] += weight
            first_seen.setdefault(normalized, position)
            position += 1

    ordered = sorted(
        scores,
        key=lambda token: (-scores[token], first_seen[token], -len(token), token),
    )
    return ordered[:limit]


def extract_search_keywords(
    *,
    keywords: Sequence[str],
    core_keywords: Sequence[str],
    company_name: str,
    limit: int = 3,
) -> list[str]:
    """NAVER 질의는 대표 키프레이즈 하나의 2~3개 사건어로 좁힌다."""

    company_tokens = {
        token.casefold() for token in TOKEN_PATTERN.findall(company_name)
    }
    for phrase in keywords:
        selected: list[str] = []
        for token in TOKEN_PATTERN.findall(phrase or ""):
            normalized = token.casefold()
            if (
                len(normalized) < 2
                or normalized in STOPWORDS
                or normalized in company_tokens
                or any(character.isdigit() for character in normalized)
                or normalized in selected
            ):
                continue
            selected.append(normalized)
            if len(selected) == limit:
                break
        if len(selected) >= 2:
            return selected
    return list(core_keywords[:limit])
