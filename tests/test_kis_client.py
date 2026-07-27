from __future__ import annotations

import unittest
from datetime import date

from collector.clients.kis import KisCredentials, KisDailyPriceClient


class FakeResponse:
    def __init__(self, payload: dict, *, ok: bool = True, status_code: int = 200):
        self._payload = payload
        self.ok = ok
        self.status_code = status_code

    def json(self) -> dict:
        return self._payload


class FakeSession:
    def __init__(self, get_payload: dict, responses: list[FakeResponse] | None = None):
        self.get_payload = get_payload
        self.responses = list(responses or [])
        self.get_calls: list[dict] = []

    def post(self, url: str, **kwargs):
        return FakeResponse({"access_token": "test-token"})

    def get(self, url: str, **kwargs):
        self.get_calls.append({"url": url, **kwargs})
        if self.responses:
            return self.responses.pop(0)
        return FakeResponse(self.get_payload)


class KisDailyPriceClientTests(unittest.TestCase):
    def test_daily_prices_keeps_ohlcv_and_adjusted_flag(self) -> None:
        session = FakeSession(
            {
                "rt_cd": "0",
                "output2": [
                    {
                        "stck_bsop_date": "20240102",
                        "stck_oprc": "100",
                        "stck_hgpr": "110",
                        "stck_lwpr": "90",
                        "stck_clpr": "105",
                        "acml_vol": "12345",
                    }
                ],
            }
        )
        client = KisDailyPriceClient(
            KisCredentials("key", "secret"),
            session=session,
        )

        rows = client.daily_prices(
            "005930",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        self.assertEqual(rows[0]["open_price"], 100)
        self.assertEqual(rows[0]["close_price"], 105)
        self.assertEqual(rows[0]["volume"], 12345)
        self.assertTrue(rows[0]["adjusted"])

    def test_daily_index_prices_uses_official_kospi_contract(self) -> None:
        session = FakeSession(
            {
                "rt_cd": "0",
                "output2": [
                    {
                        "stck_bsop_date": "20240102",
                        "bstp_nmix_oprc": "2600.10",
                        "bstp_nmix_hgpr": "2630.20",
                        "bstp_nmix_lwpr": "2590.00",
                        "bstp_nmix_prpr": "2620.30",
                        "acml_vol": "54321",
                    }
                ],
            }
        )
        client = KisDailyPriceClient(
            KisCredentials("key", "secret"),
            session=session,
        )

        rows = client.daily_index_prices(
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        self.assertEqual(rows[0]["close_price"], 2620.3)
        call = session.get_calls[0]
        self.assertTrue(call["url"].endswith("inquire-daily-indexchartprice"))
        self.assertEqual(call["headers"]["tr_id"], "FHKUP03500100")
        self.assertEqual(call["params"]["FID_COND_MRKT_DIV_CODE"], "U")
        self.assertEqual(call["params"]["FID_INPUT_ISCD"], "0001")

    def test_daily_prices_retries_transient_server_error(self) -> None:
        session = FakeSession(
            {},
            responses=[
                FakeResponse({}, ok=False, status_code=500),
                FakeResponse({"rt_cd": "0", "output2": []}),
            ],
        )
        client = KisDailyPriceClient(
            KisCredentials("key", "secret"),
            session=session,
            max_retries=1,
            retry_backoff_seconds=0,
        )

        rows = client.daily_prices(
            "005930",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )

        self.assertEqual(rows, [])
        self.assertEqual(len(session.get_calls), 2)


if __name__ == "__main__":
    unittest.main()
