# -*- coding: utf-8 -*-
"""
===================================
板块决策解释生成器
===================================

本文件唯一职责：将各维度评分结果整理为用户可读的摘要、理由和风险列表。
"""

from __future__ import annotations

from src.schemas.board_diagnosis import BoardDecisionAction, BoardDiagnosisDimension

_ACTION_SUMMARY_PREFIX = {
    BoardDecisionAction.BUY: "当前板块综合信号偏强，ETF 可考虑分批买入。",
    BoardDecisionAction.HOLD: "当前板块仍具备延续性，ETF 更适合继续持有。",
    BoardDecisionAction.REDUCE: "当前板块强度开始衰减，ETF 更适合主动减仓。",
    BoardDecisionAction.EXIT: "当前板块有效支撑不足，ETF 更适合退出或回避。",
}


class ExplanationRenderer:
    """板块决策解释生成器。"""

    def render(
        self,
        *,
        action: BoardDecisionAction,
        dimensions: list[BoardDiagnosisDimension],
    ) -> tuple[str, list[str], list[str], list[str]]:
        reasons: list[str] = []
        risks: list[str] = []
        warnings: list[str] = []

        for dimension in dimensions:
            reasons.extend(dimension.evidence[:2])
            risks.extend(dimension.risks[:2])
            warnings.extend(dimension.warnings[:2])

        summary_prefix = _ACTION_SUMMARY_PREFIX[action]
        if reasons:
            summary = f"{summary_prefix} 主要依据包括：{reasons[0]}"
        elif risks:
            summary = f"{summary_prefix} 当前主要问题是：{risks[0]}"
        else:
            summary = summary_prefix

        dedup_reasons = list(dict.fromkeys(reasons))[:6]
        dedup_risks = list(dict.fromkeys(risks))[:6]
        dedup_warnings = list(dict.fromkeys(warnings))[:6]
        return summary, dedup_reasons, dedup_risks, dedup_warnings
