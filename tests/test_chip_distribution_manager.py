# -*- coding: utf-8 -*-
"""Regression tests for chip distribution provider fallback."""

from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import patch

from data_provider.base import DataFetcherManager
from data_provider.realtime_types import ChipDistribution, get_chip_circuit_breaker


class _ChipFetcher:
    def __init__(self, name: str, priority: int, result):
        self.name = name
        self.priority = priority
        self._result = result
        self.calls = 0

    def get_chip_distribution(self, stock_code: str):
        self.calls += 1
        return self._result


def test_manager_skips_placeholder_chip_distribution_and_tries_next_fetcher():
    get_chip_circuit_breaker().reset()
    empty_chip = ChipDistribution(code="600519")
    valid_chip = ChipDistribution(
        code="600519",
        profit_ratio=0.61,
        avg_cost=12.3,
        concentration_90=0.13,
    )
    manager = DataFetcherManager(
        fetchers=[
            _ChipFetcher("EmptyFetcher", 0, empty_chip),
            _ChipFetcher("ValidFetcher", 1, valid_chip),
        ]
    )

    with patch("src.config.get_config", return_value=SimpleNamespace(enable_chip_distribution=True)):
        chip = manager.get_chip_distribution("600519")

    assert chip is valid_chip


def test_manager_accepts_zero_concentration_chip_distribution():
    get_chip_circuit_breaker().reset()
    zero_concentration_chip = ChipDistribution(
        code="600519",
        profit_ratio=0.61,
        avg_cost=12.3,
        concentration_90=0.0,
        concentration_70=0.0,
    )
    fallback_chip = ChipDistribution(
        code="600519",
        profit_ratio=0.62,
        avg_cost=12.5,
        concentration_90=0.13,
    )
    zero_fetcher = _ChipFetcher("ZeroConcentrationFetcher", 0, zero_concentration_chip)
    fallback_fetcher = _ChipFetcher("FallbackFetcher", 1, fallback_chip)
    manager = DataFetcherManager(fetchers=[zero_fetcher, fallback_fetcher])

    with patch("src.config.get_config", return_value=SimpleNamespace(enable_chip_distribution=True)):
        chip = manager.get_chip_distribution("600519")

    assert chip is zero_concentration_chip
    assert zero_fetcher.calls == 1
    assert fallback_fetcher.calls == 0


def test_manager_uses_local_chip_profile_when_all_providers_fail():
    get_chip_circuit_breaker().reset()
    manager = DataFetcherManager(fetchers=[_ChipFetcher("FailingFetcher", 0, None)])
    start = date(2026, 4, 1)
    local_bars = [
        SimpleNamespace(
            date=start + timedelta(days=index),
            high=10.8 + index * 0.25,
            low=9.7 + index * 0.25,
            close=10.3 + index * 0.25,
            volume=1_000_000 + index * 8_000,
        )
        for index in range(40)
    ]

    with (
        patch("src.config.get_config", return_value=SimpleNamespace(enable_chip_distribution=True)),
        patch("src.repositories.stock_repo.StockRepository") as stock_repo_cls,
    ):
        stock_repo_cls.return_value.get_latest.return_value = local_bars
        chip = manager.get_chip_distribution("600519")

    assert chip is not None
    assert chip.source == "local_volume_profile:time_decay"
    assert chip.code == "600519"
    assert chip.avg_cost > 0
    assert 0 <= chip.profit_ratio <= 1
