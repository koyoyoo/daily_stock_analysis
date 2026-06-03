# -*- coding: utf-8 -*-
"""
本文件唯一职责：基于本地日线 K 线计算可复用的筹码峰分布指标。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Literal, Mapping, Sequence

import numpy as np

from data_provider.realtime_types import ChipDistribution

ChipProfileAlgorithm: type = Literal["fixed_window", "time_decay"]

FIXED_WINDOW_ALGORITHM: ChipProfileAlgorithm = "fixed_window"
TIME_DECAY_ALGORITHM: ChipProfileAlgorithm = "time_decay"
DEFAULT_CHIP_PROFILE_ALGORITHM: ChipProfileAlgorithm = TIME_DECAY_ALGORITHM
DEFAULT_CHIP_PROFILE_BINS = 100
DEFAULT_CHIP_PROFILE_LOOKBACK_BARS = 90
DEFAULT_CHIP_PROFILE_HALF_LIFE_DAYS = 20.0
MIN_CHIP_PROFILE_BARS = 30

_DATE_FIELDS = ("trade_date", "date", "日期")
_HIGH_FIELDS = ("high", "最高")
_LOW_FIELDS = ("low", "最低")
_CLOSE_FIELDS = ("close", "收盘")
_VOLUME_FIELDS = ("volume", "成交量")


@dataclass(frozen=True)
class DailyPriceVolumeBar:
    """标准化后的单根日线输入。"""

    trade_date: date
    high: float
    low: float
    close: float
    volume: float


def build_chip_distribution_from_bars(
    *,
    stock_code: str,
    bars: Sequence[Mapping[str, Any] | Any],
    algorithm: ChipProfileAlgorithm = DEFAULT_CHIP_PROFILE_ALGORITHM,
    bins: int = DEFAULT_CHIP_PROFILE_BINS,
    half_life_days: float = DEFAULT_CHIP_PROFILE_HALF_LIFE_DAYS,
    source: str | None = None,
) -> ChipDistribution:
    """
    用途：基于日线 K 线计算筹码分布。

    参数：
    - stock_code: 股票代码；必填。
    - bars: 日线序列；推荐值：30-120 根，少于 30 根直接快速失败。
    - algorithm: `fixed_window` 或 `time_decay`；推荐值：`time_decay`。
    - bins: 价格切片数量；推荐值：50-120。
    - half_life_days: 时间衰减半衰期；推荐值：10-40，仅 `time_decay` 生效。
    - source: 返回对象的数据来源标记；留空时自动生成。

    返回：
    - ChipDistribution: 与现有分析链路兼容的筹码对象。

    异常：
    - ValueError: 输入样本不足、价格区间非法或参数越界时抛出。
    - TypeError: 输入记录缺少关键字段时抛出。
    """
    normalized_bars = _normalize_bars(bars)
    if len(normalized_bars) < MIN_CHIP_PROFILE_BARS:
        raise ValueError(
            f"at least {MIN_CHIP_PROFILE_BARS} daily bars are required, got {len(normalized_bars)}"
        )
    if bins < 10:
        raise ValueError(f"bins must be >= 10, got {bins}")
    if algorithm == TIME_DECAY_ALGORITHM and half_life_days <= 0:
        raise ValueError(f"half_life_days must be > 0, got {half_life_days}")

    sorted_bars = sorted(normalized_bars, key=lambda item: item.trade_date)
    metrics = _calculate_metrics(
        sorted_bars,
        algorithm=algorithm,
        bins=bins,
        half_life_days=half_life_days,
    )
    latest_bar = sorted_bars[-1]
    resolved_source = source or f"local_volume_profile:{algorithm}"
    return ChipDistribution(
        code=stock_code,
        date=latest_bar.trade_date.isoformat(),
        source=resolved_source,
        profit_ratio=metrics["profit_ratio"],
        avg_cost=metrics["avg_cost"],
        cost_90_low=metrics["cost_90_low"],
        cost_90_high=metrics["cost_90_high"],
        concentration_90=metrics["concentration_90"],
        cost_70_low=metrics["cost_70_low"],
        cost_70_high=metrics["cost_70_high"],
        concentration_70=metrics["concentration_70"],
    )


def build_chip_distributions_for_all_algorithms(
    *,
    stock_code: str,
    bars: Sequence[Mapping[str, Any] | Any],
    bins: int = DEFAULT_CHIP_PROFILE_BINS,
    half_life_days: float = DEFAULT_CHIP_PROFILE_HALF_LIFE_DAYS,
) -> dict[ChipProfileAlgorithm, ChipDistribution]:
    """
    用途：一次性输出固定周期版与时间衰减版筹码结果，便于比较口径差异。

    参数：
    - stock_code: 股票代码；必填。
    - bars: 日线序列；推荐值：30-120 根。
    - bins: 价格切片数量；推荐值：50-120。
    - half_life_days: 时间衰减半衰期；推荐值：10-40。

    返回：
    - dict: `fixed_window` 与 `time_decay` 两套 ChipDistribution。

    异常：
    - ValueError/TypeError: 透传自 `build_chip_distribution_from_bars`。
    """
    return {
        FIXED_WINDOW_ALGORITHM: build_chip_distribution_from_bars(
            stock_code=stock_code,
            bars=bars,
            algorithm=FIXED_WINDOW_ALGORITHM,
            bins=bins,
            half_life_days=half_life_days,
        ),
        TIME_DECAY_ALGORITHM: build_chip_distribution_from_bars(
            stock_code=stock_code,
            bars=bars,
            algorithm=TIME_DECAY_ALGORITHM,
            bins=bins,
            half_life_days=half_life_days,
        ),
    }


def _normalize_bars(bars: Sequence[Mapping[str, Any] | Any]) -> list[DailyPriceVolumeBar]:
    normalized: list[DailyPriceVolumeBar] = []
    for raw in bars:
        trade_date = _coerce_date(_extract_field(raw, _DATE_FIELDS))
        high = _coerce_positive_float(_extract_field(raw, _HIGH_FIELDS), "high")
        low = _coerce_positive_float(_extract_field(raw, _LOW_FIELDS), "low")
        close = _coerce_positive_float(_extract_field(raw, _CLOSE_FIELDS), "close")
        volume = _coerce_non_negative_float(_extract_field(raw, _VOLUME_FIELDS), "volume")
        if high < low:
            raise ValueError(f"high must be >= low, got high={high}, low={low}")
        normalized.append(
            DailyPriceVolumeBar(
                trade_date=trade_date,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
        )
    return normalized


def _extract_field(record: Mapping[str, Any] | Any, field_names: tuple[str, ...]) -> Any:
    if isinstance(record, Mapping):
        for field_name in field_names:
            if field_name in record:
                return record[field_name]
    else:
        for field_name in field_names:
            if hasattr(record, field_name):
                return getattr(record, field_name)
    raise TypeError(f"missing required field, expected one of {field_names}")


def _coerce_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError("trade_date must not be empty")
        try:
            return date.fromisoformat(text[:10])
        except ValueError as exc:
            raise ValueError(f"invalid trade_date: {value}") from exc
    raise TypeError(f"unsupported trade_date type: {type(value)!r}")


def _coerce_positive_float(value: Any, field_name: str) -> float:
    numeric = float(value)
    if not np.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"{field_name} must be > 0, got {value}")
    return numeric


def _coerce_non_negative_float(value: Any, field_name: str) -> float:
    numeric = float(value)
    if not np.isfinite(numeric) or numeric < 0:
        raise ValueError(f"{field_name} must be >= 0, got {value}")
    return numeric


def _calculate_metrics(
    bars: Sequence[DailyPriceVolumeBar],
    *,
    algorithm: ChipProfileAlgorithm,
    bins: int,
    half_life_days: float,
) -> dict[str, float]:
    highs = np.array([bar.high for bar in bars], dtype=float)
    lows = np.array([bar.low for bar in bars], dtype=float)
    closes = np.array([bar.close for bar in bars], dtype=float)
    volumes = np.array([bar.volume for bar in bars], dtype=float)
    dates = np.array([np.datetime64(bar.trade_date.isoformat()) for bar in bars])

    min_price = float(lows.min())
    max_price = float(highs.max())
    if max_price < min_price:
        raise ValueError(f"invalid price range: min={min_price}, max={max_price}")
    if max_price == min_price:
        max_price += 0.01

    price_bins = np.linspace(min_price, max_price, bins + 1)
    bin_centers = (price_bins[:-1] + price_bins[1:]) / 2
    profile = np.zeros(bins, dtype=float)
    latest_date = dates[-1]

    # 时间复杂度 O(n * bins)，空间复杂度 O(bins)。
    for index, bar in enumerate(bars):
        effective_volume = volumes[index] * _resolve_weight(
            algorithm=algorithm,
            latest_date=latest_date,
            bar_date=dates[index],
            half_life_days=half_life_days,
        )
        if bar.high == bar.low:
            bucket_index = int(np.digitize(bar.high, price_bins) - 1)
            bucket_index = max(0, min(bucket_index, bins - 1))
            profile[bucket_index] += effective_volume
            continue

        overlap = np.minimum(bar.high, price_bins[1:]) - np.maximum(bar.low, price_bins[:-1])
        overlap = np.clip(overlap, 0.0, None)
        overlap_sum = float(overlap.sum())
        if overlap_sum <= 0:
            bucket_index = int(np.digitize((bar.high + bar.low) / 2, price_bins) - 1)
            bucket_index = max(0, min(bucket_index, bins - 1))
            profile[bucket_index] += effective_volume
            continue
        profile += effective_volume * overlap / overlap_sum

    total_volume = float(profile.sum())
    if total_volume <= 0:
        raise ValueError("volume profile sum must be positive")

    norm_percent = profile / total_volume * 100.0
    cumsum = np.cumsum(norm_percent)
    current_price = float(closes[-1])
    winner_rate = float(norm_percent[bin_centers <= current_price].sum()) / 100.0
    avg_cost = float(np.average(bin_centers, weights=norm_percent))

    def percentile_price(target_pct: float) -> float:
        bucket_index = int(np.searchsorted(cumsum, target_pct, side="left"))
        bucket_index = min(bucket_index, len(bin_centers) - 1)
        return float(bin_centers[bucket_index])

    cost_90_low = percentile_price(5.0)
    cost_90_high = percentile_price(95.0)
    cost_70_low = percentile_price(15.0)
    cost_70_high = percentile_price(85.0)

    return {
        "profit_ratio": round(winner_rate, 4),
        "avg_cost": round(avg_cost, 4),
        "cost_90_low": round(cost_90_low, 4),
        "cost_90_high": round(cost_90_high, 4),
        "concentration_90": round(_concentration(cost_90_low, cost_90_high), 4),
        "cost_70_low": round(cost_70_low, 4),
        "cost_70_high": round(cost_70_high, 4),
        "concentration_70": round(_concentration(cost_70_low, cost_70_high), 4),
    }


def _resolve_weight(
    *,
    algorithm: ChipProfileAlgorithm,
    latest_date: np.datetime64,
    bar_date: np.datetime64,
    half_life_days: float,
) -> float:
    match algorithm:
        case "fixed_window":
            return 1.0
        case "time_decay":
            age_days = max(int((latest_date - bar_date) / np.timedelta64(1, "D")), 0)
            return float(0.5 ** (age_days / half_life_days))
        case _:
            raise ValueError(f"unsupported chip profile algorithm: {algorithm}")


def _concentration(low: float, high: float) -> float:
    denominator = low + high
    if denominator == 0:
        return 0.0
    return float((high - low) / denominator)
