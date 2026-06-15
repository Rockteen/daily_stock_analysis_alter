# -*- coding: utf-8 -*-
"""Sector Inflection API schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SectorDashboardItem(BaseModel):
    etf_code: str = Field(..., description="ETF 代码")
    sector_name: str = Field(..., description="板块名称")
    trade_date: date = Field(..., description="交易日期")
    ignition_score: int = Field(..., description="启动评分")
    distribution_score: int = Field(..., description="见顶评分")
    state: str = Field(..., description="当前状态机状态")
    prev_state: Optional[str] = Field(None, description="前一状态")
    state_reason: Optional[str] = Field(None, description="状态转移原因")
    state_entered_date: Optional[date] = Field(None, description="进入当前状态的日期")
    market_regime: str = Field(..., description="大盘环境状态 (risk_on/risk_off)")
    ignition_details: Dict[str, Any] = Field(default_factory=dict, description="启动评分细项")
    distribution_details: Dict[str, Any] = Field(default_factory=dict, description="见顶评分细项")


class SectorDashboardResponse(BaseModel):
    trade_date: date = Field(..., description="分析基准日期")
    market_regime: str = Field(..., description="大盘环境 (risk_on/risk_off)")
    items: List[SectorDashboardItem] = Field(default_factory=list, description="各板块最新状态列表")


class SectorHistoryItem(BaseModel):
    trade_date: date = Field(..., description="交易日期")
    ignition_score: int = Field(..., description="启动评分")
    distribution_score: int = Field(..., description="见顶评分")
    state: str = Field(..., description="当时状态")
    prev_state: Optional[str] = Field(None, description="前一状态")
    state_reason: Optional[str] = Field(None, description="状态转移原因")
    state_entered_date: Optional[date] = Field(None, description="进入当前状态的日期")
    market_regime: str = Field(..., description="当时大盘环境")


class SectorHistoryResponse(BaseModel):
    etf_code: str = Field(..., description="ETF 代码")
    sector_name: str = Field(..., description="板块名称")
    history: List[SectorHistoryItem] = Field(default_factory=list, description="板块历史状态序列")


class SectorScanRequest(BaseModel):
    trade_date: Optional[date] = Field(None, description="指定扫描日期，默认今天")
    force: bool = Field(False, description="是否强制重新扫描")


class SectorScanResponse(BaseModel):
    status: str = Field(..., description="执行状态 (success/failed/skipped)")
    trade_date: str = Field(..., description="执行交易日")
    market_regime: str = Field(..., description="大盘环境")
    transitions_count: int = Field(..., description="发生状态转移的板块数量")
    results: List[Dict[str, Any]] = Field(default_factory=list, description="扫描结果列表")


class SectorPoolItem(BaseModel):
    id: Optional[int] = Field(None, description="ID")
    etf_code: str = Field(..., description="ETF 代码")
    sector_name: str = Field(..., description="板块名称")
    category: Optional[str] = Field("industry", description="类别 (industry/theme/safe_haven)")
    benchmark_index: Optional[str] = Field(None, description="对应的成分股指数代码 (如 399976)")
    is_active: bool = Field(True, description="是否激活")
    created_at: Optional[datetime] = Field(None, description="创建时间")


class SectorPoolCreateRequest(BaseModel):
    etf_code: str = Field(..., description="ETF 代码")
    sector_name: str = Field(..., description="板块名称")
    category: str = Field("industry", description="类别 (industry/theme/safe_haven)")
    benchmark_index: Optional[str] = Field(None, description="对应的成分股指数代码")
    is_active: bool = Field(True, description="是否激活")
