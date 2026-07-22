"""Event 기사 군집에서 자연스러운 추출형 이슈명과 의미 키프레이즈를 만든다."""

from __future__ import annotations

import hashlib
import re
from collections import Counter, defaultdict
from collections.abc import Callable, Sequence
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo


LABEL_METHOD = "extractive-semantic-mmr-v1"
EDITORIAL_TOKENS = {"단독", "르포", "종합", "속보", "사진", "영상"}


def _event_key(document_ids: Sequence[str]) -> str:
    return hashlib.sha256("\n".join(sorted(document_ids)).encode("utf-8")).hexdigest()[:20]


def _company_noise(company_name: str, tokenizer: Callable[[str], list[str]]) -> set[str]:
    tokens = set(tokenizer(company_name))
    tokens.add(company_name.casefold().replace(" ", ""))
    for suffix in ("전자", "그룹", "홀딩스", "주식회사"):
        if company_name.endswith(suffix) and len(company_name) > len(suffix):
            alias = company_name[: -len(suffix)]
            tokens.update(tokenizer(alias))
            tokens.add(alias.casefold().replace(" ", ""))
    return tokens | EDITORIAL_TOKENS


def _candidate_phrases(
    rows: Sequence[dict[str, Any]],
    tokenizer: Callable[[str], list[str]],
    company_name: str,
) -> tuple[list[str], dict[str, float]]:
    noise = _company_noise(company_name, tokenizer)
    document_counts: Counter[str] = Counter()
    for row in rows:
        tokens = [token for token in tokenizer(row.get("title", "")) if token not in noise]
        phrases: set[str] = set()
        for size in (2, 3):
            phrases.update(
                " ".join(tokens[index : index + size])
                for index in range(len(tokens) - size + 1)
            )
        if not phrases:
            phrases.update(tokens)
        document_counts.update(phrases)

    total = max(len(rows), 1)
    candidates = sorted(document_counts, key=lambda value: (-document_counts[value], value))
    coverage = {candidate: document_counts[candidate] / total for candidate in candidates}
    return candidates, coverage


def _headline_clauses(title: str, company_name: str) -> list[str]:
    aliases = {company_name}
    for suffix in ("전자", "그룹", "홀딩스", "주식회사"):
        if company_name.endswith(suffix) and len(company_name) > len(suffix):
            aliases.add(company_name[: -len(suffix)])
    company_pattern = "|".join(re.escape(alias) for alias in sorted(aliases, key=len, reverse=True))

    cleaned = re.sub(r"^\s*(?:\[[^\]]+\]|\([^)]*(?:단독|속보|종합)[^)]*\))\s*", "", title)
    parts = re.split(r"(?:\.{2,}|…+|[|｜]|\s[-–—]\s|[,，])", cleaned)
    clauses = []
    for part in parts:
        value = re.sub(rf"^\s*(?:{company_pattern})(?:의|가|은|는|이|도)?\s*", "", part, flags=re.I)
        value = re.sub(r"\s+", " ", value).strip(" \t\n\r:;·'\"")
        value = re.sub(
            r"(\S*설)\s+(?:사실무근|부인(?:했다|해)?|반박(?:했다|해)?)$",
            r"\1",
            value,
        )
        last_word = value.rsplit(" ", 1)[-1]
        if len(last_word) == 1 and re.fullmatch(r"[가-힣]", last_word):
            continue
        if 4 <= len(value) <= 54:
            clauses.append(value)
    return clauses


def _mmr_indices(vectors, relevance, *, top_n: int = 5, diversity: float = 0.2) -> list[int]:
    import numpy as np

    if len(relevance) == 0:
        return []
    selected = [int(np.argmax(relevance))]
    remaining = set(range(len(relevance))) - set(selected)
    relevance_weight = 1.0 - diversity
    while remaining and len(selected) < top_n:
        best = max(
            remaining,
            key=lambda index: (
                relevance_weight * relevance[index]
                - diversity * max(float(vectors[index] @ vectors[chosen]) for chosen in selected),
                relevance[index],
                -index,
            ),
        )
        selected.append(best)
        remaining.remove(best)
    return selected


