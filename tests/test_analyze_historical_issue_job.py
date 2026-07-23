from __future__ import annotations

import unittest

from collector.jobs.analyze_historical_issue import (
    _diagnostic_output,
    _failure_payload,
    _json_output,
)


class HistoricalIssueJobFailureTests(unittest.TestCase):
    def test_reports_missing_supabase_configuration_without_secret_values(self) -> None:
        payload = _failure_payload(
            RuntimeError(
                "SUPABASE_DB_URL에 유효한 Postgres 연결 문자열이 필요합니다."
            )
        )

        self.assertEqual(payload["errorCode"], "collector_configuration_missing")
        self.assertIn("SUPABASE_DB_URL", payload["error"])

    def test_reports_missing_naver_configuration(self) -> None:
        payload = _failure_payload(
            RuntimeError(
                ".env에 NAVER_CLIENT_ID와 NAVER_CLIENT_SECRET을 설정해 주세요."
            )
        )

        self.assertEqual(payload["errorCode"], "collector_configuration_missing")
        self.assertIn("NAVER_CLIENT_ID", payload["error"])

    def test_hides_unexpected_internal_error_details(self) -> None:
        payload = _failure_payload(
            RuntimeError("database password was accidentally included")
        )

        self.assertEqual(payload["errorCode"], "analysis_failed")
        self.assertNotIn("password", payload["error"])

    def test_json_output_is_safe_for_windows_cp949_console(self) -> None:
        output = _json_output(
            {
                "success": True,
                "data": {"title": "삼성전자⋯과거 유사 이슈"},
            }
        )

        encoded = output.encode("cp949")
        self.assertIn(b"\\u22ef", encoded)

    def test_diagnostic_output_exposes_type_but_not_error_message(self) -> None:
        output = _diagnostic_output(
            RuntimeError("database password was accidentally included")
        )

        self.assertIn("RuntimeError", output)
        self.assertNotIn("password", output)


if __name__ == "__main__":
    unittest.main()
