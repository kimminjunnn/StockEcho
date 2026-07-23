from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "output" / "pdf" / "StockEcho_뉴스데이터_활용계획서.pdf"
FONT_PATH = Path("/System/Library/Fonts/Supplemental/AppleGothic.ttf")

PAGE_W, PAGE_H = A4
NAVY = colors.HexColor("#173B5E")
BLUE = colors.HexColor("#2878D0")
PALE_BLUE = colors.HexColor("#EDF5FD")
INK = colors.HexColor("#1C2733")
MUTED = colors.HexColor("#5F6B78")
LINE = colors.HexColor("#D9E2EA")
SOFT = colors.HexColor("#F6F8FA")


pdfmetrics.registerFont(TTFont("Korean", str(FONT_PATH)))


styles = getSampleStyleSheet()
title_style = ParagraphStyle(
    "TitleKR",
    parent=styles["Title"],
    fontName="Korean",
    fontSize=23,
    leading=32,
    textColor=NAVY,
    alignment=TA_LEFT,
    spaceAfter=8 * mm,
)
subtitle_style = ParagraphStyle(
    "SubtitleKR",
    parent=styles["Normal"],
    fontName="Korean",
    fontSize=11,
    leading=18,
    textColor=MUTED,
)
section_style = ParagraphStyle(
    "SectionKR",
    parent=styles["Heading2"],
    fontName="Korean",
    fontSize=14,
    leading=20,
    textColor=NAVY,
    spaceBefore=5 * mm,
    spaceAfter=3 * mm,
)
body_style = ParagraphStyle(
    "BodyKR",
    parent=styles["BodyText"],
    fontName="Korean",
    fontSize=9.4,
    leading=16,
    textColor=INK,
    wordWrap="CJK",
    spaceAfter=2.2 * mm,
)
small_style = ParagraphStyle(
    "SmallKR",
    parent=body_style,
    fontSize=8.3,
    leading=13,
    textColor=MUTED,
    spaceAfter=0,
)
callout_style = ParagraphStyle(
    "CalloutKR",
    parent=body_style,
    fontSize=10,
    leading=17,
    textColor=NAVY,
    spaceAfter=0,
)
bullet_style = ParagraphStyle(
    "BulletKR",
    parent=body_style,
    leftIndent=5 * mm,
    firstLineIndent=-3.5 * mm,
    bulletIndent=1.5 * mm,
    spaceAfter=1.4 * mm,
)
table_head_style = ParagraphStyle(
    "TableHeadKR",
    parent=small_style,
    textColor=colors.white,
    alignment=TA_CENTER,
    fontSize=8.5,
    leading=12,
)
table_body_style = ParagraphStyle(
    "TableBodyKR",
    parent=small_style,
    textColor=INK,
    fontSize=8.1,
    leading=12,
)


def header_footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_H - 8 * mm, PAGE_W, 8 * mm, fill=1, stroke=0)
    canvas.setFont("Korean", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(18 * mm, 10 * mm, "StockEcho 뉴스데이터 활용계획서")
    canvas.drawRightString(PAGE_W - 18 * mm, 10 * mm, f"{doc.page}")
    canvas.setStrokeColor(LINE)
    canvas.line(18 * mm, 14 * mm, PAGE_W - 18 * mm, 14 * mm)
    canvas.restoreState()


def P(text, style=body_style):
    return Paragraph(text, style)


def bullet(text):
    return Paragraph(f"• {text}", bullet_style)


def section(number, title):
    return Paragraph(f"{number}. {title}", section_style)


def callout(text):
    box = Table([[P(text, callout_style)]], colWidths=[166 * mm])
    box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), PALE_BLUE),
                ("BOX", (0, 0), (-1, -1), 0.7, colors.HexColor("#B9D7F3")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6 * mm),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6 * mm),
                ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
            ]
        )
    )
    return box


def flow_table():
    labels = [
        "뉴스데이터\n수집",
        "정규화·\n중복 제거",
        "기업·사건\n식별",
        "유사 사건\n검색",
        "주가 반응\n결합",
        "분석 결과\n제공",
    ]
    cells = []
    for index, label in enumerate(labels):
        cells.append(P(label.replace("\n", "<br/>"), ParagraphStyle(
            f"Flow{index}", parent=small_style, alignment=TA_CENTER,
            textColor=NAVY, fontSize=8.1, leading=11,
        )))
        if index < len(labels) - 1:
            cells.append(P("›", ParagraphStyle(
                f"Arrow{index}", parent=small_style, alignment=TA_CENTER,
                textColor=BLUE, fontSize=16, leading=18,
            )))
    widths = []
    for index in range(len(cells)):
        widths.append(24 * mm if index % 2 == 0 else 4.2 * mm)
    table = Table([cells], colWidths=widths, rowHeights=[19 * mm])
    style = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 1.5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 1.5 * mm),
    ]
    for index in range(0, len(cells), 2):
        style.extend([
            ("BACKGROUND", (index, 0), (index, 0), SOFT),
            ("BOX", (index, 0), (index, 0), 0.6, LINE),
        ])
    table.setStyle(TableStyle(style))
    return table


