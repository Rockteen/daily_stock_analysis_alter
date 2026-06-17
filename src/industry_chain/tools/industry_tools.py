# -*- coding: utf-8 -*-
"""
Agent 工具注册 - AI 产业链分析

向 Agent 系统注册产业链分析工具，供 AI Agent 调用。
注册方式参照 `src/agent/tools/analysis_tools.py`。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 延迟导入以避免循环依赖
_CHAIN_REGISTRY = None
_FETCHER = None
_SCORER = None
_VALIDATOR = None
_SIGNAL = None
_REPORTER = None


def _lazy_init():
    global _CHAIN_REGISTRY, _FETCHER, _SCORER, _VALIDATOR, _SIGNAL, _REPORTER
    if _FETCHER is not None:
        return

    from src.industry_chain.data.financial import ChainFinancialFetcher
    from src.industry_chain.analysis.layer_scorer import LayerScorer
    from src.industry_chain.analysis.thesis_validator import ThesisValidator
    from src.industry_chain.analysis.signal_generator import SignalGenerator
    from src.industry_chain.reporting.chain_report import ChainReportGenerator
    from src.industry_chain.registry import get_all_companies, get_layers

    _FETCHER = ChainFinancialFetcher()
    _SCORER = LayerScorer()
    _VALIDATOR = ThesisValidator()
    _SIGNAL = SignalGenerator()
    _REPORTER = ChainReportGenerator()


def handle_get_industry_chain_overview(
    refresh: bool = False,
    compact: bool = False,
) -> Dict[str, Any]:
    """获取 AI 产业链全景扫描结果

    Args:
        refresh: 是否强制刷新数据（跳过缓存）
        compact: 是否输出简版报告

    Returns:
        包含报告文本和统计信息的字典
    """
    try:
        _lazy_init()

        # 1. 获取财务数据
        financials = _FETCHER.full_snapshot()

        # 2. 构建层快照并评分
        from src.industry_chain.registry import get_all_companies
        companies = get_all_companies()

        snapshots = _SCORER.build_layer_snapshots(financials)
        score_cards = _SCORER.score_all(snapshots)

        # 3. 假说验证
        thesis_report = _VALIDATOR.validate_all(
            layer_snapshots=snapshots,
            financials=financials,
        )

        # 4. 生成信号
        signals = _SIGNAL.generate(
            score_cards=score_cards,
            thesis_report=thesis_report,
            financials=financials,
        )

        # 5. 组装结果
        from datetime import date
        from src.industry_chain.models import ChainScanResult

        result = ChainScanResult(
            scan_date=date.today(),
            company_count=len(companies),
            companies_with_data=len(financials),
            score_cards=score_cards,
            thesis_report=thesis_report,
            signals=signals,
        )

        # 6. 生成报告
        report = _REPORTER.generate_compact(result) if compact else _REPORTER.generate(result)

        layers_data = []
        for card in score_cards:
            layers_data.append({
                "layer": card.layer.value,
                "display_name": card.layer.display_name,
                "rank": card.composite_rank,
                "composite_score": card.composite_score,
                "competitive_intensity": card.competitive_intensity,
            })

        return {
            "success": True,
            "report": report,
            "stats": {
                "company_count": result.company_count,
                "companies_with_data": result.companies_with_data,
                "thesis_pass": result.thesis_report.pass_count if result.thesis_report else 0,
                "thesis_fail": result.thesis_report.fail_count if result.thesis_report else 0,
                "thesis_insufficient": result.thesis_report.insufficient_count if result.thesis_report else 0,
            },
            "layers": layers_data,
        }

    except Exception as exc:
        logger.error("handle_get_industry_chain_overview failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}


def handle_get_layer_analysis(layer_name: str) -> Dict[str, Any]:
    """分析指定链层

    Args:
        layer_name: 链层枚举值，如 "ai_accelerator" / "hbm_memory_and_storage"

    Returns:
        该层的详细分析
    """
    try:
        _lazy_init()

        from src.industry_chain.models import ChainLayer

        try:
            layer = ChainLayer(layer_name)
        except ValueError:
            valid = [l.value for l in ChainLayer]
            return {"success": False, "error": f"无效链层: {layer_name}，有效值: {valid}"}

        # 获取该层公司
        from src.industry_chain.registry import get_companies_by_layer
        companies = get_companies_by_layer(layer)
        if not companies:
            return {"success": False, "error": f"链层 {layer.display_name} 没有注册的公司"}

        # 获取财务数据
        financials = _FETCHER.full_snapshot(companies)
        snapshots = _SCORER.build_layer_snapshots(financials)
        card = _SCORER.score_single(layer, snapshots.get(layer))

        # 该层公司推荐
        from src.industry_chain.analysis.signal_generator import SignalGenerator
        sig = SignalGenerator()
        layer_scores = {card.layer: card.composite_score}
        recommendations = []
        for fin in financials:
            signal, reasoning = sig._judge_company(fin, layer_scores.get(fin.layer, 50))
            recommendations.append({
                "ticker": fin.ticker,
                "name": fin.name,
                "signal": signal.value,
                "reasoning": reasoning,
            })

        return {
            "success": True,
            "layer": layer.value,
            "display_name": layer.display_name,
            "composite_score": card.composite_score,
            "rank": card.composite_rank,
            "competitive_intensity": card.competitive_intensity,
            "summary": card.summary,
            "dimension_scores": [
                {
                    "dimension": s.dimension.value,
                    "score": s.score,
                    "rank": s.rank,
                    "explanation": s.explanation,
                }
                for s in card.dimension_scores
            ],
            "companies": [
                {
                    "code": c.code,
                    "name": c.name,
                    "ticker": c.ticker_yf,
                    "role": c.description,
                }
                for c in companies
            ],
            "recommendations": recommendations,
        }

    except Exception as exc:
        logger.error("handle_get_layer_analysis failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}


def handle_validate_chain_thesis(thesis_id: Optional[str] = None) -> Dict[str, Any]:
    """验证产业链框架假说

    Args:
        thesis_id: 指定验证单个假说（如 "nvda_margin"），不传则验证全部

    Returns:
        假说验证结果
    """
    try:
        _lazy_init()

        # 获取财务数据
        financials = _FETCHER.full_snapshot()
        snapshots = _SCORER.build_layer_snapshots(financials)

        if thesis_id:
            report = _VALIDATOR.validate_one(thesis_id, snapshots, financials)
            if report is None:
                valid_ids = [t["id"] for t in _VALIDATOR.list_theses()]
                return {"success": False, "error": f"未知假说: {thesis_id}，有效值: {valid_ids}"}
            theses_data = [_thesis_to_dict(report)]
        else:
            report = _VALIDATOR.validate_all(snapshots, financials)
            theses_data = [_thesis_to_dict(t) for t in report.theses]

        return {
            "success": True,
            "theses": theses_data,
            "summary": {
                "pass": sum(1 for t in theses_data if t["status"] == "pass"),
                "fail": sum(1 for t in theses_data if t["status"] == "fail"),
                "insufficient_data": sum(1 for t in theses_data if t["status"] == "insufficient_data"),
            } if not thesis_id else None,
        }

    except Exception as exc:
        logger.error("handle_validate_chain_thesis failed: %s", exc, exc_info=True)
        return {"success": False, "error": str(exc)}


def _thesis_to_dict(thesis) -> Dict[str, Any]:
    return {
        "id": thesis.thesis_id,
        "title": thesis.title,
        "status": thesis.status.value,
        "actual_value": thesis.actual_value,
        "expected_range": thesis.expected_range,
        "evidence": thesis.evidence,
        "confidence": thesis.confidence,
    }


# ============================================================
# 工具定义（供 ToolRegistry 注册）
# ============================================================

def register_all(registry) -> None:
    """将所有产业链工具注册到 Agent 的工具注册表

    Args:
        registry: ToolRegistry 实例
    """
    tool_defs = _get_tool_definitions()
    for td in tool_defs:
        registry.register(td)
    logger.info("industry_chain tools registered: %d", len(tool_defs))


def _get_tool_definitions():
    """返回工具定义列表，供 register_all 使用"""
    try:
        from src.agent.tools.registry import ToolDefinition, ToolParameter
    except ImportError:
        logger.warning("ToolRegistry not available, skipping tool registration")
        return []

    return [
        ToolDefinition(
            name="get_industry_chain_overview",
            description="获取 AI 产业链全景扫描报告，包含 8 层评分排名、假说验证结果和投资信号。"
                        "不传参数时使用缓存数据。设置 refresh=True 强制从 yfinance 拉取最新数据。",
            parameters=[
                ToolParameter(
                    name="refresh",
                    type="boolean",
                    description="是否强制刷新数据",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="compact",
                    type="boolean",
                    description="是否输出简版报告",
                    required=False,
                    default=False,
                ),
            ],
            handler=handle_get_industry_chain_overview,
            category="analysis",
        ),
        ToolDefinition(
            name="get_layer_analysis",
            description="分析指定产业链层的详细数据，包括该层所有公司的财务数据、评分和推荐。",
            parameters=[
                ToolParameter(
                    name="layer_name",
                    type="string",
                    description="链层名称（如 ai_accelerator, hbm_memory_and_storage, "
                                "foundry_and_advanced_packaging, cloud_platform_and_iaas 等）",
                    required=True,
                ),
            ],
            handler=handle_get_layer_analysis,
            category="analysis",
        ),
        ToolDefinition(
            name="validate_chain_thesis",
            description="验证 AI 产业链研究框架中的核心假说。不传 thesis_id 则验证全部。",
            parameters=[
                ToolParameter(
                    name="thesis_id",
                    type="string",
                    description="假说 ID（如 nvda_margin, application_lowest_margin, "
                                "hyperscaler_capex_growth 等）",
                    required=False,
                    default=None,
                ),
            ],
            handler=handle_validate_chain_thesis,
            category="analysis",
        ),
    ]
