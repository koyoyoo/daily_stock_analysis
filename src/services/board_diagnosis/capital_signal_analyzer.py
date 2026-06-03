# -*- coding: utf-8 -*-
"""
===================================
资金状态评分器
===================================

本文件唯一职责：根据 ETF 成交额和龙头量能状态输出资金维度评分，并显式标记缺失项。
"""

from __future__ import annotations

from src.schemas.board_diagnosis import BoardDiagnosisDimension, BoardDiagnosisSource, BoardSignalDataStatus
from src.services.board_diagnosis.capital_data_loader import CapitalSupportSnapshot
from src.services.board_diagnosis.shared import AssetInsight


class CapitalSignalAnalyzer:
    """资金维度评分器。"""

    KEY = "capital"
    LABEL = "资金状态"
    MAX_SCORE = 15

    def analyze(
        self,
        etf_insight: AssetInsight,
        leader_insights: list[AssetInsight],
        capital_support: CapitalSupportSnapshot,
    ) -> BoardDiagnosisDimension:
        score = 0
        evidence: list[str] = []
        risks: list[str] = []
        warnings = list(capital_support.warnings) + list(etf_insight.warnings)
        sources: list[BoardDiagnosisSource] = [
            BoardDiagnosisSource(
                label="ETF 与核心股量能",
                provider="stock_service",
                detail="使用 ETF 与 3 只核心股的最新行情和日线成交额，估算量能共振。",
            )
        ]

        etf_share = capital_support.etf_share
        if etf_share is not None:
            sources.append(
                BoardDiagnosisSource(
                    label="ETF 份额变化",
                    provider=etf_share.source,
                    detail=f"单位：{etf_share.unit}",
                    trade_date=etf_share.trade_date,
                    range_start=etf_share.previous_trade_date,
                    range_end=etf_share.trade_date,
                )
            )
        if etf_share is not None and etf_share.change > 0:
            score += 6 if etf_share.change_pct >= 1.0 else 4
            evidence.append(
                f"ETF 份额较前值增加 {etf_share.change_pct:.2f}%（{etf_share.previous_trade_date} -> {etf_share.trade_date}）"
            )
        elif etf_share is not None:
            risks.append(
                f"ETF 份额较前值下降 {abs(etf_share.change_pct):.2f}%（{etf_share.previous_trade_date} -> {etf_share.trade_date}）"
            )
        else:
            if etf_insight.amount_ratio_5d is not None and etf_insight.amount_ratio_5d >= 1.05:
                score += 3
                evidence.append(f"ETF 最新成交额放大至 5 日均值的 {etf_insight.amount_ratio_5d:.2f} 倍")
            elif etf_insight.amount_ratio_5d is not None:
                risks.append("ETF 成交额未明显放大，新增资金力度一般")
            else:
                risks.append("缺少 ETF 份额变化与成交额放大倍数")

        leader_amount_positive = sum(
            1 for insight in leader_insights
            if insight.amount_ratio_5d is not None and insight.amount_ratio_5d >= 1.0
        )
        if leader_amount_positive >= 2:
            score += 5
            evidence.append(f"{leader_amount_positive}/3 核心股成交额高于 5 日均值")
        elif leader_amount_positive == 1:
            score += 2
            risks.append("仅 1 只核心股放量，资金扩散仍偏弱")
        else:
            risks.append("核心股未形成明显量能共振")

        sector_turnover = capital_support.sector_turnover
        if sector_turnover is not None:
            sources.append(
                BoardDiagnosisSource(
                    label="板块成交额快照",
                    provider=sector_turnover.source,
                    detail=f"匹配板块：{sector_turnover.sector_name}",
                )
            )
        if sector_turnover is not None and sector_turnover.amount > 0:
            score += 2
            evidence.append(f"板块 {sector_turnover.sector_name} 成交额 {sector_turnover.amount:.2f} 亿元")
            if sector_turnover.turnover_share_pct is not None:
                score += 1
                evidence.append(f"占两市成交额 {sector_turnover.turnover_share_pct:.2f}%")
            if sector_turnover.change_pct is not None and sector_turnover.change_pct > 0:
                score += 1
                evidence.append(f"板块当日涨跌幅 {sector_turnover.change_pct:.2f}%")
        else:
            risks.append("缺少真实板块成交额快照")

        status = BoardSignalDataStatus.AVAILABLE if etf_share is not None and sector_turnover is not None else BoardSignalDataStatus.PARTIAL

        return BoardDiagnosisDimension(
            key=self.KEY,
            label=self.LABEL,
            score=min(score, self.MAX_SCORE),
            max_score=self.MAX_SCORE,
            data_status=status,
            summary="资金评分优先使用 ETF 份额变化、龙头量能和板块成交额；缺失项会显式降级。",
            evidence=evidence,
            risks=risks,
            warnings=warnings,
            metrics={
                "etf_share_change_pct": etf_share.change_pct if etf_share is not None else None,
                "etf_amount_ratio_5d": etf_insight.amount_ratio_5d,
                "leader_amount_positive": leader_amount_positive,
                "sector_turnover_amount": sector_turnover.amount if sector_turnover is not None else None,
                "sector_turnover_share_pct": (
                    sector_turnover.turnover_share_pct if sector_turnover is not None else None
                ),
            },
            sources=sources,
        )
