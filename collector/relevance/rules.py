"""모든 지원 종목에 공통 적용하는 설명 가능한 기사 관련도 v2 규칙."""

from __future__ import annotations

import re

from collector.companies import Company, SUPPORTED_COMPANIES
from collector.models.news import NormalizedNewsArticle, RelevanceResult


RULE_VERSION = "relevance-v2"
ELIGIBLE_THRESHOLD = 0.65
CANDIDATE_THRESHOLD = 0.45

MARKET_PATTERNS = (
    "코스피", "코스닥", "증시", "특징주", "급등", "급락", "상승 마감",
    "하락 마감", "동반 상승", "동반 하락", "동반 강세", "동반 약세", "장 마감",
    "장중", "시황", "반도체주 반등", "훈풍", "사이드카", "200만닉스",
    "레버리지", "자산운용사",
)
COMMERCIAL_PATTERNS = (
    "할인", "페스티벌", "쇼핑", "상품권", "최저가", "구매 혜택", "프로모션",
    "이벤트 진행", "사은품", "특가",
)
EMPLOYMENT_PATTERNS = (
    "채용", "취업", "인턴", "설명회", "구인", "일자리 박람회",
)
CEREMONIAL_PATTERNS = (
    "수상", "대상 수상", "에너지대상", "위너상", "관왕", "영예", "선정",
    "시상식", "봉사활동", "기부", "캠페인 참여",
)
ROUNDUP_PATTERNS = (
    "[비즈&]", "오늘의 주요", "한눈에", "주요 뉴스", " 外",
)
EVENT_PATTERNS = (
    "파업", "쟁의", "노조", "임금협상", "출시", "공개", "신설", "수주",
    "공급", "규제", "리콜", "인수", "매각", "합병", "실적", "영업이익",
    "적자", "흑자", "증설", "감산", "양산", "계약", "소송", "조사", "중단",
    "장애", "화재", "사고", "개발", "승인", "허가", "신용등급", "조직 개편",
)


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern.casefold() in text for pattern in patterns)


def _topic_from_query(query_text: str | None, company: Company) -> str:
    if not query_text:
        return ""
    normalized = re.sub(r"\s+", " ", query_text).strip().casefold()
    company_name = company.name.casefold()
    if normalized == company_name:
        return ""
    if normalized.startswith(f"{company_name} "):
        return normalized[len(company_name) :].strip()
    return normalized


def _status_for(confidence: float) -> str:
    if confidence >= ELIGIBLE_THRESHOLD:
        return "eligible"
    if confidence >= CANDIDATE_THRESHOLD:
        return "candidate"
    return "rejected"


def classify_relevance(
    article: NormalizedNewsArticle,
    company: Company,
    *,
    query_text: str | None = None,
    query_type: str = "company",
    link_weight: float = 1.0,
) -> RelevanceResult:
    """기사 하나를 회사·검색어 문맥에 맞춰 점수화한다.

    BERTopic 입력에는 status가 ``eligible``인 기사만 사용한다. 점수의 모든
    가감 사유는 evidence에 남겨 규칙을 재현하고 조정할 수 있게 한다.
    """

    company_name = company.name.casefold()
    title = article.title.casefold()
    summary = article.summary.casefold()
    full_text = f"{title} {summary}"
    topic = _topic_from_query(query_text, company)
    score = 0.0
    evidence: list[str] = []

    company_in_title = company_name in title
    company_in_summary = company_name in summary
    if company_in_title:
        score += 0.65
        evidence.append("company_in_title:+0.65")
        if title.find(company_name) <= max(12, len(title) // 3):
            score += 0.05
            evidence.append("company_near_title_start:+0.05")
    elif company_in_summary:
        score += 0.35
        evidence.append("company_only_in_summary:+0.35")
    else:
        evidence.append("company_not_mentioned:+0.00")

    topic_in_title = bool(topic and topic in title)
    topic_in_summary = bool(topic and topic in summary)
    if topic_in_title:
        score += 0.25
        evidence.append("topic_in_title:+0.25")
    elif topic_in_summary:
        score += 0.12
        evidence.append("topic_only_in_summary:+0.12")
    elif topic:
        score -= 0.45
        evidence.append("topic_not_mentioned:-0.45")

    if _contains_any(full_text, EVENT_PATTERNS):
        score += 0.10
        evidence.append("event_signal:+0.10")

    if _contains_any(title, MARKET_PATTERNS):
        score -= 0.35
        evidence.append("market_roundup:-0.35")
    if _contains_any(full_text, COMMERCIAL_PATTERNS):
        score -= 0.50
        evidence.append("commercial_content:-0.50")
    if _contains_any(full_text, EMPLOYMENT_PATTERNS):
        score -= 0.50
        evidence.append("employment_content:-0.50")
    if _contains_any(full_text, CEREMONIAL_PATTERNS):
        score -= 0.30
        evidence.append("ceremonial_content:-0.30")
    if _contains_any(title, ROUNDUP_PATTERNS):
        score -= 0.45
        evidence.append("news_roundup:-0.45")

    mentioned_companies = {
        supported.name
        for supported in SUPPORTED_COMPANIES
        if supported.name.casefold() in full_text
    }
    if len(mentioned_companies) >= 3:
        score -= 0.15
        evidence.append("many_companies_listed:-0.15")

    bounded_weight = min(max(link_weight, 0.0), 1.0)
    if query_type != "company":
        score *= 0.85 + 0.15 * bounded_weight
        evidence.append(f"query_company_weight:{bounded_weight:.2f}")

    confidence = round(min(max(score, 0.0), 1.0), 4)
    status = _status_for(confidence)
    if status == "rejected":
        relation_type = "irrelevant"
    elif query_type == "company":
        relation_type = "direct"
    elif query_type == "product":
        relation_type = "product"
    else:
        relation_type = "industry"

    return RelevanceResult(
        relation_type=relation_type,
        confidence=confidence,
        evidence=tuple(evidence),
        status=status,
        rule_version=RULE_VERSION,
    )
