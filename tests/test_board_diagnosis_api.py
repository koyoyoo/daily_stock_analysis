# -*- coding: utf-8 -*-
"""Regression tests for ETF board diagnosis API helpers."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from tests.litellm_stub import ensure_litellm_stub

ensure_litellm_stub()

try:
    from api.v1.endpoints.board_diagnosis import diagnose_board
except Exception:  # pragma: no cover - optional dependency environments
    diagnose_board = None


class BoardDiagnosisApiTestCase(unittest.TestCase):
    def test_diagnose_board_returns_404_for_unknown_board(self) -> None:
        if diagnose_board is None:
            self.skipTest("board diagnosis endpoint unavailable in this environment")

        with patch("api.v1.endpoints.board_diagnosis.BoardDiagnosisService") as service_cls:
            service_cls.return_value.diagnose.side_effect = ValueError("未找到板块配置: unknown")
            with self.assertRaises(Exception) as ctx:
                diagnose_board("unknown")

        self.assertEqual(getattr(ctx.exception, "status_code", None), 404)
