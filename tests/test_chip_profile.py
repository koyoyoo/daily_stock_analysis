# -*- coding: utf-8 -*-
"""Regression tests for local chip profile calculation."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.utils.chip_profile import (
    FIXED_WINDOW_ALGORITHM,
    TIME_DECAY_ALGORITHM,
    build_chip_distribution_from_bars,
    build_chip_distributions_for_all_algorithms,
)


def _make_bars(total: int = 40) -> list[dict[str, object]]:
    start = date(2026, 4, 1)
    bars: list[dict[str, object]] = []
    for index in range(total):
        base_price = 10.0 + index * 0.3
        bars.append(
            {
                "date": (start + timedelta(days=index)).isoformat(),
                "high": base_price + 0.9,
                "low": base_price - 0.6,
                "close": base_price + 0.4,
                "volume": 1_000_000 + index * 5_000,
            }
        )
    return bars


def test_build_chip_distribution_from_bars_supports_fixed_and_decay_algorithms():
    bars = _make_bars()

    fixed_chip = build_chip_distribution_from_bars(
        stock_code="002015",
        bars=bars,
        algorithm=FIXED_WINDOW_ALGORITHM,
    )
    decay_chip = build_chip_distribution_from_bars(
        stock_code="002015",
        bars=bars,
        algorithm=TIME_DECAY_ALGORITHM,
        half_life_days=15.0,
    )

    assert fixed_chip.code == "002015"
    assert decay_chip.code == "002015"
    assert fixed_chip.source == "local_volume_profile:fixed_window"
    assert decay_chip.source == "local_volume_profile:time_decay"
    assert fixed_chip.avg_cost > 0
    assert decay_chip.avg_cost > fixed_chip.avg_cost
    assert 0 <= fixed_chip.profit_ratio <= 1
    assert 0 <= decay_chip.profit_ratio <= 1
    assert fixed_chip.concentration_90 >= 0
    assert decay_chip.concentration_90 >= 0


def test_build_chip_distributions_for_all_algorithms_returns_both_profiles():
    profiles = build_chip_distributions_for_all_algorithms(
        stock_code="002015",
        bars=_make_bars(),
        half_life_days=20.0,
    )

    assert set(profiles.keys()) == {"fixed_window", "time_decay"}
    assert profiles["fixed_window"].date == profiles["time_decay"].date


def test_build_chip_distribution_from_bars_fails_fast_when_history_is_insufficient():
    with pytest.raises(ValueError, match="at least 30 daily bars"):
        build_chip_distribution_from_bars(
            stock_code="002015",
            bars=_make_bars(total=10),
            algorithm=TIME_DECAY_ALGORITHM,
        )
