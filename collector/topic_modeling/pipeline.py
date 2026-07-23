"""로컬과 Colab에서 공유하는 한국어 BERTopic 실험 파이프라인."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Sequence
from zoneinfo import ZoneInfo

from collector.repositories.local import read_jsonl, write_jsonl_atomic
from collector.topic_modeling.event_labeling import build_event_labels
from collector.topic_modeling.issue_classifier import classify_major_issues
from collector.topic_modeling.results import (
    annotate_major_issues,
    build_topic_records,
    select_major_issues,
)
from collector.topic_modeling.tokenizer import KiwiTokenizer


@dataclass(frozen=True)
class TopicModelConfig:
    model_version: str = "bertopic-ko-v1"
    embedding_model: str = "jhgan/ko-sroberta-multitask"
    timezone_name: str = "Asia/Seoul"
    random_state: int = 42
    min_topic_size: int = 3
    top_n_words: int = 10
    issue_windows: tuple[int, ...] = (7, 14, 30)
    issue_limit: int = 3
    issue_min_articles: int = 2


def _validate_articles(rows: Sequence[dict[str, Any]]) -> list[dict[str, Any]]:
    required = {"document_id", "stock_code", "published_at", "text"}
    unique: dict[str, dict[str, Any]] = {}
    for line_number, row in enumerate(rows, start=1):
        missing = required - row.keys()
        if missing:
            raise ValueError(
                f"입력 {line_number}행에 필수 필드가 없습니다: {sorted(missing)}"
            )
        if row["document_id"] not in unique:
            unique[row["document_id"]] = dict(row)
    stock_codes = {row["stock_code"] for row in unique.values()}
    if len(stock_codes) != 1:
        raise ValueError("한 번의 실행에는 한 종목의 기사만 입력할 수 있습니다.")
    result = sorted(unique.values(), key=lambda row: row["document_id"])
    if len(result) < 5:
        raise ValueError("BERTopic 실험에는 중복 제거 후 최소 5개 기사가 필요합니다.")
    return result


def _load_runtime():
    try:
        import numpy as np
        from bertopic import BERTopic
        from hdbscan import HDBSCAN
        from sentence_transformers import SentenceTransformer
        from sklearn.feature_extraction.text import CountVectorizer
        from umap import UMAP
    except ImportError as exc:
        raise RuntimeError(
            "BERTopic 실험 의존성이 없습니다. "
            "pip install -r requirements-bertopic.txt 를 먼저 실행하세요."
        ) from exc
    return np, BERTopic, HDBSCAN, SentenceTransformer, CountVectorizer, UMAP


def _representation_scores(
    embeddings,
    assignments: Sequence[int],
    articles: Sequence[dict[str, Any]],
    timezone_name: str,
) -> list[float]:
    import numpy as np

    values = np.asarray(embeddings)
    scores = np.zeros(len(assignments), dtype=float)
    groups: dict[tuple[int, date], list[int]] = {}
    local_timezone = ZoneInfo(timezone_name)
    for index, (topic_id, article) in enumerate(zip(assignments, articles)):
        published = datetime.fromisoformat(article["published_at"].replace("Z", "+00:00"))
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)
        key = (topic_id, published.astimezone(local_timezone).date())
        groups.setdefault(key, []).append(index)

    for (topic_id, _event_date), indices in groups.items():
        if topic_id == -1 or len(indices) == 1:
            continue
        cluster = values[indices]
        centroid = cluster.mean(axis=0)
        centroid_norm = np.linalg.norm(centroid) or 1.0
        row_norms = np.linalg.norm(cluster, axis=1)
        similarities = (cluster @ centroid) / np.maximum(row_norms * centroid_norm, 1e-12)
        for index, similarity in zip(indices, similarities):
            scores[index] = float(similarity)
    return scores.tolist()


def _remove_company_keywords(
    keywords: Sequence[str], company_name: str, tokenizer: KiwiTokenizer
) -> list[str]:
    company_tokens = set(tokenizer(company_name))
    company_tokens.add(company_name.casefold().replace(" ", ""))
    filtered = []
    for keyword in keywords:
        keyword_tokens = set(keyword.casefold().split())
        compact = keyword.casefold().replace(" ", "")
        if compact in company_tokens or (
            keyword_tokens and keyword_tokens.issubset(company_tokens)
        ):
            continue
        filtered.append(keyword)
    return filtered


def run_topic_pipeline(
    *,
    input_path: Path,
    topics_output_path: Path,
    issues_output_path: Path,
    config: TopicModelConfig = TopicModelConfig(),
    as_of: date | None = None,
    device: str | None = None,
) -> dict[str, Any]:
    articles = _validate_articles(read_jsonl(input_path))
    (
        _np,
        BERTopic,
        HDBSCAN,
        SentenceTransformer,
        CountVectorizer,
        UMAP,
    ) = _load_runtime()

    texts = [row["text"] for row in articles]
    embedding_model = SentenceTransformer(config.embedding_model, device=device)
    embeddings = embedding_model.encode(
        texts,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    n_neighbors = max(2, min(15, len(articles) - 1))
    n_components = max(2, min(5, len(articles) - 2))
    min_cluster_size = max(2, min(config.min_topic_size, len(articles) // 2))
    kiwi_tokenizer = KiwiTokenizer()
    vectorizer = CountVectorizer(
        tokenizer=kiwi_tokenizer,
        token_pattern=None,
        lowercase=False,
        ngram_range=(1, 2),
        min_df=1,
    )
    topic_model = BERTopic(
        embedding_model=embedding_model,
        vectorizer_model=vectorizer,
        umap_model=UMAP(
            n_neighbors=n_neighbors,
            n_components=n_components,
            min_dist=0.0,
            metric="cosine",
            random_state=config.random_state,
        ),
        hdbscan_model=HDBSCAN(
            min_cluster_size=min_cluster_size,
            metric="euclidean",
            cluster_selection_method="eom",
            prediction_data=True,
        ),
        top_n_words=config.top_n_words,
        # 작은 종목별 corpus가 전부 outlier가 되면 auto reduction이 빈 배열로
        # 실패한다. 원래 군집을 보존하면 데이터 부족도 정상 결과로 기록할 수 있다.
        nr_topics=None,
        calculate_probabilities=False,
        verbose=True,
    )
    assignments, _ = topic_model.fit_transform(texts, embeddings)
    keywords_by_topic = {
        topic_id: _remove_company_keywords(
            [word for word, _weight in (topic_model.get_topic(topic_id) or [])],
            articles[0].get("company_name", ""),
            kiwi_tokenizer,
        )
        for topic_id in set(assignments)
        if topic_id != -1
    }
    representation_scores = _representation_scores(
        embeddings,
        assignments,
        articles,
        config.timezone_name,
    )
    scored_articles = []
    for article, score in zip(articles, representation_scores):
        scored = dict(article)
        scored["_representation_score"] = score
        scored_articles.append(scored)
    event_labels = build_event_labels(
        scored_articles,
        assignments,
        embeddings,
        tokenizer=kiwi_tokenizer,
        encode=lambda values: embedding_model.encode(
            list(values),
            show_progress_bar=False,
            normalize_embeddings=True,
        ),
        timezone_name=config.timezone_name,
    )
    enriched_articles = []
    for article in scored_articles:
        enriched = dict(article)
        enriched["_event_representation"] = event_labels.get(article["document_id"])
        enriched_articles.append(enriched)

    topics = build_topic_records(
        enriched_articles,
        assignments,
        keywords_by_topic,
        model_version=config.model_version,
        timezone_name=config.timezone_name,
        event_keyword_tokenizer=kiwi_tokenizer,
    )
    reference_date = as_of or max(
        date.fromisoformat(event["event_date"])
        for topic in topics
        for event in topic["events"]
    )
    issues, used_window = select_major_issues(
        topics,
        as_of=reference_date,
        windows=config.issue_windows,
        limit=config.issue_limit,
        min_articles=config.issue_min_articles,
    )
    issues, classification_summary = classify_major_issues(issues)
    annotate_major_issues(topics, issues)
    write_jsonl_atomic(topics_output_path, topics)
    write_jsonl_atomic(issues_output_path, issues)
    return {
        "stock_code": articles[0]["stock_code"],
        "model_version": config.model_version,
        "embedding_model": config.embedding_model,
        "as_of": reference_date.isoformat(),
        "article_count": len(articles),
        "topic_count": sum(not topic["is_outlier"] for topic in topics),
        "outlier_count": sum(topic["is_outlier"] for topic in topics),
        "major_issue_count": len(issues),
        "issue_classification": classification_summary,
        "expanded_through_days": used_window,
        "topics_output_path": str(topics_output_path),
        "issues_output_path": str(issues_output_path),
    }
