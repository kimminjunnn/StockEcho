"""BERTopic c-TF-IDF에 연결하는 Kiwi tokenizer."""

from __future__ import annotations

from collections.abc import Iterable

from kiwipiepy import Kiwi


DEFAULT_STOPWORDS = frozenset(
    {
        "기자",
        "뉴스",
        "관련",
        "통해",
        "대한",
        "위해",
        "이번",
        "지난",
        "올해",
        "현재",
        "가운데",
        "따르면",
        "밝혔다",
        "대해",
        "등",
    }
)


class KiwiTokenizer:
    """명사·동사·형용사 중심의 pickle 가능한 sklearn tokenizer.

    Kiwi 인스턴스는 직렬화하지 않고 worker에서 처음 호출될 때 만든다.
    """

    def __init__(
        self,
        *,
        stopwords: Iterable[str] = DEFAULT_STOPWORDS,
        min_length: int = 2,
    ) -> None:
        self.stopwords = tuple(sorted(set(stopwords)))
        self.min_length = min_length
        self._kiwi: Kiwi | None = None

    @property
    def kiwi(self) -> Kiwi:
        if self._kiwi is None:
            self._kiwi = Kiwi()
        return self._kiwi

    def __call__(self, text: str) -> list[str]:
        stopwords = set(self.stopwords)
        result: list[str] = []
        for token in self.kiwi.tokenize(text or ""):
            if not token.tag.startswith(("NN", "VV", "VA", "SL")):
                continue
            form = token.form.casefold().strip()
            if len(form) < self.min_length or form in stopwords:
                continue
            result.append(form)
        return result

    def __getstate__(self) -> dict:
        state = self.__dict__.copy()
        state["_kiwi"] = None
        return state
