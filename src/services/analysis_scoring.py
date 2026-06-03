# -*- coding: utf-8 -*-
"""
本文件唯一职责：基于现有分析产物生成低敏、多维度的评分摘要。
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Dict, Optional

from src.schemas.analysis_context_pack import (
    AnalysisScore,
    AnalysisScoreDimension,
    AnalysisScoreLevel,
    ContextFieldStatus,
)

_DIMENSION_WEIGHTS: Dict[str, int] = {
    "technical": 40,
    "fundamentals": 25,
    "chip": 35,
}

_UNAVAILABLE_STATUSES = {
    ContextFieldStatus.MISSING,
    ContextFieldStatus.NOT_SUPPORTED,
    ContextFieldStatus.FETCH_FAILED,
}


def build_analysis_score(
    *,
    base_context: Dict[str, Any],
    realtime_quote: Optional[Dict[str, Any]],
    trend_result: Optional[Dict[str, Any]],
    chip_data: Optional[Dict[str, Any]],
    fundamental_context: Optional[Dict[str, Any]],
    block_statuses: Dict[str, ContextFieldStatus],
) -> AnalysisScore:
    """
    用途：为技术面、基本面、筹码面生成统一评分摘要。

    参数：
    - base_context: 日线上下文；推荐至少包含 today.close。
    - realtime_quote: 实时行情字典；推荐包含 price。
    - trend_result: 技术分析结果；推荐包含 trend_status、ma5/ma10/ma20、rsi_6。
    - chip_data: 筹码分布结果；推荐包含 profit_ratio、avg_cost、cost_90_low/high、concentration_90。
    - fundamental_context: 基本面上下文；推荐包含 status、coverage、source_chain。
    - block_statuses: 各维度数据质量状态。

    返回：
    - AnalysisScore: 低敏评分摘要。
    """
    current_price = _current_price(realtime_quote, base_context)
    dimensions = {
        "technical": _score_technical(
            trend_result=trend_result,
            current_price=current_price,
            status=block_statuses.get("technical", ContextFieldStatus.MISSING),
        ),
        "fundamentals": _score_fundamentals(
            context=fundamental_context,
            status=block_statuses.get("fundamentals", ContextFieldStatus.MISSING),
        ),
        "chip": _score_chip(
            chip=chip_data,
            current_price=current_price,
            status=block_statuses.get("chip", ContextFieldStatus.MISSING),
        ),
    }

    weighted_sum = 0
    weighted_confidence = 0
    total_weight = 0
    contributing: list[str] = []
    for key, dimension in dimensions.items():
        if dimension.score is None:
            continue
        weight = _DIMENSION_WEIGHTS[key]
        total_weight += weight
        weighted_sum += dimension.score * weight
        weighted_confidence += (dimension.confidence or 0) * weight
        contributing.append(key)

    if total_weight == 0:
        return AnalysisScore(
            level="unavailable",
            summary="关键分析维度数据不足，暂不生成评分。",
            dimensions=dimensions,
        )

    overall_score = int(round(weighted_sum / total_weight))
    confidence = int(round(weighted_confidence / total_weight))
    level = _score_level(overall_score)
    return AnalysisScore(
        overall_score=overall_score,
        confidence=confidence,
        level=level,
        action=_score_action(overall_score),
        summary=_overall_summary(dimensions, contributing, overall_score),
        dimensions=dimensions,
    )


def _score_technical(
    *,
    trend_result: Optional[Dict[str, Any]],
    current_price: Optional[float],
    status: ContextFieldStatus,
) -> AnalysisScoreDimension:
    if status in _UNAVAILABLE_STATUSES or not trend_result:
        return AnalysisScoreDimension(
            status=status,
            level="unavailable",
            summary="技术面数据不足，暂不评分。",
        )

    score = 50
    confidence = 55
    signals: list[str] = []
    trend_status = _text(trend_result.get("trend_status"))
    if any(token in trend_status for token in ("多头", "上升", "突破", "强势")):
        score += 15
        confidence += 10
        signals.append("趋势状态偏强")
    elif any(token in trend_status for token in ("空头", "下跌", "破位", "弱势")):
        score -= 15
        confidence += 10
        signals.append("趋势状态偏弱")

    ma5 = _float(trend_result.get("ma5"))
    ma10 = _float(trend_result.get("ma10"))
    ma20 = _float(trend_result.get("ma20"))
    if ma5 is not None and ma10 is not None:
        score += 8 if ma5 >= ma10 else -8
        confidence += 6
        signals.append("短期均线向上" if ma5 >= ma10 else "短期均线走弱")
    if ma10 is not None and ma20 is not None:
        score += 8 if ma10 >= ma20 else -8
        confidence += 6
        signals.append("中期均线支撑较好" if ma10 >= ma20 else "中期均线承压")
    if current_price is not None and ma20 is not None:
        score += 8 if current_price >= ma20 else -8
        confidence += 6
        signals.append("股价站上 MA20" if current_price >= ma20 else "股价位于 MA20 下方")

    rsi = _first_number(trend_result, "rsi_6", "rsi6", "rsi_14", "rsi14", "rsi")
    if rsi is not None:
        confidence += 6
        if 55 <= rsi <= 70:
            score += 6
            signals.append(f"RSI {rsi:.0f}，动能温和偏强")
        elif rsi > 80:
            score -= 8
            signals.append(f"RSI {rsi:.0f}，短线偏热")
        elif rsi < 30:
            score += 2
            signals.append(f"RSI {rsi:.0f}，接近超卖区")
        elif 30 <= rsi < 45:
            score -= 2
            signals.append(f"RSI {rsi:.0f}，动能偏弱")

    score, confidence = _apply_status_penalty(score, confidence, status)
    level = _score_level(score)
    return AnalysisScoreDimension(
        status=status,
        score=score,
        confidence=confidence,
        level=level,
        summary=_technical_summary(level, status),
        signals=signals[:3],
    )


def _score_fundamentals(
    *,
    context: Optional[Dict[str, Any]],
    status: ContextFieldStatus,
) -> AnalysisScoreDimension:
    if status in _UNAVAILABLE_STATUSES or not isinstance(context, Mapping):
        return AnalysisScoreDimension(
            status=status,
            level="unavailable",
            summary="基本面覆盖不足，暂不评分。",
        )

    raw_status = _text(context.get("status")).lower()
    coverage = context.get("coverage") if isinstance(context.get("coverage"), Mapping) else {}
    source_chain = context.get("source_chain") if isinstance(context.get("source_chain"), list) else []

    score = 60 if raw_status == "ok" else 48
    confidence = 35
    signals: list[str] = []

    ok_count = 0
    partial_count = 0
    failed_count = 0
    for key, value in coverage.items():
        normalized = _text(value).lower()
        if normalized == "ok":
            ok_count += 1
        elif normalized == "partial":
            partial_count += 1
        elif normalized == "failed":
            failed_count += 1
        signals.append(f"{key}：{normalized or 'unknown'}")

    score += min(ok_count * 8, 24)
    score += min(partial_count * 3, 9)
    score -= min(failed_count * 8, 16)
    confidence += min(ok_count * 15 + partial_count * 8, 45)

    first_chain = source_chain[0] if source_chain else None
    if isinstance(first_chain, Mapping):
        provider = _text(first_chain.get("provider"))
        result = _text(first_chain.get("result")).lower()
        if provider:
            signals.append(f"来源链首项：{provider}")
        if result == "ok":
            score += 4
            confidence += 8
        elif result in {"partial", "failed"}:
            score -= 4

    score, confidence = _apply_status_penalty(score, confidence, status)
    level = _score_level(score)
    return AnalysisScoreDimension(
        status=status,
        score=score,
        confidence=confidence,
        level=level,
        summary=_fundamental_summary(level, ok_count, partial_count, failed_count),
        signals=signals[:3],
    )


def _score_chip(
    *,
    chip: Optional[Dict[str, Any]],
    current_price: Optional[float],
    status: ContextFieldStatus,
) -> AnalysisScoreDimension:
    if status in _UNAVAILABLE_STATUSES or not chip:
        return AnalysisScoreDimension(
            status=status,
            level="unavailable",
            summary="筹码数据不足，暂不评分。",
        )

    score = 50
    confidence = 55
    signals: list[str] = []

    profit_ratio = _float(chip.get("profit_ratio"))
    if profit_ratio is not None:
        confidence += 10
        if profit_ratio >= 0.85:
            score += 18
            signals.append("获利盘占比很高")
        elif profit_ratio >= 0.70:
            score += 12
            signals.append("获利盘占比偏高")
        elif profit_ratio >= 0.55:
            score += 6
            signals.append("获利盘占比中性偏强")
        elif profit_ratio <= 0.20:
            score -= 18
            signals.append("高比例套牢盘压制")
        elif profit_ratio <= 0.35:
            score -= 10
            signals.append("套牢盘压力偏重")

    concentration_90 = _float(chip.get("concentration_90"))
    if concentration_90 is not None:
        confidence += 10
        if concentration_90 <= 0.08:
            score += 15
            signals.append("筹码高度集中")
        elif concentration_90 <= 0.15:
            score += 10
            signals.append("筹码较集中")
        elif concentration_90 > 0.25:
            score -= 8
            signals.append("筹码分散，承接一般")

    avg_cost = _float(chip.get("avg_cost"))
    if current_price is not None and avg_cost is not None and avg_cost > 0:
        confidence += 10
        premium = (current_price - avg_cost) / avg_cost
        if premium >= 0.05:
            score += 12
            signals.append("现价位于平均成本上方")
        elif premium >= 0:
            score += 8
            signals.append("现价略高于平均成本")
        elif premium <= -0.03:
            score -= 12
            signals.append("现价跌破平均成本")
        else:
            score -= 5
            signals.append("现价接近平均成本")

    low_90 = _float(chip.get("cost_90_low"))
    high_90 = _float(chip.get("cost_90_high"))
    if current_price is not None and low_90 is not None and high_90 is not None:
        confidence += 6
        if low_90 <= current_price <= high_90:
            score += 4
            signals.append("股价运行在主筹码区间内")
        elif current_price > high_90:
            score += 6
            signals.append("股价运行在主筹码区上方")
        else:
            score -= 6
            signals.append("股价运行在主筹码区下方")

    score, confidence = _apply_status_penalty(score, confidence, status)
    level = _score_level(score)
    return AnalysisScoreDimension(
        status=status,
        score=score,
        confidence=confidence,
        level=level,
        summary=_chip_summary(level),
        signals=signals[:3],
    )


def _current_price(
    realtime_quote: Optional[Dict[str, Any]],
    base_context: Dict[str, Any],
) -> Optional[float]:
    if isinstance(realtime_quote, Mapping):
        price = _float(realtime_quote.get("price"))
        if price is not None:
            return price
    today = base_context.get("today") if isinstance(base_context.get("today"), Mapping) else {}
    return _float(today.get("close"))


def _apply_status_penalty(score: int, confidence: int, status: ContextFieldStatus) -> tuple[int, int]:
    if status == ContextFieldStatus.PARTIAL:
        score -= 5
        confidence -= 12
    elif status == ContextFieldStatus.FALLBACK:
        score -= 3
        confidence -= 10
    elif status in {ContextFieldStatus.STALE, ContextFieldStatus.ESTIMATED}:
        score -= 6
        confidence -= 15
    return _clamp_score(score), _clamp_score(confidence)


def _score_level(score: int) -> AnalysisScoreLevel:
    if score >= 78:
        return "strong"
    if score >= 64:
        return "positive"
    if score >= 48:
        return "neutral"
    if score >= 34:
        return "cautious"
    return "weak"


def _score_action(score: int) -> str:
    if score >= 78:
        return "priority_focus"
    if score >= 64:
        return "lean_positive"
    if score >= 48:
        return "neutral_wait"
    if score >= 34:
        return "cautious"
    return "avoid"


def _overall_summary(
    dimensions: Dict[str, AnalysisScoreDimension],
    contributing: list[str],
    overall_score: int,
) -> str:
    strongest = max(
        (key for key in contributing),
        key=lambda key: dimensions[key].score or 0,
    )
    weakest = min(
        (key for key in contributing),
        key=lambda key: dimensions[key].score or 0,
    )
    dimension_labels = {
        "technical": "技术面",
        "fundamentals": "基本面",
        "chip": "筹码面",
    }
    if strongest == weakest:
        return f"{dimension_labels[strongest]}主导当前判断，总体评分 {overall_score}。"
    return (
        f"{dimension_labels[strongest]}相对占优，"
        f"{dimension_labels[weakest]}仍需继续确认，总体评分 {overall_score}。"
    )


def _technical_summary(level: AnalysisScoreLevel, status: ContextFieldStatus) -> str:
    if status == ContextFieldStatus.PARTIAL:
        return "技术面偏强弱判断可用，但盘中覆盖导致置信度下调。"
    mapping = {
        "strong": "技术结构偏强，趋势与动量共振较好。",
        "positive": "技术面偏多，趋势结构整体占优。",
        "neutral": "技术面中性，趋势尚未形成明确优势。",
        "cautious": "技术面偏弱，短中期结构需要谨慎。",
        "weak": "技术面明显承压，短线防守优先。",
        "unavailable": "技术面数据不足，暂不评分。",
    }
    return mapping[level]


def _fundamental_summary(
    level: AnalysisScoreLevel,
    ok_count: int,
    partial_count: int,
    failed_count: int,
) -> str:
    if ok_count == 0 and partial_count == 0 and failed_count == 0:
        return "基本面仅有状态级信息，适合做粗粒度判断。"
    return (
        f"基本面已覆盖 {ok_count} 个完整维度、{partial_count} 个部分维度，"
        f"{'存在失败项。' if failed_count else '当前可做中低敏判断。'}"
    )


def _chip_summary(level: AnalysisScoreLevel) -> str:
    mapping = {
        "strong": "筹码结构偏强，主筹码区对趋势形成支撑。",
        "positive": "筹码面偏多，获利盘与集中度组合较健康。",
        "neutral": "筹码面中性，尚未形成明显优势。",
        "cautious": "筹码面偏弱，上方压力仍需消化。",
        "weak": "筹码面较弱，套牢与分散特征明显。",
        "unavailable": "筹码数据不足，暂不评分。",
    }
    return mapping[level]


def _first_number(mapping: Mapping[str, Any], *keys: str) -> Optional[float]:
    for key in keys:
        value = _float(mapping.get(key))
        if value is not None:
            return value
    return None


def _text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _float(value: Any) -> Optional[float]:
    try:
        if value in (None, ""):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp_score(value: int) -> int:
    return max(0, min(100, int(round(value))))
