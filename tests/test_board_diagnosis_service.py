# -*- coding: utf-8 -*-
"""Regression tests for ETF board diagnosis service MVP contracts."""

from __future__ import annotations

import unittest

from src.schemas.board_diagnosis import BoardAssetRef, BoardAssetRole, BoardDefinition
from src.services.board_diagnosis.capital_data_loader import (
    CapitalSupportSnapshot,
    EtfShareChangeSnapshot,
    SectorTurnoverSnapshot,
)
from src.services.board_diagnosis.board_registry import BoardRegistry
from src.services.board_diagnosis.service import BoardDiagnosisService


class _FakeStockService:
    def __init__(self) -> None:
        self._payloads = {
            "159755": self._build_history("新能源车ETF", 100.0, 0.8),
            "399808": self._build_history("新能源车指数", 3000.0, 20.0),
            "300750": self._build_history("宁德时代", 200.0, 8.0),
            "002594": self._build_history("比亚迪", 250.0, 6.0),
            "300274": self._build_history("阳光电源", 180.0, 5.0),
        }

    @staticmethod
    def _build_history(name: str, start_price: float, amount_scale: float) -> dict:
        data = []
        for day in range(90):
            close = start_price + day * 1.2
            data.append(
                {
                    "date": f"2026-01-{(day % 28) + 1:02d}",
                    "open": close - 0.8,
                    "high": close + 1.0,
                    "low": close - 1.0,
                    "close": close,
                    "volume": 1000000 + day * 1000,
                    "amount": (10_000_000 + day * 300_000) * amount_scale,
                    "change_percent": 1.2,
                }
            )
        return {"stock_name": name, "data": data}

    def get_history_data(self, stock_code: str, period: str = "daily", days: int = 30) -> dict:
        return self._payloads[stock_code]

    def get_realtime_quote(self, stock_code: str) -> dict:
        last_row = self._payloads[stock_code]["data"][-1]
        return {
            "stock_code": stock_code,
            "stock_name": self._payloads[stock_code]["stock_name"],
            "current_price": last_row["close"],
            "change_percent": last_row["change_percent"],
            "amount": last_row["amount"],
        }


class _FakeCapitalLoader:
    def load(self, _definition: BoardDefinition) -> CapitalSupportSnapshot:
        return CapitalSupportSnapshot(
            etf_share=EtfShareChangeSnapshot(
                latest_share=1050.0,
                previous_share=1000.0,
                change=50.0,
                change_pct=5.0,
                trade_date="20260603",
                previous_trade_date="20260602",
                unit="万份",
                source="tushare.fund_share",
            ),
            sector_turnover=SectorTurnoverSnapshot(
                sector_name="新能源车",
                amount=860.0,
                change_pct=2.8,
                total_market_amount=12000.0,
                turnover_share_pct=7.1667,
                source="fake",
            ),
        )


class BoardDiagnosisServiceTestCase(unittest.TestCase):
    def setUp(self) -> None:
        definition = BoardDefinition(
            board_key="new_energy",
            board_name="新能源",
            primary_etf=BoardAssetRef(code="159755", name="新能源车ETF", role=BoardAssetRole.ETF),
            benchmark_index=BoardAssetRef(code="399808", name="新能源车指数", role=BoardAssetRole.INDEX),
            leaders=[
                BoardAssetRef(code="300750", name="宁德时代", role=BoardAssetRole.LEADER),
                BoardAssetRef(code="002594", name="比亚迪", role=BoardAssetRole.CORE),
                BoardAssetRef(code="300274", name="阳光电源", role=BoardAssetRole.CORE),
            ],
        )
        self.registry = BoardRegistry(definitions=(definition,))
        self.service = BoardDiagnosisService(
            stock_service=_FakeStockService(),
            search_service=None,
            registry=self.registry,
            capital_data_loader=_FakeCapitalLoader(),
        )

    def test_list_boards_returns_summary(self) -> None:
        boards = self.service.list_boards()
        self.assertEqual(len(boards), 1)
        self.assertEqual(boards[0].board_key, "new_energy")
        self.assertEqual(len(boards[0].leaders), 3)

    def test_diagnose_returns_structured_result(self) -> None:
        result = self.service.diagnose("new_energy")

        self.assertEqual(result.board_key, "new_energy")
        self.assertEqual(result.action.value, "buy")
        self.assertGreaterEqual(result.score, 80)
        self.assertEqual(len(result.dimensions), 5)
        self.assertIn("index", result.dimension_scores)
        self.assertIn("leaders", result.dimension_scores)
        self.assertGreater(result.dimension_scores["capital"], 0)
        self.assertEqual(result.dimensions[-1].key, "events")
        self.assertEqual(result.dimensions[-1].score, 0)
        capital_dimension = next(item for item in result.dimensions if item.key == "capital")
        self.assertGreaterEqual(len(capital_dimension.sources), 2)
        self.assertEqual(capital_dimension.sources[1].provider, "tushare.fund_share")
        self.assertEqual(capital_dimension.sources[1].range_start, "20260602")
        self.assertEqual(capital_dimension.sources[1].range_end, "20260603")
        self.assertTrue(result.summary)

    def test_diagnose_unknown_board_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.service.diagnose("unknown")
