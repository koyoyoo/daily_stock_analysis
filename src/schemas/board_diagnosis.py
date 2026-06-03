# -*- coding: utf-8 -*-
"""
===================================
ETF板块决策板内部契约
===================================

本文件唯一职责：定义 ETF 板块诊断的内部 Pydantic 契约，统一板块配置、维度评分和决策结果结构。
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class BoardAssetRole(str, Enum):
    """板块资产角色。"""

    ETF = "etf"
    INDEX = "index"
    LEADER = "leader"
    CORE = "core"


class BoardDecisionAction(str, Enum):
    """板块决策动作。"""

    BUY = "buy"
    HOLD = "hold"
    REDUCE = "reduce"
    EXIT = "exit"


class BoardDecisionConfidence(str, Enum):
    """板块决策置信度。"""

    HIGH = "high"
    MEDIUM_HIGH = "medium_high"
    MEDIUM = "medium"
    LOW = "low"


class BoardSignalDataStatus(str, Enum):
    """维度数据状态。"""

    AVAILABLE = "available"
    PARTIAL = "partial"
    ESTIMATED = "estimated"
    MISSING = "missing"


class BoardAssetRef(BaseModel):
    """板块配置中的资产引用。"""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(..., description="资产代码")
    name: str = Field(..., description="资产名称")
    role: BoardAssetRole = Field(..., description="资产角色")
    market: str = Field("CN", description="市场标识")


class BoardDefinition(BaseModel):
    """板块配置定义。"""

    model_config = ConfigDict(extra="forbid")

    board_key: str = Field(..., description="板块唯一键")
    board_name: str = Field(..., description="板块名称")
    market: str = Field("CN", description="市场标识")
    primary_etf: BoardAssetRef = Field(..., description="主 ETF")
    benchmark_index: BoardAssetRef = Field(..., description="板块指数")
    sector_names: list[str] = Field(default_factory=list, description="用于匹配板块成交额的行业名称列表")
    leaders: list[BoardAssetRef] = Field(..., min_length=3, max_length=3, description="核心个股列表")

    @model_validator(mode="after")
    def validate_roles(self) -> "BoardDefinition":
        if self.primary_etf.role is not BoardAssetRole.ETF:
            raise ValueError("primary_etf.role 必须为 etf")
        if self.benchmark_index.role is not BoardAssetRole.INDEX:
            raise ValueError("benchmark_index.role 必须为 index")
        if len(self.leaders) != 3:
            raise ValueError("leaders 必须固定为 3 只核心股")

        leader_codes = {asset.code for asset in self.leaders}
        if len(leader_codes) != 3:
            raise ValueError("leaders 不允许重复代码")

        allowed_roles = {BoardAssetRole.LEADER, BoardAssetRole.CORE}
        invalid_roles = [asset.role.value for asset in self.leaders if asset.role not in allowed_roles]
        if invalid_roles:
            raise ValueError(f"leaders 角色非法: {', '.join(invalid_roles)}")
        if not self.sector_names:
            self.sector_names = [self.board_name]
        return self


class BoardDefinitionSummary(BaseModel):
    """板块配置摘要。"""

    model_config = ConfigDict(extra="forbid")

    board_key: str = Field(..., description="板块唯一键")
    board_name: str = Field(..., description="板块名称")
    market: str = Field(..., description="市场标识")
    primary_etf: BoardAssetRef = Field(..., description="主 ETF")
    benchmark_index: BoardAssetRef = Field(..., description="板块指数")
    sector_names: list[str] = Field(default_factory=list, description="用于匹配板块成交额的行业名称列表")
    leaders: list[BoardAssetRef] = Field(..., description="核心个股列表")


class BoardDiagnosisSource(BaseModel):
    """维度来源信息。"""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(..., description="来源标签")
    provider: Optional[str] = Field(default=None, description="数据提供方或能力来源")
    detail: Optional[str] = Field(default=None, description="来源说明")
    trade_date: Optional[str] = Field(default=None, description="单点交易日")
    range_start: Optional[str] = Field(default=None, description="区间起点")
    range_end: Optional[str] = Field(default=None, description="区间终点")


class BoardDiagnosisDimension(BaseModel):
    """单个评分维度的结果。"""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., description="维度键")
    label: str = Field(..., description="维度名称")
    score: int = Field(..., ge=0, description="当前得分")
    max_score: int = Field(..., ge=0, description="最大分值")
    data_status: BoardSignalDataStatus = Field(..., description="数据状态")
    summary: str = Field(..., description="维度摘要")
    evidence: list[str] = Field(default_factory=list, description="证据列表")
    risks: list[str] = Field(default_factory=list, description="风险列表")
    warnings: list[str] = Field(default_factory=list, description="告警列表")
    metrics: dict[str, Any] = Field(default_factory=dict, description="结构化指标")
    sources: list[BoardDiagnosisSource] = Field(default_factory=list, description="结构化来源信息")


class BoardDiagnosisResult(BaseModel):
    """板块决策板输出结果。"""

    model_config = ConfigDict(extra="forbid")

    board_key: str = Field(..., description="板块唯一键")
    board_name: str = Field(..., description="板块名称")
    market: str = Field(..., description="市场标识")
    primary_etf: BoardAssetRef = Field(..., description="主 ETF")
    benchmark_index: BoardAssetRef = Field(..., description="板块指数")
    leaders: list[BoardAssetRef] = Field(..., description="核心个股列表")
    score: int = Field(..., ge=0, le=100, description="总分")
    action: BoardDecisionAction = Field(..., description="英文动作枚举")
    action_label: str = Field(..., description="中文动作标签")
    confidence: BoardDecisionConfidence = Field(..., description="英文置信度枚举")
    confidence_label: str = Field(..., description="中文置信度标签")
    summary: str = Field(..., description="整体摘要")
    reasons: list[str] = Field(default_factory=list, description="主要理由")
    risks: list[str] = Field(default_factory=list, description="主要风险")
    warnings: list[str] = Field(default_factory=list, description="全局告警")
    dimension_scores: dict[str, int] = Field(default_factory=dict, description="维度分数字典")
    dimensions: list[BoardDiagnosisDimension] = Field(default_factory=list, description="维度详情")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC), description="生成时间")
