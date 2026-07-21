"""직접 수집한 기사에서 설명 가능한 확장 검색어 후보를 추출한다."""

from __future__ import annotations

import math
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Mapping
from urllib.parse import urlsplit

from kiwipiepy import Kiwi

from collector.companies import Company, SUPPORTED_COMPANIES


RULE_VERSION = "keyword-v1"
NOUN_TAGS = {"NNG", "NNP", "SL"}
GENERIC_REJECT = {
    "관련", "회사", "기업", "업계", "시장", "주가", "증시", "코스피", "투자",
    "기자", "뉴스", "이날", "전망", "상승", "하락", "종목", "실적", "발표",
    "올해", "사업", "그룹", "대표", "회장", "사장", "국내", "글로벌", "한국",
    "서울", "거래", "기관", "외국인", "정부", "경제", "기술", "제품", "대상",
    "대통령", "노동", "쟁의", "문의", "수상", "기염", "유지", "급등", "반등",
    "연속", "신설", "본격", "신용", "조직", "차세대", "지수", "코스피", "효율",
    "핵심", "추진", "직속", "거점", "사업", "소비자시민모임", "이사", "대비",
    "대형", "주최", "후원", "기반", "부문", "선정", "평가", "확대", "강화",
}
BROAD_STANDALONE = {
    "삼성", "현대", "SK", "LG", "반도체", "자동차", "배터리", "금융", "바이오",
    "통신", "플랫폼", "전자", "철강", "조선", "에너지",
}
EVENT_PHRASES = (
    "공급 부족", "공급 차질", "수출 규제", "판매 부진", "실적 부진", "대규모 수주",
    "수주", "리콜", "관세", "증설", "감산", "파업", "출시", "양산",
)


@dataclass(frozen=True)
class KeywordCandidate:
    keyword: str
    kind: str
    score: float
    document_count: int
    source_count: int
    title_count: int
    evidence_article_ids: tuple[str, ...]
    status: str
    reason: str
    discovered_at: str
    expires_at: str
    rule_version: str = RULE_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _article_value(article: Mapping[str, Any] | Any, field: str) -> str:
    if isinstance(article, Mapping):
        return str(article.get(field, ""))
    return str(getattr(article, field, ""))


def _source_key(article: Mapping[str, Any] | Any) -> str:
    url = _article_value(article, "canonical_url")
    return urlsplit(url).netloc.casefold() or _article_value(article, "source") or "unknown"


def _clean_token(token: str) -> str:
    value = token.strip("_-·.,()[]{}'\"")
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9.+-]*", value):
        return value.upper()
    return value


