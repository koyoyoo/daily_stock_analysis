# -*- coding: utf-8 -*-
"""
===================================
板块配置注册表
===================================

本文件唯一职责：维护 ETF 板块诊断的显式板块映射配置，并提供查询入口。
"""

from __future__ import annotations

from src.schemas.board_diagnosis import BoardAssetRef, BoardAssetRole, BoardDefinition, BoardDefinitionSummary


DEFAULT_BOARD_DEFINITIONS: tuple[BoardDefinition, ...] = (
    BoardDefinition(
        board_key="new_energy",
        board_name="新能源",
        primary_etf=BoardAssetRef(code="159755", name="新能源车ETF", role=BoardAssetRole.ETF),
        benchmark_index=BoardAssetRef(code="399808", name="新能源车指数", role=BoardAssetRole.INDEX),
        sector_names=["新能源车", "电池", "新能源"],
        leaders=[
            BoardAssetRef(code="300750", name="宁德时代", role=BoardAssetRole.LEADER),
            BoardAssetRef(code="002594", name="比亚迪", role=BoardAssetRole.CORE),
            BoardAssetRef(code="300274", name="阳光电源", role=BoardAssetRole.CORE),
        ],
    ),
    BoardDefinition(
        board_key="liquor",
        board_name="白酒",
        primary_etf=BoardAssetRef(code="512690", name="酒ETF", role=BoardAssetRole.ETF),
        benchmark_index=BoardAssetRef(code="399997", name="中证白酒指数", role=BoardAssetRole.INDEX),
        sector_names=["酿酒行业", "白酒"],
        leaders=[
            BoardAssetRef(code="600519", name="贵州茅台", role=BoardAssetRole.LEADER),
            BoardAssetRef(code="000858", name="五粮液", role=BoardAssetRole.CORE),
            BoardAssetRef(code="600809", name="山西汾酒", role=BoardAssetRole.CORE),
        ],
    ),
    BoardDefinition(
        board_key="robotics",
        board_name="机器人",
        primary_etf=BoardAssetRef(code="562500", name="机器人ETF", role=BoardAssetRole.ETF),
        benchmark_index=BoardAssetRef(code="930853", name="中证机器人指数", role=BoardAssetRole.INDEX),
        sector_names=["机器人", "专用设备", "通用设备"],
        leaders=[
            BoardAssetRef(code="688017", name="绿的谐波", role=BoardAssetRole.LEADER),
            BoardAssetRef(code="300124", name="汇川技术", role=BoardAssetRole.CORE),
            BoardAssetRef(code="002747", name="埃斯顿", role=BoardAssetRole.CORE),
        ],
    ),
    BoardDefinition(
        board_key="semiconductor",
        board_name="半导体",
        primary_etf=BoardAssetRef(code="512480", name="半导体ETF", role=BoardAssetRole.ETF),
        benchmark_index=BoardAssetRef(code="931865", name="中证芯片产业指数", role=BoardAssetRole.INDEX),
        sector_names=["半导体", "芯片概念", "电子元件"],
        leaders=[
            BoardAssetRef(code="688981", name="中芯国际", role=BoardAssetRole.LEADER),
            BoardAssetRef(code="688012", name="中微公司", role=BoardAssetRole.CORE),
            BoardAssetRef(code="603501", name="豪威集团", role=BoardAssetRole.CORE),
        ],
    ),
    BoardDefinition(
        board_key="broker",
        board_name="证券",
        primary_etf=BoardAssetRef(code="512880", name="证券ETF", role=BoardAssetRole.ETF),
        benchmark_index=BoardAssetRef(code="399975", name="证券公司指数", role=BoardAssetRole.INDEX),
        sector_names=["证券", "证券Ⅱ"],
        leaders=[
            BoardAssetRef(code="300059", name="东方财富", role=BoardAssetRole.LEADER),
            BoardAssetRef(code="600030", name="中信证券", role=BoardAssetRole.CORE),
            BoardAssetRef(code="601211", name="国泰海通", role=BoardAssetRole.CORE),
        ],
    ),
)


class BoardRegistry:
    """
    板块配置注册表。

    用途：
        提供手工维护的板块映射查询入口。

    异常：
        `get()` 在板块不存在时抛出 `ValueError`。
    """

    def __init__(self, definitions: tuple[BoardDefinition, ...] = DEFAULT_BOARD_DEFINITIONS):
        self._definitions = {definition.board_key: definition for definition in definitions}

    def list_summaries(self) -> list[BoardDefinitionSummary]:
        """返回所有板块摘要，按板块键排序。"""
        return [
            BoardDefinitionSummary.model_validate(definition.model_dump())
            for definition in sorted(self._definitions.values(), key=lambda item: item.board_key)
        ]

    def get(self, board_key: str) -> BoardDefinition:
        """
        获取板块定义。

        参数：
            board_key: 板块唯一键，推荐值：注册表中存在的 key。

        返回：
            BoardDefinition：板块定义对象。

        异常：
            ValueError：当板块不存在时抛出。
        """
        normalized_key = (board_key or "").strip().lower()
        if normalized_key not in self._definitions:
            raise ValueError(f"未找到板块配置: {board_key}")
        return self._definitions[normalized_key]
