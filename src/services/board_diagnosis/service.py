# -*- coding: utf-8 -*-
"""
===================================
板块诊断服务
===================================

本文件唯一职责：编排板块配置、行情加载、维度评分与最终决策汇总，输出 ETF 板块诊断结果。
"""

from __future__ import annotations

import logging

from src.schemas.board_diagnosis import BoardDefinitionSummary, BoardDiagnosisResult
from src.search_service import SearchService, get_search_service
from src.services.board_diagnosis.board_registry import BoardRegistry
from src.services.board_diagnosis.capital_data_loader import BoardCapitalDataLoader
from src.services.board_diagnosis.capital_signal_analyzer import CapitalSignalAnalyzer
from src.services.board_diagnosis.decision_scorer import DecisionScorer
from src.services.board_diagnosis.event_signal_analyzer import EventSignalAnalyzer
from src.services.board_diagnosis.explanation_renderer import ExplanationRenderer
from src.services.board_diagnosis.index_signal_analyzer import IndexSignalAnalyzer
from src.services.board_diagnosis.leader_signal_analyzer import LeaderSignalAnalyzer
from src.services.board_diagnosis.sentiment_signal_analyzer import SentimentSignalAnalyzer
from src.services.board_diagnosis.shared import load_asset_insight
from src.services.stock_service import StockService

logger = logging.getLogger(__name__)


class BoardDiagnosisService:
    """
    ETF 板块诊断服务。

    用途：
        输出单个板块对应 ETF 的结构化评分与动作建议。

    异常：
        `diagnose()` 在板块不存在时抛出 `ValueError`。
    """

    def __init__(
        self,
        *,
        stock_service: StockService | None = None,
        search_service: SearchService | None = None,
        registry: BoardRegistry | None = None,
        capital_data_loader: BoardCapitalDataLoader | None = None,
    ):
        self._stock_service = stock_service or StockService()
        self._registry = registry or BoardRegistry()
        self._capital_data_loader = capital_data_loader or BoardCapitalDataLoader()
        if search_service is None:
            try:
                search_service = get_search_service()
            except Exception as exc:  # noqa: BLE001 - 搜索不可用不应阻断服务初始化
                logger.warning("初始化板块诊断搜索服务失败，将跳过事件维度增强: %s", exc, exc_info=True)
                search_service = None
        self._search_service = search_service

        self._index_analyzer = IndexSignalAnalyzer()
        self._leader_analyzer = LeaderSignalAnalyzer()
        self._sentiment_analyzer = SentimentSignalAnalyzer()
        self._capital_analyzer = CapitalSignalAnalyzer()
        self._event_analyzer = EventSignalAnalyzer(self._search_service)
        self._decision_scorer = DecisionScorer()
        self._renderer = ExplanationRenderer()

    def list_boards(self) -> list[BoardDefinitionSummary]:
        """返回所有可用板块摘要。"""
        return self._registry.list_summaries()

    def diagnose(self, board_key: str) -> BoardDiagnosisResult:
        """
        执行单个板块诊断。

        参数：
            board_key: 板块唯一键，推荐值：注册表中存在的 key。

        返回：
            BoardDiagnosisResult：结构化板块诊断结果。

        异常：
            ValueError：当板块配置不存在时抛出。
        """
        definition = self._registry.get(board_key)
        etf_insight = load_asset_insight(self._stock_service, definition.primary_etf)
        index_insight = load_asset_insight(self._stock_service, definition.benchmark_index)
        leader_insights = [load_asset_insight(self._stock_service, asset) for asset in definition.leaders]
        capital_support = self._capital_data_loader.load(definition)

        dimensions = [
            self._index_analyzer.analyze(index_insight),
            self._leader_analyzer.analyze(leader_insights),
            self._sentiment_analyzer.analyze(etf_insight, index_insight, leader_insights),
            self._capital_analyzer.analyze(etf_insight, leader_insights, capital_support),
            self._event_analyzer.analyze(leader_insights),
        ]

        score, action, action_label, confidence, confidence_label = self._decision_scorer.score(dimensions)
        summary, reasons, risks, warnings = self._renderer.render(action=action, dimensions=dimensions)

        return BoardDiagnosisResult(
            board_key=definition.board_key,
            board_name=definition.board_name,
            market=definition.market,
            primary_etf=definition.primary_etf,
            benchmark_index=definition.benchmark_index,
            leaders=definition.leaders,
            score=score,
            action=action,
            action_label=action_label,
            confidence=confidence,
            confidence_label=confidence_label,
            summary=summary,
            reasons=reasons,
            risks=risks,
            warnings=warnings,
            dimension_scores={dimension.key: dimension.score for dimension in dimensions},
            dimensions=dimensions,
        )