def build_story():
    story = []
    story.append(Spacer(1, 12 * mm))
    story.append(P("뉴스데이터 활용계획서", title_style))
    story.append(P("StockEcho(스톡에코) - 과거 유사 이슈 및 주가 반응 분석 서비스", subtitle_style))
    story.append(Spacer(1, 9 * mm))

    info = Table(
        [
            [P("활용 서비스", small_style), P("StockEcho(스톡에코)", table_body_style)],
            [P("활용 부문", small_style), P("과거 유사 뉴스 사건 검색 및 주가 반응 비교(Risk Replay)", table_body_style)],
            [P("작성일", small_style), P("2026년 7월 23일", table_body_style)],
            [P("연락 이메일", small_style), P("alswns8495@naver.com", table_body_style)],
        ],
        colWidths=[31 * mm, 135 * mm],
    )
    info.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("BACKGROUND", (1, 0), (1, -1), SOFT),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3.2 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.2 * mm),
    ]))
    story.append(info)
    story.append(Spacer(1, 7 * mm))

    story.append(section("1", "서비스 개요 및 목적"))
    story.append(P(
        "StockEcho는 국내 상장사와 관련된 주요 뉴스 및 공시를 사건 단위로 정리하고, "
        "현재 발생한 이슈와 의미적으로 유사한 과거 사건을 검색하여 당시의 실제 주가 반응을 함께 제공하는 투자정보 분석 서비스입니다."
    ))
    story.append(P(
        "사용자가 보유하거나 관심 있는 종목에서 주요 이슈가 발생하면 과거 유사 뉴스 사건을 찾아 "
        "사건 발생 이후 실제 거래일 기준 1일, 5일, 15일, 30일의 주가 변동을 비교해 제공합니다."
    ))
    story.append(callout(
        "본 서비스는 투자자의 정보 이해를 돕기 위한 분석·교육 목적의 서비스이며, 특정 종목의 매수·매도 권유 또는 미래 주가의 확정적 예측을 목적으로 하지 않습니다."
    ))
    story.append(Spacer(1, 5 * mm))

    story.append(section("2", "뉴스데이터 활용 범위"))
    uses = [
        "뉴스와 국내 상장 종목 간의 연관성 판별",
        "동일하거나 유사한 뉴스 기사의 중복 제거",
        "동일 사건을 보도한 복수 기사의 사건 단위 그룹화",
        "사건 유형, 관련 기업, 발생 시점 및 영향 대상 분류",
        "현재 이슈와 과거 뉴스 사건 간의 의미 유사도 분석",
        "과거 사건과 주가 데이터 연결 및 1·5·15·30 거래일 수익률 산출",
        "분석 품질 검증과 검색·분류 정확도 개선",
    ]
    for item in uses:
        story.append(bullet(item))
    story.append(P(
        "뉴스 본문은 종목 연관성 판별, 사건 분류 및 유사 사건 검색의 정확도를 높이기 위한 내부 분석 목적으로 사용합니다."
    ))

    story.append(PageBreak())
    story.append(section("3", "데이터 처리 과정"))
    story.append(P(
        "구매한 뉴스데이터는 아래 절차에 따라 처리하며, 각 단계의 결과에는 사용 데이터와 분석 버전을 기록해 추적 가능하도록 관리합니다."
    ))
    story.append(Spacer(1, 2 * mm))
    story.append(flow_table())
    story.append(Spacer(1, 6 * mm))

    process_rows = [
        [P("단계", table_head_style), P("주요 처리 내용", table_head_style), P("생성 결과", table_head_style)],
        [P("수집·정규화", table_body_style), P("기사 식별자, 제목, 본문, 발행시각, 언론사, URL 및 분류정보를 표준 형식으로 변환", table_body_style), P("정규화 기사", table_body_style)],
        [P("중복 제거", table_body_style), P("URL·제목·본문 유사도를 활용해 동일 보도자료와 반복 기사를 그룹화", table_body_style), P("기사 그룹", table_body_style)],
        [P("사건 구성", table_body_style), P("기업, 사건 유형, 시점 및 의미 유사성을 기준으로 복수 기사를 하나의 사건으로 구성", table_body_style), P("Historical Event", table_body_style)],
        [P("유사도 분석", table_body_style), P("현재 이슈와 과거 사건의 사건 유형·핵심 개체·내용 유사성을 평가", table_body_style), P("과거 유사 사례", table_body_style)],
        [P("시장 반응", table_body_style), P("사건 시점의 가격 데이터를 연결해 1·5·15·30 거래일 수익률과 비교 차트를 계산", table_body_style), P("주가 반응 지표", table_body_style)],
    ]
    process_table = Table(process_rows, colWidths=[28 * mm, 102 * mm, 36 * mm], repeatRows=1)
    process_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, SOFT]),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 2.8 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2.8 * mm),
    ]))
    story.append(process_table)

    story.append(section("4", "사용자 제공 범위"))
    story.append(P("사용자 화면에는 원칙적으로 다음 정보만 제공합니다."))
    display_items = [
        "사건명, 사건 발생일, 관련 기업 및 종목",
        "언론사명, 기사 제목, 발행일 및 언론사 원문 링크",
        "자체 분석으로 생성한 사건 분류, 관련도 및 근거 출처 수",
        "사건 발생 이후 주가 변동 통계와 정규화 비교 차트",
    ]
    for item in display_items:
        story.append(bullet(item))
    story.append(callout(
        "구매한 뉴스 본문 전체 또는 원본 데이터 파일을 사용자에게 제공하지 않으며, 뉴스데이터 자체를 재판매하거나 제3자에게 데이터셋 형태로 제공하지 않습니다."
    ))

    story.append(section("5", "초기 적용 대상"))
    story.append(P(
        "초기에는 국내 주요 상장사를 대상으로 개발·검증하며, 실적 발표, 수주·계약, 규제·정책, 소송·제재, "
        "노사갈등·파업, 생산중단·화재·사고, 공급망 차질, 투자·증설, 신제품·기술 발표, 인수합병 및 경영진 변경 등의 사건을 분석합니다."
    ))

    story.append(PageBreak())
    story.append(section("6", "데이터 관리 및 보호"))
    protections = [
        "뉴스 원본 데이터는 접근 권한이 제한된 서버와 데이터베이스에 저장합니다.",
        "서비스 운영에 필요한 관리자 및 승인된 분석 프로세스만 원본 데이터에 접근합니다.",
        "데이터베이스 인증정보와 원본 뉴스데이터는 외부에 공개하지 않습니다.",
        "사용자에게 기사 본문 원문 파일이나 대량 다운로드 기능을 제공하지 않습니다.",
        "계약 종료 또는 보유기간 종료 시 계약 조건에 따라 원본 데이터를 삭제하거나 이용을 중단합니다.",
        "데이터 사용 목적이나 화면 제공 범위가 변경되는 경우 사전에 이용 가능 범위를 확인합니다.",
    ]
    for item in protections:
        story.append(bullet(item))

    story.append(section("7", "이용허락 및 견적 문의사항"))
    story.append(P(
        "StockEcho는 뉴스 본문을 내부 검색·분류·유사도 분석에 활용하고, 사용자에게는 원문 전체가 아닌 최소한의 기사 메타정보와 자체 산출한 사건·주가 분석 결과를 제공하고자 합니다. 다음 사항에 대한 확인을 요청드립니다."
    ))
    questions = [
        "구매한 뉴스 본문을 종목 연관성 판별, 중복 제거, 사건 클러스터링 및 유사도 분석에 사용할 수 있는지",
        "내부 분석으로 생성한 사건명, 사건 유형, 관련도 및 통계값을 서비스 화면에 제공할 수 있는지",
        "기사 제목, 언론사명, 발행일 및 언론사 원문 링크를 사용자 화면에 표시할 수 있는지",
        "기사 원문을 노출하지 않고 사건 단위 통계와 주가 분석 결과만 제공하는 경우의 이용허락 범위",
        "계약 종료 시 원본 데이터와 파생 분석 결과의 보관·이용 가능 범위",
        "향후 분석 종목 및 서비스 이용자가 증가할 경우 필요한 추가 계약 조건",
    ]
    for idx, item in enumerate(questions, start=1):
        story.append(Paragraph(f"{idx}. {item}", bullet_style))

    story.append(Spacer(1, 5 * mm))
    story.append(callout(
        "현재 개발·검증 단계이며, 향후 서비스 운영 및 유료화 가능성을 고려하여 필요한 계약 범위와 견적을 함께 안내해 주시면 감사하겠습니다."
    ))
    story.append(Spacer(1, 8 * mm))

    contact = Table(
        [[P("문의 이메일", table_head_style), P("alswns8495@naver.com", table_body_style)]],
        colWidths=[38 * mm, 128 * mm],
    )
    contact.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, 0), NAVY),
        ("BACKGROUND", (1, 0), (1, 0), SOFT),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3.5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5 * mm),
    ]))
    story.append(contact)
    return story


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=17 * mm,
        bottomMargin=20 * mm,
        title="StockEcho 뉴스데이터 활용계획서",
        author="StockEcho",
        subject="뉴스데이터 구매 및 활용 목적 설명자료",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="standard", frames=[frame], onPage=header_footer)])
    doc.build(build_story())
    print(OUTPUT)


if __name__ == "__main__":
    main()
