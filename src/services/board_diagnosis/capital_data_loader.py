# -*- coding: utf-8 -*-
"""
===================================
板块诊断资金数据加载器
===================================

本文件唯一职责：为 ETF 板块诊断加载真实资金维度增强数据，包括 ETF 份额变化、板块成交额和市场总成交额。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from data_provider.base import DataFetcherManager
from src.schemas.board_diagnosis import BoardDefinition


@dataclass(slots=True)
class EtfShareChangeSnapshot:
    """ETF 份额变化快照。"""

    latest_share: float
    previous_share: float
    change: float
    change_pct: float
    trade_date: str
    previous_trade_date: str
    unit: str
    source: Optional[str] = None


@dataclass(slots=True)
class SectorTurnoverSnapshot:
    """板块成交额快照。"""

    sector_name: str
    amount: float
    change_pct: Optional[float]
    total_market_amount: Optional[float]
    turnover_share_pct: Optional[float]
    source: Optional[str] = None


@dataclass(slots=True)
class CapitalSupportSnapshot:
    """资金维度附加支持数据。"""

    etf_share: Optional[EtfShareChangeSnapshot] = None
    sector_turnover: Optional[SectorTurnoverSnapshot] = None
    warnings: list[str] = field(default_factory=list)


class BoardCapitalDataLoader:
    """
    板块诊断资金数据加载器。

    用途：
        统一从 DataFetcherManager 加载 ETF 份额变化和板块成交额快照。
    """

    def __init__(self, data_manager: DataFetcherManager | None = None):
        self._data_manager = data_manager or DataFetcherManager()

    def load(self, definition: BoardDefinition) -> CapitalSupportSnapshot:
        snapshot = CapitalSupportSnapshot()

        share_payload = self._data_manager.get_etf_share_change(definition.primary_etf.code, lookback_days=10)
        if share_payload:
            snapshot.etf_share = EtfShareChangeSnapshot(
                latest_share=float(share_payload["latest_share"]),
                previous_share=float(share_payload["previous_share"]),
                change=float(share_payload["change"]),
                change_pct=float(share_payload["change_pct"]),
                trade_date=str(share_payload["trade_date"]),
                previous_trade_date=str(share_payload["previous_trade_date"]),
                unit=str(share_payload.get("unit") or "unknown"),
                source=str(share_payload.get("source")) if share_payload.get("source") else None,
            )
        else:
            snapshot.warnings.append("未获取到 ETF 份额变化数据")

        market_stats = self._data_manager.get_market_stats() or {}
        total_market_amount = market_stats.get("total_amount")
        total_market_amount = float(total_market_amount) if isinstance(total_market_amount, (int, float)) else None

        sector_payload = self._data_manager.get_sector_snapshot(definition.sector_names)
        if sector_payload:
            amount = float(sector_payload["amount"])
            turnover_share_pct = None
            if total_market_amount and total_market_amount > 0:
                turnover_share_pct = amount / total_market_amount * 100

            change_pct = sector_payload.get("change_pct")
            snapshot.sector_turnover = SectorTurnoverSnapshot(
                sector_name=str(sector_payload["name"]),
                amount=amount,
                change_pct=float(change_pct) if isinstance(change_pct, (int, float)) else None,
                total_market_amount=total_market_amount,
                turnover_share_pct=turnover_share_pct,
                source=str(sector_payload.get("source")) if sector_payload.get("source") else None,
            )
        else:
            snapshot.warnings.append("未获取到板块成交额快照")

        return snapshot