def build_event_labels(
    articles: Sequence[dict[str, Any]],
    assignments: Sequence[int],
    embeddings,
    *,
    tokenizer: Callable[[str], list[str]],
    encode: Callable[[Sequence[str]], Any],
    timezone_name: str,
) -> dict[str, dict[str, Any]]:
    """문서 ID별로 동일 Event의 추출형 이름/키프레이즈를 반환한다."""

    import numpy as np

    local_timezone = ZoneInfo(timezone_name)
    groups: dict[tuple[int, str], list[int]] = defaultdict(list)
    for index, (topic_id, article) in enumerate(zip(assignments, articles)):
        published = datetime.fromisoformat(article["published_at"].replace("Z", "+00:00"))
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        outlier_key = article["document_id"] if topic_id == -1 else "topic"
        groups[
            (topic_id, f"{published.astimezone(local_timezone).date().isoformat()}:{outlier_key}")
        ].append(index)

    values = np.asarray(embeddings)
    labels_by_document: dict[str, dict[str, Any]] = {}
    for indices in groups.values():
        rows = [articles[index] for index in indices]
        company_name = rows[0].get("company_name", "")
        candidates, coverage = _candidate_phrases(rows, tokenizer, company_name)
        if not candidates:
            continue

        event_centroid = values[indices].mean(axis=0)
        event_centroid /= np.linalg.norm(event_centroid) or 1.0
        candidate_vectors = np.asarray(encode(candidates))
        semantic_scores = candidate_vectors @ event_centroid
        relevance = np.asarray(
            [0.72 * float(score) + 0.28 * coverage[candidate] for candidate, score in zip(candidates, semantic_scores)]
        )
        selected_indices = _mmr_indices(candidate_vectors, relevance)
        keyphrases = [candidates[index] for index in selected_indices]

        representative_rows = sorted(
            rows,
            key=lambda row: (
                float(row.get("_representation_score", 0.0)),
                float(row.get("relevance_confidence", 0.0)),
                row.get("published_at", ""),
            ),
            reverse=True,
        )[:3]
        clause_ranks: dict[str, int] = {}
        for rank, row in enumerate(representative_rows):
            for clause in _headline_clauses(row.get("title", ""), company_name):
                clause_ranks.setdefault(clause, rank)
        clauses_with_rank = list(clause_ranks.items())
        clauses = [clause for clause, _rank in clauses_with_rank]
        if clauses:
            clause_vectors = np.asarray(encode(clauses))
            centroid_scores = clause_vectors @ event_centroid
            article_vectors = values[indices]
            coverage_scores = (clause_vectors @ article_vectors.T).mean(axis=1)
            key_tokens = set(token for phrase in keyphrases[:3] for token in phrase.split())
            lexical_scores = np.asarray(
                [
                    len(set(tokenizer(clause)) & key_tokens) / max(len(key_tokens), 1)
                    for clause in clauses
                ]
            )
            if np.any(lexical_scores > 0):
                valid = lexical_scores > 0
            else:
                valid = np.ones(len(clauses), dtype=bool)
            length_scores = np.asarray([1.0 - min(abs(len(clause) - 20) / 40, 1.0) for clause in clauses])
            rank_scores = np.asarray(
                [1.0 - rank / max(len(representative_rows), 1) for _clause, rank in clauses_with_rank]
            )
            has_denial = any(
                re.search(r"사실무근|부인|반박", row.get("title", ""))
                for row in representative_rows
            )
            neutrality_scores = np.asarray(
                [
                    1.0 if has_denial and re.search(r"(?:설|가능성)$", clause) else 0.0
                    for clause in clauses
                ]
            )
            clause_scores = (
                0.42 * centroid_scores
                + 0.23 * coverage_scores
                + 0.20 * lexical_scores
                + 0.05 * length_scores
                + 0.10 * rank_scores
                + 0.12 * neutrality_scores
            )
            clause_scores = np.where(valid, clause_scores, -np.inf)
            name = clauses[int(np.argmax(clause_scores))]
        else:
            name = keyphrases[0]

        representation = {
            "name": name,
            "keywords": keyphrases,
            "label_method": LABEL_METHOD,
            "event_fingerprint": _event_key([row["document_id"] for row in rows]),
        }
        for row in rows:
            labels_by_document[row["document_id"]] = representation
    return labels_by_document
