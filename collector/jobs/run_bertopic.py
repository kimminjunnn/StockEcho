"""한국어 뉴스 BERTopic 실험을 실행하고 Topic/Event JSONL을 저장한다."""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from collector.topic_modeling.pipeline import TopicModelConfig, run_topic_pipeline


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stock-code", required=True)
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--as-of", type=date.fromisoformat)
    parser.add_argument("--device", help="예: cpu, cuda, mps")
    parser.add_argument("--model-version", default="bertopic-ko-v1")
    parser.add_argument(
        "--embedding-model", default="jhgan/ko-sroberta-multitask"
    )
    parser.add_argument("--min-topic-size", type=int, default=3)
    parser.add_argument("--issue-min-articles", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    input_path = args.input or (
        PROJECT_ROOT / "data" / "processed" / "bertopic" / f"{args.stock_code}_articles.jsonl"
    )
    output_dir = args.output_dir or PROJECT_ROOT / "data" / "processed" / "topics"
    summary = run_topic_pipeline(
        input_path=input_path,
        topics_output_path=output_dir / f"{args.stock_code}_topics.jsonl",
        issues_output_path=output_dir / f"{args.stock_code}_major_issues.jsonl",
        config=TopicModelConfig(
            model_version=args.model_version,
            embedding_model=args.embedding_model,
            min_topic_size=args.min_topic_size,
            issue_min_articles=args.issue_min_articles,
        ),
        as_of=args.as_of,
        device=args.device,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
