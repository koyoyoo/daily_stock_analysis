# -*- coding: utf-8 -*-
"""
===================================
龙头共振评分器
===================================

本文件唯一职责：根据 3 只核心股的趋势与量能状态输出龙头共振维度评分。
"""

from __future__ import annotations

from src.schemas.board_diagnosis import BoardDiagnosisDimension, BoardDiagnosisSource, BoardSignalDataStatus
from src.services.board_diagnosis.shared import AssetInsight


class LeaderSignalAnalyzer:
    """龙头共振维度评分器。"""

    KEY = "leaders"
    LABEL = "龙头共振"
    MAX_SCORE = 30

    def analyze(self, insights: list[AssetInsight]) -> BoardDiagnosisDimension:
        available = [item for item in insights if item.has_minimum_history]
        if len(available) < 2:
            warnings = [warning for item in insights for warning in item.warnings]
            return BoardDiagnosisDimension(
                key=self.KEY,
                label=self.LABEL,
                score=0,
                max_score=self.MAX_SCORE,
                data_status=BoardSignalDataStatus.MISSING,
                summary="核心股有效样本不足 2 只，无法判断共振。",
                warnings=warnings,
                metrics={"available_leaders": len(available)},
                sources=[
                    BoardDiagnosisSource(
                        label="3 只核心股日线与实时行情",
                        provider="stock_service",
                        detail="使用核心股近 90 日日线和最新行情快照估算龙头共振。",
                    )
                ],
            )

        evidence: list[str] = []
        risks: list[str] = []
        leader_metrics: list[dict[str, object]] = []
        total_score = 0
        strong_count = 0

        for insight in insights:
            leader_score = 0
            if insight.has_minimum_history and insight.ma_bullish:
                leader_score += 4
            if insight.has_minimum_history and insight.above_ma20:
                leader_score += 2
            if insight.return_10d is not None and insight.return_10d > 0:
                leader_score += 2
            if insight.amount_ratio_5d is not None and insight.amount_ratio_5d >= 1.0:
                leader_score += 2

            total_score += leader_score
            if leader_score >= 6:
                strong_count += 1
                evidence.append(f"{insight.stock_name} 维持强势结构（{leader_score}/10）")
            else:
                risks.append(f"{insight.stock_name} 共振强度偏弱（{leader_score}/10）")

            leader_metrics.append(
                {
                    "code": insight.asset.code,
                    "name": insight.stock_name,
                    "score": leader_score,
                    "change_pct": insight.change_pct,
                    "return_10d": insight.return_10d,
                    "amount_ratio_5d": insight.amount_ratio_5d,
                }
            )

        breadth_bonus = 6 if strong_count == 3 else 3 if strong_count == 2 else 0
        score = min(total_score + breadth_bonus, self.MAX_SCORE)
        status = BoardSignalDataStatus.AVAILABLE if len(available) == 3 else BoardSignalDataStatus.PARTIAL
        summary = "3 只核心股共振较强，龙头驱动清晰。" if strong_count == 3 else "核心股存在分化，需要防范仅靠单龙头硬拉。"

        return BoardDiagnosisDimension(
            key=self.KEY,
            label=self.LABEL,
            score=score,
            max_score=self.MAX_SCORE,
            data_status=status,
            summary=summary,
            evidence=evidence,
            risks=risks,
            warnings=[warning for item in insights for warning in item.warnings],
            metrics={
                "leaders": leader_metrics,
                "strong_count": strong_count,
                "available_leaders": len(available),
            },
            sources=[
                BoardDiagnosisSource(
                    label="3 只核心股日线与实时行情",
                    provider="stock_service",
                    detail="使用核心股近 90 日日线和最新行情快照计算趋势、涨跌幅与量能共振。",
                )
            ],
        )
