# -*- coding: utf-8 -*-
"""
===================================
板块情绪评分器
===================================

本文件唯一职责：基于指数与核心股一致性输出板块情绪代理评分，并显式标记为估算结果。
"""

from __future__ import annotations

from src.schemas.board_diagnosis import BoardDiagnosisDimension, BoardDiagnosisSource, BoardSignalDataStatus
from src.services.board_diagnosis.shared import AssetInsight


class SentimentSignalAnalyzer:
    """板块情绪代理评分器。"""

    KEY = "sentiment"
    LABEL = "板块情绪"
    MAX_SCORE = 20

    def analyze(self, etf_insight: AssetInsight, index_insight: AssetInsight, leader_insights: list[AssetInsight]) -> BoardDiagnosisDimension:
        available_leaders = [item for item in leader_insights if item.has_minimum_history]
        if not available_leaders or not index_insight.has_minimum_history:
            warnings = [warning for item in leader_insights for warning in item.warnings]
            warnings.extend(index_insight.warnings)
            return BoardDiagnosisDimension(
                key=self.KEY,
                label=self.LABEL,
                score=0,
                max_score=self.MAX_SCORE,
                data_status=BoardSignalDataStatus.MISSING,
                summary="缺少核心指数或龙头样本，无法估算板块情绪。",
                warnings=warnings,
                sources=[
                    BoardDiagnosisSource(
                        label="指数 + 3 只核心股代理情绪",
                        provider="proxy_estimation",
                        detail="基于板块指数、ETF 与 3 只核心股的一致性估算板块情绪，不是真实全板块统计。",
                    )
                ],
            )

        positive_change_count = sum(1 for item in available_leaders if (item.change_pct or 0) > 0)
        bullish_count = sum(1 for item in available_leaders if item.ma_bullish)

        score = 0
        evidence: list[str] = []
        risks: list[str] = []

        if positive_change_count >= 2:
            score += 8
            evidence.append(f"{positive_change_count}/3 核心股当日为正，短线情绪未散")
        else:
            risks.append("核心股上涨家数不足 2 只，情绪扩散度不足")

        if bullish_count >= 2:
            score += 6
            evidence.append(f"{bullish_count}/3 核心股维持多头排列")
        else:
            risks.append("核心股趋势分化，情绪延续性一般")

        etf_positive = (etf_insight.change_pct or 0) > 0
        index_positive = (index_insight.change_pct or 0) > 0
        if etf_positive and index_positive:
            score += 3
            evidence.append("ETF 与板块指数同向走强")
        elif etf_insight.change_pct is not None and index_insight.change_pct is not None:
            risks.append("ETF 与指数方向不完全一致，需警惕结构性背离")

        if positive_change_count == 3 and bullish_count == 3:
            score += 3
            evidence.append("前排一致性较高，情绪代理信号偏强")

        return BoardDiagnosisDimension(
            key=self.KEY,
            label=self.LABEL,
            score=min(score, self.MAX_SCORE),
            max_score=self.MAX_SCORE,
            data_status=BoardSignalDataStatus.ESTIMATED,
            summary="当前情绪评分基于指数与 3 只核心股的代理一致性，并非真实全板块涨跌家数统计。",
            evidence=evidence,
            risks=risks,
            warnings=["情绪维度暂未接入真实板块涨跌家数与热度排行，仅提供代理估算。"] + etf_insight.warnings,
            metrics={
                "positive_change_count": positive_change_count,
                "bullish_count": bullish_count,
                "etf_change_pct": etf_insight.change_pct,
                "index_change_pct": index_insight.change_pct,
            },
            sources=[
                BoardDiagnosisSource(
                    label="指数 + 3 只核心股代理情绪",
                    provider="proxy_estimation",
                    detail="基于 ETF、板块指数和 3 只核心股的一致性估算情绪，暂未接入真实涨跌家数与热度排行。",
                )
            ],
        )
