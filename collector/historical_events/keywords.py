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
SEARCH_NOISE = (STOPWORDS - {"공개", "발표"}) | {
    "개월",
    "연속",
    "최초",
    "기록",
    "달러",
    "전용",
}
EVENT_TERMS = {
    "가격",
    "개발",
    "경쟁",
    "계약",
    "공급",
    "공모",
    "공장",
    "공개",
    "관리",
    "교섭",
    "규제",
    "기술",
    "노사",
    "노조",
    "리콜",
    "매각",
    "매출",
    "발행",
    "발표",
    "법인",
    "분쟁",
    "생산",
    "서비스",
    "성과급",
    "소송",
    "수요",
    "수주",
    "승인",
    "실적",
    "양산",
    "업황",
    "인수",
    "임금",
    "점유",
    "점유율",
    "정책",
    "증자",
    "채권",
    "치료제",
    "출시",
    "투자",
    "파업",
    "합병",
    "협력",
    "협상",
    "화재",
}


def _company_tokens(company_name: str) -> set[str]:
    normalized_name = "".join(TOKEN_PATTERN.findall(company_name.casefold()))
    tokens = {
        token.casefold() for token in TOKEN_PATTERN.findall(company_name)
    }
    # 기사 키프레이즈가 "한화 에어로스페이스"처럼 회사명을 띄어 쓰는 경우도
    # 제거할 수 있도록, 두 글자 이상의 회사명 부분 문자열도 아래 호출부에서
    # 판별한다.
    if normalized_name:
        tokens.add(normalized_name)
    return tokens


def _is_company_token(token: str, company_tokens: set[str]) -> bool:
    return token in company_tokens or any(
        len(token) >= 2 and token in company_token
        for company_token in company_tokens
    )


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

    company_tokens = _company_tokens(company_name)
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
                or _is_company_token(normalized, company_tokens)
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
    """여러 키프레이즈에서 반복되는 사건어를 NAVER 질의로 선택한다.

    첫 키프레이즈만 사용하면 회사·제품 고유명사가 질의를 독점해 과거의 같은
    유형 사건을 찾지 못한다. 문서 빈도와 사건어 사전을 함께 사용하되, 원문에
    실제 등장한 토큰만 반환한다.
    """

    if limit < 1:
        raise ValueError("limit은 1 이상이어야 합니다.")

    company_tokens = _company_tokens(company_name)
    document_counts: Counter[str] = Counter()
    total_counts: Counter[str] = Counter()
    first_seen: dict[str, int] = {}
    position = 0

    for phrase in keywords:
        phrase_tokens: list[str] = []
        for token in TOKEN_PATTERN.findall(phrase or ""):
            normalized = token.casefold()
            if (
                len(normalized) < 2
                or normalized in SEARCH_NOISE
                or _is_company_token(normalized, company_tokens)
                or any(character.isdigit() for character in normalized)
            ):
                continue
            phrase_tokens.append(normalized)
            first_seen.setdefault(normalized, position)
            position += 1
        document_counts.update(set(phrase_tokens))
        total_counts.update(phrase_tokens)

    # 제목·Topic에서만 살아남은 핵심 사건어도 후보에 넣는다. 키프레이즈에
    # 반복 등장한 단어보다 높은 점수를 받지는 않도록 빈도는 약하게 부여한다.
    for token in core_keywords:
        normalized = token.casefold().strip()
        if (
            len(normalized) < 2
            or normalized in SEARCH_NOISE
            or _is_company_token(normalized, company_tokens)
            or any(character.isdigit() for character in normalized)
        ):
            continue
        first_seen.setdefault(normalized, position)
        position += 1
        total_counts[normalized] += 1

    ordered = sorted(
        total_counts,
        key=lambda token: (
            -(8 if token in EVENT_TERMS else 0),
            -document_counts[token],
            -total_counts[token],
            first_seen[token],
            -len(token),
            token,
        ),
    )
    selected: list[str] = []
    for token in ordered:
        # "점유"와 "점유율"처럼 같은 어근을 중복 선택하면 2개 일치 규칙을
        # 사실상 한 단어 일치로 약화한다. 더 구체적인 긴 토큰을 남긴다.
        overlapping_index = next(
            (
                index
                for index, selected_token in enumerate(selected)
                if token in selected_token or selected_token in token
            ),
            None,
        )
        if overlapping_index is not None:
            if len(token) > len(selected[overlapping_index]):
                selected[overlapping_index] = token
            continue
        selected.append(token)
        if len(selected) == limit:
            break
    return selected
