# -*- coding: utf-8 -*-
"""
===================================
板块决策汇总器
===================================

本文件唯一职责：根据各维度评分结果生成 ETF 板块诊断的总分、动作和置信度。
"""

from __future__ import annotations

from src.schemas.board_diagnosis import (
    BoardDecisionAction,
    BoardDecisionConfidence,
    BoardDiagnosisDimension,
)

_ACTION_LABELS = {
    BoardDecisionAction.BUY: "买入",
    BoardDecisionAction.HOLD: "持有",
    BoardDecisionAction.REDUCE: "减仓",
    BoardDecisionAction.EXIT: "清仓",
}

_CONFIDENCE_LABELS = {
    BoardDecisionConfidence.HIGH: "高",
    BoardDecisionConfidence.MEDIUM_HIGH: "中高",
    BoardDecisionConfidence.MEDIUM: "中",
    BoardDecisionConfidence.LOW: "低",
}


class DecisionScorer:
    """板块决策汇总器。"""

    BUY_THRESHOLD = 80
    HOLD_THRESHOLD = 65
    REDUCE_THRESHOLD = 50

    def score(self, dimensions: list[BoardDiagnosisDimension]) -> tuple[int, BoardDecisionAction, str, BoardDecisionConfidence, str]:
        """
        汇总维度结果。

        参数：
            dimensions: 各维度评分结果。

        返回：
            `(score, action, action_label, confidence, confidence_label)`。
        """
        total_score = sum(item.score for item in dimensions)
        score = max(0, min(100, total_score))

        if score >= self.BUY_THRESHOLD:
            action = BoardDecisionAction.BUY
        elif score >= self.HOLD_THRESHOLD:
            action = BoardDecisionAction.HOLD
        elif score >= self.REDUCE_THRESHOLD:
            action = BoardDecisionAction.REDUCE
        else:
            action = BoardDecisionAction.EXIT

        data_states = [item.data_status.value for item in dimensions]
        available_count = data_states.count("available")
        partial_count = data_states.count("partial")
        estimated_count = data_states.count("estimated")
        missing_count = data_states.count("missing")

        if missing_count == 0 and available_count >= 4:
            confidence = BoardDecisionConfidence.HIGH
        elif missing_count <= 1 and available_count + partial_count >= 4:
            confidence = BoardDecisionConfidence.MEDIUM_HIGH
        elif missing_count <= 2 and available_count + partial_count + estimated_count >= 4:
            confidence = BoardDecisionConfidence.MEDIUM
        else:
            confidence = BoardDecisionConfidence.LOW

        return (
            score,
            action,
            _ACTION_LABELS[action],
            confidence,
            _CONFIDENCE_LABELS[confidence],
        )
