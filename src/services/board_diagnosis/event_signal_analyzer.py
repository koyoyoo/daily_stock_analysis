# -*- coding: utf-8 -*-
"""
===================================
事件催化评分器
===================================

本文件唯一职责：基于核心股事件搜索结果输出事件催化维度评分。
"""

from __future__ import annotations

from src.schemas.board_diagnosis import BoardDiagnosisDimension, BoardDiagnosisSource, BoardSignalDataStatus
from src.search_service import SearchService
from src.services.board_diagnosis.shared import AssetInsight

_POSITIVE_EVENT_TERMS = ("增持", "回购", "中标", "订单", "业绩预增", "增长", "合作", "盈利", "利好")
_NEGATIVE_EVENT_TERMS = ("减持", "诉讼", "处罚", "亏损", "下滑", "爆雷", "风险", "利空", "失速")


class EventSignalAnalyzer:
    """事件催化维度评分器。"""

    KEY = "events"
    LABEL = "事件催化"
    MAX_SCORE = 10

    def __init__(self, search_service: SearchService | None):
        self._search_service = search_service

    def analyze(self, leader_insights: list[AssetInsight]) -> BoardDiagnosisDimension:
        if self._search_service is None or not self._search_service.is_available:
            return BoardDiagnosisDimension(
                key=self.KEY,
                label=self.LABEL,
                score=0,
                max_score=self.MAX_SCORE,
                data_status=BoardSignalDataStatus.MISSING,
                summary="未配置可用搜索能力，无法评估事件催化。",
                warnings=["事件维度依赖搜索能力，当前环境未启用。"],
                sources=[
                    BoardDiagnosisSource(
                        label="核心股事件检索",
                        provider="search_service",
                        detail="需要搜索能力检索核心股近期事件，当前环境未启用。",
                    )
                ],
            )

        positive_hits = 0
        negative_hits = 0
        evidence: list[str] = []
        risks: list[str] = []

        for insight in leader_insights:
            response = self._search_service.search_stock_events(insight.asset.code, insight.stock_name)
            if not response.success or not response.results:
                continue

            text = " ".join(f"{result.title} {result.snippet}" for result in response.results[:3]).lower()
            positive_match = any(term.lower() in text for term in _POSITIVE_EVENT_TERMS)
            negative_match = any(term.lower() in text for term in _NEGATIVE_EVENT_TERMS)

            if positive_match and not negative_match:
                positive_hits += 1
                evidence.append(f"{insight.stock_name} 检索到偏正向事件线索")
            elif negative_match and not positive_match:
                negative_hits += 1
                risks.append(f"{insight.stock_name} 检索到偏负向事件线索")

        if positive_hits == 0 and negative_hits == 0:
            return BoardDiagnosisDimension(
                key=self.KEY,
                label=self.LABEL,
                score=0,
                max_score=self.MAX_SCORE,
                data_status=BoardSignalDataStatus.PARTIAL,
                summary="已执行事件检索，但未形成稳定的正负向催化结论。",
                warnings=["事件维度暂未接入公告结构化解析，仅基于搜索结果关键词判断。"],
                sources=[
                    BoardDiagnosisSource(
                        label="核心股事件检索",
                        provider="search_service",
                        detail="基于每只核心股事件搜索结果前 3 条做关键词启发式判断，未做公告级事实核验。",
                    )
                ],
            )

        score = 0
        if positive_hits >= 2:
            score += 8
        elif positive_hits == 1:
            score += 5

        if negative_hits >= 2:
            score = max(score - 4, 0)
        elif negative_hits == 1:
            score = max(score - 2, 0)

        return BoardDiagnosisDimension(
            key=self.KEY,
            label=self.LABEL,
            score=min(score, self.MAX_SCORE),
            max_score=self.MAX_SCORE,
            data_status=BoardSignalDataStatus.PARTIAL,
            summary="事件评分基于核心股事件搜索的关键词启发式判断，仅作为辅助信号。",
            evidence=evidence,
            risks=risks,
            warnings=["事件维度当前未做公告级事实核验，结果只用于辅助打分。"],
            metrics={
                "positive_hits": positive_hits,
                "negative_hits": negative_hits,
            },
            sources=[
                BoardDiagnosisSource(
                    label="核心股事件检索",
                    provider="search_service",
                    detail="基于每只核心股事件搜索结果前 3 条做关键词启发式判断，未做公告级事实核验。",
                )
            ],
        )
