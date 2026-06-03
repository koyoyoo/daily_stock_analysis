# -*- coding: utf-8 -*-
"""
===================================
板块诊断 API 模型
===================================

本文件唯一职责：复用内部板块诊断契约，为 API 层提供稳定的响应模型导出。
"""

from src.schemas.board_diagnosis import BoardDefinitionSummary, BoardDiagnosisResult

__all__ = [
    "BoardDefinitionSummary",
    "BoardDiagnosisResult",
]