class KiwiKeywordExtractor:
    def __init__(self, *, max_active: int = 5) -> None:
        self.max_active = max_active
        self.kiwi = Kiwi()

    def _terms(self, text: str) -> set[str]:
        nouns: list[tuple[str, int, int]] = []
        for token in self.kiwi.tokenize(text):
            if token.tag not in NOUN_TAGS:
                continue
            value = _clean_token(token.form)
            if len(value) < 2 and not re.fullmatch(r"[A-Z0-9]{2,}", value):
                continue
            nouns.append((value, token.start, token.len))
        terms = {value for value, _, _ in nouns}
        for (left, left_start, left_len), (right, right_start, _) in zip(nouns, nouns[1:]):
            # 문장 안에서 실제로 인접한 명사만 복합어로 묶는다.
            if left != right and right_start - (left_start + left_len) <= 1:
                terms.add(f"{left} {right}")
        return terms

    def extract(
        self,
        company: Company,
        articles: Iterable[Mapping[str, Any] | Any],
    ) -> list[KeywordCandidate]:
        documents = list(articles)
        if not documents:
            return []
        now = datetime.now(timezone.utc)
        discovered_at = now.isoformat()
        expires_at = (now + timedelta(days=7)).isoformat()
        blocked = {company.name.casefold(), *(alias.casefold() for alias in company.aliases)}
        company_entity_terms = set()
        for supported in SUPPORTED_COMPANIES:
            company_entity_terms.add(supported.name.casefold())
            company_entity_terms.update(alias.casefold() for alias in supported.aliases)
            company_entity_terms.update(
                part.casefold()
                for part in re.findall(r"[A-Za-z]+|[가-힣]{2,}", supported.name)
            )
        document_terms: list[set[str]] = []
        title_terms: list[set[str]] = []
        for article in documents:
            title = _article_value(article, "title")
            summary = _article_value(article, "summary")
            title_terms.append(self._terms(title))
            document_terms.append(self._terms(f"{title} {summary}"))

        document_frequency = Counter(term for terms in document_terms for term in terms)
        title_frequency = Counter(term for terms in title_terms for term in terms)
        source_sets: dict[str, set[str]] = defaultdict(set)
        evidence: dict[str, list[str]] = defaultdict(list)
        weighted_frequency: Counter[str] = Counter()
        for index, article in enumerate(documents):
            article_id = _article_value(article, "document_id")
            source = _source_key(article)
            for term in document_terms[index]:
                source_sets[term].add(source)
                if article_id and len(evidence[term]) < 5:
                    evidence[term].append(article_id)
                weighted_frequency[term] += 1.0 + (1.5 if term in title_terms[index] else 0.0)

        raw: list[dict[str, Any]] = []
        total_documents = len(documents)
        for term, document_count in document_frequency.items():
            folded = term.casefold()
            if (
                document_count < 2
                or folded in blocked
                or term in GENERIC_REJECT
                or any(part in GENERIC_REJECT for part in term.split())
                or folded in company_entity_terms
                or any(part.casefold() in company_entity_terms for part in term.split())
            ):
                continue
            if any(part.casefold() in blocked for part in term.split()) and len(term.split()) == 1:
                continue
            source_count = len(source_sets[term])
            title_count = title_frequency[term]
            idf = math.log((total_documents + 1) / (document_count + 1)) + 1
            score = weighted_frequency[term] * idf * (1 + 0.2 * max(source_count - 1, 0))
            is_broad = term in BROAD_STANDALONE
            eligible = (
                not is_broad
                and document_count >= 2
                and source_count >= 2
                and title_count >= 1
            )
            raw.append(
                {
                    "keyword": term,
                    "kind": "topic",
                    "score": score,
                    "document_count": document_count,
                    "source_count": source_count,
                    "title_count": title_count,
                    "evidence_article_ids": tuple(evidence[term]),
                    "eligible": eligible,
                    "reason": "broad_standalone" if is_broad else "corpus_metrics",
                }
            )

        # 이벤트 조합은 같은 기사에 두 표현이 실제로 공존할 때만 생성한다.
        event_metrics: dict[str, dict[str, Any]] = {}
        base_terms = [row["keyword"] for row in raw if " " not in row["keyword"]]
        for term in base_terms:
            for event_phrase in EVENT_PHRASES:
                if (
                    term.casefold() == event_phrase.casefold()
                    or term.casefold() in {part.casefold() for part in event_phrase.split()}
                ):
                    continue
                matched_indexes = []
                for index, article in enumerate(documents):
                    text = f"{_article_value(article, 'title')} {_article_value(article, 'summary')}"
                    if term.casefold() in text.casefold() and event_phrase in text:
                        matched_indexes.append(index)
                if len(matched_indexes) < 2:
                    continue
                keyword = f"{term} {event_phrase}"
                sources = {_source_key(documents[index]) for index in matched_indexes}
                titles = sum(
                    keyword.casefold() in _article_value(documents[index], "title").casefold()
                    or (
                        term.casefold() in _article_value(documents[index], "title").casefold()
                        and event_phrase in _article_value(documents[index], "title")
                    )
                    for index in matched_indexes
                )
                event_metrics[keyword] = {
                    "keyword": keyword,
                    "kind": "event",
                    "score": len(matched_indexes) * 2.5 + len(sources) + titles,
                    "document_count": len(matched_indexes),
                    "source_count": len(sources),
                    "title_count": titles,
                    "evidence_article_ids": tuple(
                        _article_value(documents[index], "document_id")
                        for index in matched_indexes[:5]
                    ),
                    "eligible": len(sources) >= 2 and titles >= 1,
                    "reason": "observed_keyword_event_cooccurrence",
                }
        raw.extend(event_metrics.values())
        raw.sort(
            key=lambda row: (
                -int(row["eligible"]),
                -int(row["kind"] == "event"),
                -row["score"],
                -row["source_count"],
                -row["title_count"],
                row["keyword"].casefold(),
            ),
        )
        active_keywords: set[str] = set()
        active_token_sets: list[tuple[str, set[str]]] = []
        for row in (candidate for candidate in raw if candidate["eligible"]):
            tokens = set(row["keyword"].casefold().split())
            if any(
                row["kind"] == selected_kind
                and (tokens <= selected or selected <= tokens)
                for selected_kind, selected in active_token_sets
            ):
                continue
            active_keywords.add(row["keyword"])
            active_token_sets.append((row["kind"], tokens))
            if len(active_keywords) >= self.max_active:
                break
        return [
            KeywordCandidate(
                keyword=row["keyword"],
                kind=row["kind"],
                score=round(row["score"], 4),
                document_count=row["document_count"],
                source_count=row["source_count"],
                title_count=row["title_count"],
                evidence_article_ids=row["evidence_article_ids"],
                status=("active" if row["keyword"] in active_keywords else "candidate"),
                reason=row["reason"],
                discovered_at=discovered_at,
                expires_at=expires_at,
            )
            for row in raw
        ]
