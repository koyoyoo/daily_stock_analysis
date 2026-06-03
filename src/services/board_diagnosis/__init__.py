# -*- coding: utf-8 -*-
"""
===================================
板块诊断服务导出
===================================

本文件唯一职责：控制板块诊断服务包的公开导出接口。
"""

from src.services.board_diagnosis.board_registry import BoardRegistry
from src.services.board_diagnosis.capital_data_loader import BoardCapitalDataLoader
from src.services.board_diagnosis.service import BoardDiagnosisService

__all__ = [
    "BoardRegistry",
    "BoardCapitalDataLoader",
    "BoardDiagnosisService",
]
