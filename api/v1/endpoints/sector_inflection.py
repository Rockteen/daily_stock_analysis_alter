# -*- coding: utf-8 -*-
"""Sector Inflection API endpoints."""

from __future__ import annotations

import logging
from datetime import date
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from api.deps import get_database_manager
from api.v1.schemas.sector_inflection import (
    SectorDashboardResponse,
    SectorDashboardItem,
    SectorHistoryResponse,
    SectorHistoryItem,
    SectorScanRequest,
    SectorScanResponse,
    SectorPoolItem,
    SectorPoolCreateRequest,
)
from src.services.sector_inflection_service import SectorInflectionService
from src.storage import DatabaseManager, SectorETFPool, SectorInflectionState

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/dashboard",
    response_model=SectorDashboardResponse,
    summary="获取板块最新分析看板数据",
)
def get_sector_dashboard(
    trade_date: Optional[date] = Query(None, description="指定查询日期，默认使用最新交易日记录"),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> SectorDashboardResponse:
    try:
        service = SectorInflectionService()
        data = service.get_dashboard(trade_date=trade_date)
        if not data:
            return SectorDashboardResponse(
                trade_date=trade_date or date.today(),
                market_regime="unknown",
                items=[],
            )

        # 提取基准日期与大盘开关状态
        first_item = data[0]
        resp_date = date.fromisoformat(first_item["trade_date"])
        resp_regime = first_item["market_regime"]

        items = []
        for r in data:
            items.append(
                SectorDashboardItem(
                    etf_code=r["etf_code"],
                    sector_name=r["sector_name"],
                    trade_date=date.fromisoformat(r["trade_date"]),
                    ignition_score=r["ignition_score"],
                    distribution_score=r["distribution_score"],
                    state=r["state"],
                    prev_state=r["prev_state"],
                    state_reason=r["state_reason"],
                    state_entered_date=date.fromisoformat(r["state_entered_date"])
                    if r["state_entered_date"]
                    else None,
                    market_regime=r["market_regime"],
                    ignition_details=r["ignition_details"],
                    distribution_details=r["distribution_details"],
                )
            )

        return SectorDashboardResponse(
            trade_date=resp_date,
            market_regime=resp_regime,
            items=items,
        )
    except Exception as exc:
        logger.error(f"获取板块看板数据失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"获取板块看板数据失败: {str(exc)}"},
        )


@router.get(
    "/{etf_code}/history",
    response_model=SectorHistoryResponse,
    summary="获取单板块历史状态序列",
)
def get_sector_history(
    etf_code: str,
    limit: int = Query(60, ge=1, le=200, description="历史记录条数限制"),
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> SectorHistoryResponse:
    try:
        records = db_manager.get_sector_inflection_history(etf_code, limit=limit)
        if not records:
            with db_manager.get_session() as session:
                etf = session.query(SectorETFPool).filter(SectorETFPool.etf_code == etf_code).first()
                name = etf.sector_name if etf else "Unknown"
            return SectorHistoryResponse(etf_code=etf_code, sector_name=name, history=[])

        name = records[0].sector_name
        history_items = []
        for r in records:
            history_items.append(
                SectorHistoryItem(
                    trade_date=r.trade_date,
                    ignition_score=r.ignition_score,
                    distribution_score=r.distribution_score,
                    state=r.state,
                    prev_state=r.prev_state,
                    state_reason=r.state_reason,
                    state_entered_date=r.state_entered_date,
                    market_regime=r.market_regime,
                )
            )

        return SectorHistoryResponse(
            etf_code=etf_code,
            sector_name=name,
            history=history_items,
        )
    except Exception as exc:
        logger.error(f"获取板块历史数据失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"获取板块历史数据失败: {str(exc)}"},
        )


@router.post(
    "/scan",
    response_model=SectorScanResponse,
    summary="手动触发板块拐点扫描",
)
def trigger_sector_scan(
    request: SectorScanRequest,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> SectorScanResponse:
    try:
        service = SectorInflectionService()
        result = service.run_daily_scan(
            trade_date=request.trade_date,
            force=request.force,
        )
        return SectorScanResponse(
            status=result["status"],
            trade_date=result.get("trade_date") or str(request.trade_date or date.today()),
            market_regime=result.get("market_regime") or "unknown",
            transitions_count=result.get("transitions_count") or 0,
            results=result.get("results") or [],
        )
    except Exception as exc:
        logger.error(f"手动触发板块拐点扫描失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"手动触发板块扫描失败: {str(exc)}"},
        )


@router.get(
    "/pool",
    response_model=List[SectorPoolItem],
    summary="获取 ETF 板块池列表",
)
def get_sector_pool(
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> List[SectorPoolItem]:
    try:
        with db_manager.get_session() as session:
            etfs = session.query(SectorETFPool).all()
            if not etfs:
                # 触发自动初始化 (bootstrap)
                db_manager.get_active_sector_etfs()
                etfs = session.query(SectorETFPool).all()

            return [
                SectorPoolItem(
                    id=etf.id,
                    etf_code=etf.etf_code,
                    sector_name=etf.sector_name,
                    category=etf.category,
                    benchmark_index=etf.benchmark_index,
                    is_active=etf.is_active,
                    created_at=etf.created_at,
                )
                for etf in etfs
            ]
    except Exception as exc:
        logger.error(f"获取板块 ETF 池失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"获取板块池失败: {str(exc)}"},
        )


@router.post(
    "/pool",
    response_model=SectorPoolItem,
    summary="添加或更新板块到 ETF 池",
)
def add_or_update_sector_pool(
    request: SectorPoolCreateRequest,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> SectorPoolItem:
    try:
        def _write(session):
            existing = session.query(SectorETFPool).filter(
                SectorETFPool.etf_code == request.etf_code
            ).first()
            if existing:
                existing.sector_name = request.sector_name
                existing.category = request.category
                existing.benchmark_index = request.benchmark_index
                existing.is_active = request.is_active
            else:
                new_item = SectorETFPool(
                    etf_code=request.etf_code,
                    sector_name=request.sector_name,
                    category=request.category,
                    benchmark_index=request.benchmark_index,
                    is_active=request.is_active,
                )
                session.add(new_item)

        db_manager._run_write_transaction("add_or_update_sector_pool", _write)

        with db_manager.get_session() as session:
            etf = session.query(SectorETFPool).filter(
                SectorETFPool.etf_code == request.etf_code
            ).first()
            return SectorPoolItem(
                id=etf.id,
                etf_code=etf.etf_code,
                sector_name=etf.sector_name,
                category=etf.category,
                benchmark_index=etf.benchmark_index,
                is_active=etf.is_active,
                created_at=etf.created_at,
            )
    except Exception as exc:
        logger.error(f"修改板块 ETF 池失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"操作板块池失败: {str(exc)}"},
        )


@router.delete(
    "/pool/{etf_code}",
    summary="从 ETF 池中删除板块",
)
def delete_sector_from_pool(
    etf_code: str,
    db_manager: DatabaseManager = Depends(get_database_manager),
) -> Dict[str, str]:
    try:
        def _delete(session):
            etf = session.query(SectorETFPool).filter(SectorETFPool.etf_code == etf_code).first()
            if etf:
                session.delete(etf)

        db_manager._run_write_transaction("delete_sector_from_pool", _delete)
        return {"status": "success", "message": f"Successfully deleted {etf_code} from pool"}
    except Exception as exc:
        logger.error(f"删除板块 ETF 失败: {exc}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"error": "internal_error", "message": f"删除板块失败: {str(exc)}"},
        )
