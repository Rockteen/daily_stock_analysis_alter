# -*- coding: utf-8 -*-
"""
AI 产业链分析报告生成

生成 Markdown 格式的产业链全景报告，可嵌入现有的日报/周报流程。
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Dict, List, Optional

from src.industry_chain.models import (
    ChainLayer,
    ChainScanResult,
    LayerAllocation,
    LayerScoreCard,
    ScoreDimension,
    SignalOutput,
    ThesisStatus,
    ThesisValidationReport,
)

logger = logging.getLogger(__name__)


class ChainReportGenerator:
    """产业链报告生成器"""

    def __init__(self):
        self._score_dim_display = {
            ScoreDimension.PROFITABILITY: "💰 利润率",
            ScoreDimension.MOAT: "🛡️ 竞争壁垒",
            ScoreDimension.BOTTLENECK: "🔗 供给瓶颈",
            ScoreDimension.GROWTH: "📈 增长动能",
            ScoreDimension.VALUATION: "⚖️ 估值压力",
        }

    def generate(self, result: ChainScanResult) -> str:
        """生成完整产业链报告"""
        sections = [
            self._header(result),
            self._layer_ranking(result.score_cards),
            self._layer_detail(result.score_cards),
            self._thesis_report(result.thesis_report),
            self._signal_summary(result.signals),
            self._key_variables(result.variables),
            self._footer(result),
        ]
        return "\n\n".join(sections)

    def generate_compact(self, result: ChainScanResult) -> str:
        """生成简版报告（适合嵌入已有日报）"""
        sections = [
            self._header(result),
            self._layer_ranking(result.score_cards),
            self._thesis_compact(result.thesis_report),
        ]
        return "\n\n".join(sections)

    # ---------------------------------------------------------------
    # Sections
    # ---------------------------------------------------------------

    @staticmethod
    def _header(result: ChainScanResult) -> str:
        scan_date = result.scan_date.isoformat()
        status_icon = {
            "success": "✅",
            "partial": "⚠️",
            "failed": "❌",
        }.get(result.status, "❓")
        return (
            f"# AI 产业链全景扫描\n\n"
            f"**日期**: {scan_date}  {status_icon}\n\n"
            f"覆盖 {result.company_count} 家公司，"
            f"其中 {result.companies_with_data} 家有可用数据"
            + (f"\n⏱ {result.duration_seconds:.1f}s" if result.duration_seconds else "")
        )

    def _layer_ranking(self, score_cards: List[LayerScoreCard]) -> str:
        if not score_cards:
            return "## 链层评分排名\n\n（暂无数据）"

        lines = [
            "## 一、链层评分排名\n",
            "| 排名 | 链层 | 综合评分 | 利润率 | 壁垒 | 瓶颈 | 增长 | 估值 | 配置建议 |",
            "|------|------|---------|--------|------|------|------|------|---------|",
        ]

        sorted_cards = sorted(score_cards, key=lambda c: c.composite_rank or 99)
        for card in sorted_cards:
            scores = {s.dimension: s.score for s in card.dimension_scores}
            prof = scores.get(ScoreDimension.PROFITABILITY, "-")
            moat = scores.get(ScoreDimension.MOAT, "-")
            neck = scores.get(ScoreDimension.BOTTLENECK, "-")
            grow = scores.get(ScoreDimension.GROWTH, "-")
            val = scores.get(ScoreDimension.VALUATION, "-")

            row = (
                f"| {card.composite_rank or '-'} "
                f"| {card.layer.display_name} "
                f"| **{card.composite_score}** "
                f"| {prof} "
                f"| {moat} "
                f"| {neck} "
                f"| {grow} "
                f"| {val} "
                f"| {card.competitive_intensity} |"
            )
            lines.append(row)

        return "\n".join(lines)

    def _layer_detail(self, score_cards: List[LayerScoreCard]) -> str:
        if not score_cards:
            return ""

        sections = ["## 二、各层详情\n"]
        for card in sorted(score_cards, key=lambda c: c.composite_rank or 99):
            sections.append(f"### {card.composite_rank}. {card.layer.display_name}")
            sections.append(f"**综合评分**: {card.composite_score}")
            sections.append(f"**竞争强度**: {card.competitive_intensity}")
            sections.append(f"**摘要**: {card.summary}")
            sections.append("")

            for s in card.dimension_scores:
                dim_name = self._score_dim_display.get(s.dimension, s.dimension.value)
                sections.append(f"- {dim_name}: **{s.score}** (排名 {s.rank or '-'}/8)")
                sections.append(f"  - {s.explanation}")

            sections.append("")

        return "\n".join(sections)

    def _thesis_report(self, report: Optional[ThesisValidationReport]) -> str:
        if report is None or not report.theses:
            return "## 三、假说验证\n\n（未执行验证）"

        lines = [
            "## 三、关键假说验证\n",
            f"通过 {report.pass_count} / 失败 {report.fail_count} / "
            f"数据不足 {report.insufficient_count}\n",
            "| 状态 | 假说 | 实际值 | 预期 | 证据 |",
            "|------|------|--------|------|------|",
        ]

        for t in report.theses:
            icon = {
                ThesisStatus.PASS: "✅",
                ThesisStatus.FAIL: "❌",
                ThesisStatus.INSUFFICIENT_DATA: "⚠️",
                ThesisStatus.NOT_TESTED: "⬜",
            }.get(t.status, "❓")
            lines.append(
                f"| {icon} | {t.title} | {t.actual_value} | {t.expected_range} | {t.evidence} |"
            )

        return "\n".join(lines)

    def _thesis_compact(self, report: Optional[ThesisValidationReport]) -> str:
        if report is None or not report.theses:
            return "## 关键假说\n\n（无数据）"

        lines = ["## 关键假说验证\n"]
        for t in report.theses:
            icon = {
                ThesisStatus.PASS: "✅",
                ThesisStatus.FAIL: "❌",
                ThesisStatus.INSUFFICIENT_DATA: "⚠️",
            }.get(t.status, "⬜")
            lines.append(f"- {icon} **{t.title}**: {t.actual_value}（预期 {t.expected_range}）")

        return "\n".join(lines)

    def _signal_summary(self, signals: Optional[SignalOutput]) -> str:
        if signals is None:
            return ""

        lines = ["## 四、投资信号\n"]

        if signals.layer_allocations:
            lines.append("### 层配置建议\n")
            lines.append("| 层 | 建议 | 置信度 | 理由 |")
            lines.append("|----|------|--------|------|")
            icon_map = {
                LayerAllocation.OVERWEIGHT: "🟢",
                LayerAllocation.NEUTRAL: "🟡",
                LayerAllocation.UNDERWEIGHT: "🔴",
            }
            for al in signals.layer_allocations:
                icon = icon_map.get(al.allocation, "⚪")
                lines.append(
                    f"| {icon} {al.layer.display_name} "
                    f"| {al.allocation.value} "
                    f"| {al.confidence:.0%} "
                    f"| {al.reasoning[:60]} |"
                )

        if signals.company_recommendations:
            buy_signals = [
                r for r in signals.company_recommendations
                if r.signal.value in ("strong_buy", "buy")
            ]
            if buy_signals:
                lines.append("\n### 推荐关注\n")
                lines.append("| 公司 | 层 | 信号 | 置信度 |")
                lines.append("|------|-----|------|--------|")
                for r in buy_signals[:10]:
                    lines.append(
                        f"| {r.name} | {r.layer.display_name} "
                        f"| {r.signal.value} | {r.confidence:.0%} |"
                    )

        if signals.key_alerts:
            lines.append("\n### ⚠️ 预警\n")
            for alert in signals.key_alerts:
                lines.append(f"- {alert}")

        return "\n".join(lines)

    @staticmethod
    def _key_variables(variables) -> str:
        if variables is None:
            return ""

        lines = ["## 五、关键变量追踪\n"]
        lines.append("| 变量 | 类别 | 当前值 | 趋势 | 信号 |")
        lines.append("|------|------|--------|------|------|")

        icon_map = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}
        trend_map = {"up": "↑", "down": "↓", "stable": "→"}

        for var in variables.variables:
            icon = icon_map.get(var.signal, "⚪")
            trend = trend_map.get(var.trend, "→")
            current = f"{var.current_value} {var.unit}" if var.current_value is not None else "N/A"
            lines.append(
                f"| {var.display_name} | {var.category} "
                f"| {current} | {trend} | {icon} {var.signal} |"
            )

        return "\n".join(lines)

    @staticmethod
    def _footer(result: ChainScanResult) -> str:
        parts = ["---"]
        if result.errors:
            parts.append(f"\n**错误**: {len(result.errors)} 个")
            for e in result.errors[:5]:
                parts.append(f"- {e}")
        parts.append(f"\n*由 AI 产业链量化验证子系统自动生成*")
        return "\n".join(parts)
