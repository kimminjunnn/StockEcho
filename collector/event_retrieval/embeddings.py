"""Event 문장 임베딩 어댑터."""

from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence
from typing import Protocol


DEFAULT_EMBEDDING_MODEL = "jhgan/ko-sroberta-multitask"
TOKEN_PATTERN = re.compile(r"[가-힣a-z0-9]+")


class TextEmbedder(Protocol):
    model_name: str

    def encode(self, texts: Sequence[str]) -> list[list[float]]: ...


class SentenceTransformerEmbedder:
    """대형 의존성과 모델 로딩을 실제 사용 시점까지 늦춘다."""

    def __init__(self, model_name: str = DEFAULT_EMBEDDING_MODEL) -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self._model = SentenceTransformer(model_name)

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        values = self._model.encode(
            list(texts),
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [[float(value) for value in row] for row in values]


class HashingTextEmbedder:
    """테스트와 의존성 없는 로컬 실행을 위한 결정적 lexical 기준선."""

    def __init__(self, dimensions: int = 256) -> None:
        if dimensions < 8:
            raise ValueError("dimensions는 8 이상이어야 합니다.")
        self.dimensions = dimensions
        self.model_name = f"hashing-korean-token-v1-{dimensions}"

    def encode(self, texts: Sequence[str]) -> list[list[float]]:
        rows: list[list[float]] = []
        for text in texts:
            vector = [0.0] * self.dimensions
            for token in TOKEN_PATTERN.findall(text.casefold()):
                digest = hashlib.sha256(token.encode("utf-8")).digest()
                index = int.from_bytes(digest[:4], "big") % self.dimensions
                sign = 1.0 if digest[4] % 2 == 0 else -1.0
                vector[index] += sign
            norm = math.sqrt(sum(value * value for value in vector)) or 1.0
            rows.append([value / norm for value in vector])
        return rows
