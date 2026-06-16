# -*- coding: utf-8 -*-
"""
AI 产业链分析命令行入口

用法:
    python -m src.industry_chain.cli scan          # 全量产业链扫描
    python -m src.industry_chain.cli scan --compact  # 简版报告
    python -m src.industry_chain.cli layer AI_ACCELERATOR   # 单层分析
    python -m src.industry_chain.cli thesis         # 所有假说验证
    python -m src.industry_chain.cli thesis nvda_margin  # 单条假说验证
    python -m src.industry_chain.cli companies      # 列出注册的公司
    python -m src.industry_chain.cli layers         # 列出所有链层
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from datetime import date
from typing import Any, Dict, List

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("industry_chain.cli")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="AI 产业链量化验证子系统",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # scan
    scan_p = sub.add_parser("scan", help="全量产业链扫描")
    scan_p.add_argument("--compact", action="store_true", help="输出简版报告")
    scan_p.add_argument("--no-cache", action="store_true", help="跳过缓存，强制刷新")

    # layer
    layer_p = sub.add_parser("layer", help="分析指定链层")
    layer_p.add_argument("name", help="链层枚举值（如 AI_ACCELERATOR）")

    # thesis
    thesis_p = sub.add_parser("thesis", help="假说验证")
    thesis_p.add_argument("id", nargs="?", default=None, help="假说 ID（可选，不传则验证全部）")

    # companies
    sub.add_parser("companies", help="列出注册的公司")

    # layers
    sub.add_parser("layers", help="列出所有链层")

    # track
    sub.add_parser("track", help="关键变量追踪（占位）")

    return parser


def _cmd_scan(args: argparse.Namespace) -> int:
    """执行全量扫描"""
    from src.industry_chain.data.financial import ChainFinancialFetcher
    from src.industry_chain.analysis.layer_scorer import LayerScorer
    from src.industry_chain.analysis.thesis_validator import ThesisValidator
    from src.industry_chain.analysis.signal_generator import SignalGenerator
    from src.industry_chain.reporting.chain_report import ChainReportGenerator
    from src.industry_chain.registry import get_all_companies
    from src.industry_chain.models import ChainScanResult

    logger.info("开始 AI 产业链全量扫描...")
    start = time.time()

    fetcher = ChainFinancialFetcher(use_cache=not args.no_cache)
    scorer = LayerScorer()
    validator = ThesisValidator()
    signal_gen = SignalGenerator()
    reporter = ChainReportGenerator()

    companies = get_all_companies()
    logger.info("注册公司总数: %d", len(companies))

    # 1. 获取财务数据
    logger.info("正在拉取财务数据...")
    financials = fetcher.full_snapshot()
    logger.info("获取到 %d 家公司的财务数据", len(financials))

    # 2. 构建层快照和评分
    snapshots = scorer.build_layer_snapshots(financials)
    score_cards = scorer.score_all(snapshots)

    # 3. 假说验证
    thesis_report = validator.validate_all(
        layer_snapshots=snapshots,
        financials=financials,
    )

    # 4. 信号
    signals = signal_gen.generate(
        score_cards=score_cards,
        thesis_report=thesis_report,
        financials=financials,
    )

    # 5. 组装结果
    result = ChainScanResult(
        scan_date=date.today(),
        company_count=len(companies),
        companies_with_data=len(financials),
        score_cards=score_cards,
        thesis_report=thesis_report,
        signals=signals,
        duration_seconds=round(time.time() - start, 1),
    )

    # 6. 输出报告
    report = reporter.generate_compact(result) if args.compact else reporter.generate(result)
    print("\n" + report)

    return 0


def _cmd_layer(args: argparse.Namespace) -> int:
    """单层分析"""
    from src.industry_chain.models import ChainLayer

    # 支持大小写不敏感的名称匹配
    name = args.name.upper()
    layer_map = {
        "SEMI_EQUIPMENT": ChainLayer.SEMI_EQUIPMENT,
        "SEMICONDUCTOR_EQUIPMENT": ChainLayer.SEMI_EQUIPMENT,
        "FOUNDRY": ChainLayer.FOUNDRY_PACKAGE,
        "FOUNDRY_PACKAGE": ChainLayer.FOUNDRY_PACKAGE,
        "AI_ACCELERATOR": ChainLayer.AI_ACCELERATOR,
        "ACCELERATOR": ChainLayer.AI_ACCELERATOR,
        "HBM": ChainLayer.HBM_MEMORY,
        "HBM_MEMORY": ChainLayer.HBM_MEMORY,
        "SERVER": ChainLayer.SERVER_NETWORK,
        "SERVER_NETWORK": ChainLayer.SERVER_NETWORK,
        "CLOUD": ChainLayer.CLOUD_IAAS,
        "CLOUD_IAAS": ChainLayer.CLOUD_IAAS,
        "MODEL": ChainLayer.BASE_MODEL_API,
        "BASE_MODEL": ChainLayer.BASE_MODEL_API,
        "APPLICATION": ChainLayer.APPLICATION_SAAS,
        "APPLICATION_SAAS": ChainLayer.APPLICATION_SAAS,
    }

    layer = layer_map.get(name)
    if layer is None:
        print(f"无效链层: {args.name}")
        print(f"有效值: {', '.join(sorted(layer_map.keys()))}")
        return 1

    # 复用 tool handler
    from src.industry_chain.tools.industry_tools import handle_get_layer_analysis
    result = handle_get_layer_analysis(layer.value)

    if not result.get("success"):
        print(f"错误: {result.get('error', '未知错误')}")
        return 1

    print(f"\n{'='*50}")
    print(f"链层: {result['display_name']}")
    print(f"综合评分: {result['composite_score']} (排名 {result['rank']}/8)")
    print(f"竞争强度: {result['competitive_intensity']}")
    print(f"摘要: {result['summary']}")
    print(f"{'='*50}\n")

    print("评分维度:")
    for ds in result.get("dimension_scores", []):
        print(f"  - {ds['dimension']}: {ds['score']} (排名 {ds['rank']})")

    print("\n公司推荐:")
    for r in result.get("recommendations", []):
        print(f"  - {r['name']} ({r['ticker']}): {r['signal']}")

    return 0


def _cmd_thesis(args: argparse.Namespace) -> int:
    """假说验证"""
    from src.industry_chain.tools.industry_tools import handle_validate_chain_thesis
    from src.industry_chain.reporting.chain_report import ChainReportGenerator

    result = handle_validate_chain_thesis(args.id)

    if not result.get("success"):
        print(f"错误: {result.get('error', '未知错误')}")
        return 1

    print(f"\n{'='*50}")
    print("AI 产业链假说验证结果")
    print(f"{'='*50}\n")

    for t in result.get("theses", []):
        icon = {"pass": "✅", "fail": "❌", "insufficient_data": "⚠️", "not_tested": "⬜"}
        status_label = {
            "pass": "通过", "fail": "未通过", "insufficient_data": "数据不足", "not_tested": "未测试"
        }
        print(f"{icon.get(t['status'], '❓')} [{status_label.get(t['status'], t['status'])}] {t['title']}")
        print(f"    实际: {t['actual_value']} | 预期: {t['expected_range']}")
        print(f"    证据: {t['evidence']}")
        print()

    summary = result.get("summary")
    if summary:
        print(f"汇总: ✅通过 {summary['pass']} / ❌失败 {summary['fail']} / ⚠️不足 {summary['insufficient_data']}")

    return 0


def _cmd_companies(args: argparse.Namespace) -> int:
    """列出公司"""
    from src.industry_chain.registry import get_all_companies, count_by_layer

    companies = get_all_companies()
    by_layer = count_by_layer()

    print(f"\nAI 产业链公司注册表（共 {len(companies)} 家）\n")
    for layer_name, count in sorted(by_layer.items(), key=lambda x: x[0]):
        print(f"  {layer_name}: {count} 家")

    print(f"\n所有 ticker: {', '.join(sorted(c.ticker_yf for c in companies if c.ticker_yf))}")
    return 0


def _cmd_layers(args: argparse.Namespace) -> int:
    """列出链层"""
    from src.industry_chain.registry import get_layers

    print("\nAI 产业链 8 层结构:\n")
    for layer in get_layers():
        print(f"  {layer.sort_order}. {layer.display_name} ({layer.value})")
    return 0


def _cmd_track(args: argparse.Namespace) -> int:
    """关键变量追踪（占位，后续实现自动更新）"""
    from src.industry_chain.data.key_variables import KeyVariableManager

    mgr = KeyVariableManager()
    print("\n关键变量追踪:\n")
    for var in mgr.get_all():
        auto_flag = "🤖" if var.is_automated else "✋"
        current = f"{var.current_value} {var.unit}" if var.current_value is not None else "N/A"
        print(f"  {auto_flag} {var.display_name}")
        print(f"      当前: {current} | 趋势: {var.trend} | 信号: {var.signal}")
        print(f"      来源: {var.data_source_desc}")
        print()
    return 0


_COMMANDS = {
    "scan": _cmd_scan,
    "layer": _cmd_layer,
    "thesis": _cmd_thesis,
    "companies": _cmd_companies,
    "layers": _cmd_layers,
    "track": _cmd_track,
}


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return 1

    handler = _COMMANDS.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
