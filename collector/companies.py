"""MVP 지원 종목 master."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Company:
    stock_code: str
    name: str
    tier: str
    sector: str
    aliases: tuple[str, ...] = ()


SUPPORTED_COMPANIES = (
    Company("005930", "삼성전자", "A", "반도체·전자", ("삼성",)),
    Company("000660", "SK하이닉스", "A", "반도체"),
    Company("005380", "현대차", "A", "자동차", ("현대",)),
    Company("373220", "LG에너지솔루션", "A", "배터리"),
    Company("207940", "삼성바이오로직스", "A", "바이오"),
    Company("105560", "KB금융", "A", "금융"),
    Company("005490", "POSCO홀딩스", "A", "철강·소재"),
    Company("012450", "한화에어로스페이스", "A", "방산·항공"),
    Company("035420", "NAVER", "A", "플랫폼·인터넷"),
    Company("017670", "SK텔레콤", "A", "통신"),
    Company("000270", "기아", "B", "자동차"),
    Company("068270", "셀트리온", "B", "바이오"),
    Company("035720", "카카오", "B", "플랫폼·인터넷"),
    Company("055550", "신한지주", "B", "금융"),
    Company("329180", "HD현대중공업", "B", "조선"),
    Company("034020", "두산에너빌리티", "B", "원전·에너지"),
    Company("402340", "SK스퀘어", "B", "반도체 투자·지주"),
    Company("028260", "삼성물산", "B", "건설·상사·지주", ("삼성",)),
    Company("032830", "삼성생명", "B", "보험", ("삼성",)),
    Company("009150", "삼성전기", "B", "전자부품", ("삼성",)),
)

COMPANIES_BY_CODE = {company.stock_code: company for company in SUPPORTED_COMPANIES}


def get_company(stock_code: str) -> Company:
    try:
        return COMPANIES_BY_CODE[stock_code]
    except KeyError as error:
        supported = ", ".join(COMPANIES_BY_CODE)
        raise ValueError(
            f"지원하지 않는 종목 코드입니다: {stock_code}. 지원 코드: {supported}"
        ) from error
