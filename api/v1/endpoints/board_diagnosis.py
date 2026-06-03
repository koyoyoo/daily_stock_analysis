# -*- coding: utf-8 -*-
"""
===================================
ETF板块诊断接口
===================================

本文件唯一职责：提供 ETF 板块决策板的只读查询接口。
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.v1.schemas.board_diagnosis import BoardDefinitionSummary, BoardDiagnosisResult
from api.v1.schemas.common import ErrorResponse
from src.services.board_diagnosis import BoardDiagnosisService

router = APIRouter()


@router.get(
    "/boards",
    response_model=list[BoardDefinitionSummary],
    responses={500: {"description": "板块列表读取失败", "model": ErrorResponse}},
    summary="获取可用 ETF 板块列表",
    description="返回当前手工维护的 ETF 板块注册表，用于前端选择和后续诊断。",
)
def list_boards() -> list[BoardDefinitionSummary]:
    service = BoardDiagnosisService()
    return service.list_boards()


@router.get(
    "/{board_key}",
    response_model=BoardDiagnosisResult,
    responses={
        404: {"description": "板块不存在", "model": ErrorResponse},
        500: {"description": "板块诊断失败", "model": ErrorResponse},
    },
    summary="执行 ETF 板块诊断",
    description="基于板块配置、指数、3 只核心股和已有数据源输出结构化 ETF 板块决策结果。",
)
def diagnose_board(board_key: str) -> BoardDiagnosisResult:
    service = BoardDiagnosisService()
    try:
        return service.diagnose(board_key)
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={"error": "board_not_found", "message": str(exc)},
        ) from exc
