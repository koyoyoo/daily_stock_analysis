# -*- coding: utf-8 -*-
"""
===================================
板块指数评分器
===================================

本文件唯一职责：根据板块指数的日线趋势和成交额状态输出指数维度评分。
"""

from __future__ import annotations

from src.schemas.board_diagnosis import BoardDiagnosisDimension, BoardDiagnosisSource, BoardSignalDataStatus
from src.services.board_diagnosis.shared import AssetInsight


class IndexSignalAnalyzer:
    """指数维度评分器。"""

    KEY = "index"
    LABEL = "指数强弱"
    MAX_SCORE = 25

    def analyze(self, insight: AssetInsight) -> BoardDiagnosisDimension:
        if not insight.has_minimum_history:
            return BoardDiagnosisDimension(
                key=self.KEY,
                label=self.LABEL,
                score=0,
                max_score=self.MAX_SCORE,
                data_status=BoardSignalDataStatus.MISSING,
                summary="指数数据不足，无法完成稳定趋势判断。",
                warnings=list(insight.warnings),
                metrics={"history_size": insight.history_size},
                sources=[
                    BoardDiagnosisSource(
                        label="板块指数日线与实时行情",
                        provider="stock_service",
                        detail="使用板块指数近 90 日日线和最新行情快照估算趋势结构。",
                    )
                ],
            )

        score = 0
        evidence: list[str] = []
        risks: list[str] = []

        if insight.above_ma20:
            score += 6
            evidence.append("指数站上 MA20，趋势基础成立")
        else:
            risks.append("指数仍在 MA20 下方，趋势未完全修复")

        if insight.ma_bullish:
            score += 8
            evidence.append("指数形成 MA5 > MA10 > MA20 多头排列")
        else:
            risks.append("短中期均线尚未形成多头排列")

        if insight.above_ma60:
            score += 5
            evidence.append("指数站上 MA60，中期结构偏强")
        elif insight.has_long_history:
            risks.append("指数尚未站上 MA60，中期突破仍待确认")

        if insight.return_10d is not None and insight.return_10d > 0:
            score += 3
            evidence.append(f"近 10 日收益为正（{insight.return_10d:.2f}%）")
        elif insight.return_10d is not None:
            risks.append(f"近 10 日收益转弱（{insight.return_10d:.2f}%）")

        if insight.amount_ratio_5d is not None and insight.amount_ratio_5d >= 1.05:
            score += 3
            evidence.append(f"最新成交额较 5 日均值放大（{insight.amount_ratio_5d:.2f} 倍）")
        elif insight.amount_ratio_5d is None:
            risks.append("指数缺少可用成交额放大倍数")

        summary = "指数趋势偏强，可为 ETF 决策提供正向基础。" if score >= 18 else "指数趋势中性偏弱，暂不支持高置信追涨。"
        status = BoardSignalDataStatus.AVAILABLE if insight.has_long_history else BoardSignalDataStatus.PARTIAL

        return BoardDiagnosisDimension(
            key=self.KEY,
            label=self.LABEL,
            score=min(score, self.MAX_SCORE),
            max_score=self.MAX_SCORE,
            data_status=status,
            summary=summary,
            evidence=evidence,
            risks=risks,
            warnings=list(insight.warnings),
            metrics={
                "price": insight.current_price,
                "change_pct": insight.change_pct,
                "ma5": insight.ma5,
                "ma10": insight.ma10,
                "ma20": insight.ma20,
                "ma60": insight.ma60,
                "amount_ratio_5d": insight.amount_ratio_5d,
                "return_10d": insight.return_10d,
            },
            sources=[
                BoardDiagnosisSource(
                    label="板块指数日线与实时行情",
                    provider="stock_service",
                    detail="使用板块指数近 90 日日线和最新行情快照计算均线、涨跌幅与量能倍数。",
                )
            ],
        )
