# -*- coding: utf-8 -*-
"""
===================================
板块诊断共享行情工具
===================================

本文件唯一职责：提供 ETF 板块诊断共用的行情快照加载与基础指标计算工具。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import mean
from typing import Any, Optional

from src.schemas.board_diagnosis import BoardAssetRef
from src.services.stock_service import StockService


def _safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def _moving_average(values: list[float], window: int) -> Optional[float]:
    if len(values) < window:
        return None
    return mean(values[-window:])


def _positive_amounts(values: list[Optional[float]]) -> list[float]:
    return [value for value in values if value is not None and value > 0]


@dataclass(slots=True)
class AssetInsight:
    """单个资产的日线级快照。"""

    asset: BoardAssetRef
    stock_name: str
    current_price: Optional[float]
    change_pct: Optional[float]
    ma5: Optional[float]
    ma10: Optional[float]
    ma20: Optional[float]
    ma60: Optional[float]
    return_5d: Optional[float]
    return_10d: Optional[float]
    latest_amount: Optional[float]
    avg_amount_5d: Optional[float]
    amount_ratio_5d: Optional[float]
    history_size: int
    warnings: list[str] = field(default_factory=list)

    @property
    def has_minimum_history(self) -> bool:
        return self.history_size >= 20 and self.current_price is not None and self.ma20 is not None

    @property
    def has_long_history(self) -> bool:
        return self.history_size >= 60 and self.ma60 is not None

    @property
    def ma_bullish(self) -> bool:
        return all(value is not None for value in (self.ma5, self.ma10, self.ma20)) and (
            self.ma5 > self.ma10 > self.ma20
        )

    @property
    def above_ma20(self) -> bool:
        return self.current_price is not None and self.ma20 is not None and self.current_price >= self.ma20

    @property
    def above_ma60(self) -> bool:
        return self.current_price is not None and self.ma60 is not None and self.current_price >= self.ma60


def load_asset_insight(
    stock_service: StockService,
    asset: BoardAssetRef,
    *,
    history_days: int = 90,
) -> AssetInsight:
    """
    读取单个资产的日线级快照。

    参数：
        stock_service: 数据服务实例。
        asset: 资产引用。
        history_days: 历史窗口大小，推荐值：60-120。

    返回：
        AssetInsight：标准化后的行情快照。

    异常：
        本函数不主动抛出外部数据异常；数据缺失时通过 warnings 显式暴露。
    """
    history_payload = stock_service.get_history_data(asset.code, days=history_days)
    rows = history_payload.get("data") if isinstance(history_payload, dict) else None
    rows = rows if isinstance(rows, list) else []

    closes = [_safe_float(row.get("close")) for row in rows]
    closes = [value for value in closes if value is not None]
    amounts = [_safe_float(row.get("amount")) for row in rows]

    quote = stock_service.get_realtime_quote(asset.code) or {}
    current_price = _safe_float(quote.get("current_price"))
    if current_price is None and closes:
        current_price = closes[-1]

    change_pct = _safe_float(quote.get("change_percent"))
    if change_pct is None and rows:
        change_pct = _safe_float(rows[-1].get("change_percent"))

    ma5 = _moving_average(closes, 5)
    ma10 = _moving_average(closes, 10)
    ma20 = _moving_average(closes, 20)
    ma60 = _moving_average(closes, 60)

    latest_amount = _safe_float(rows[-1].get("amount")) if rows else None
    recent_amounts = _positive_amounts(amounts[-6:-1]) if len(amounts) >= 6 else _positive_amounts(amounts[:-1])
    avg_amount_5d = mean(recent_amounts) if recent_amounts else None
    amount_ratio_5d = None
    if latest_amount is not None and avg_amount_5d is not None and avg_amount_5d > 0:
        amount_ratio_5d = latest_amount / avg_amount_5d

    return_5d = None
    if len(closes) >= 6 and closes[-6] > 0:
        return_5d = (closes[-1] - closes[-6]) / closes[-6] * 100

    return_10d = None
    if len(closes) >= 11 and closes[-11] > 0:
        return_10d = (closes[-1] - closes[-11]) / closes[-11] * 100

    warnings: list[str] = []
    if len(closes) < 20:
        warnings.append(f"{asset.name} 日线不足 20 根，无法完成稳定趋势判断")
    if latest_amount is None:
        warnings.append(f"{asset.name} 缺少最新成交额数据")

    stock_name = history_payload.get("stock_name") if isinstance(history_payload, dict) else None
    display_name = str(stock_name or asset.name or asset.code).strip()

    return AssetInsight(
        asset=asset,
        stock_name=display_name,
        current_price=current_price,
        change_pct=change_pct,
        ma5=ma5,
        ma10=ma10,
        ma20=ma20,
        ma60=ma60,
        return_5d=return_5d,
        return_10d=return_10d,
        latest_amount=latest_amount,
        avg_amount_5d=avg_amount_5d,
        amount_ratio_5d=amount_ratio_5d,
        history_size=len(closes),
        warnings=warnings,
    )
