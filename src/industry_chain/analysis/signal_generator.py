# -*- coding: utf-8 -*-
"""
信号生成器

基于链层评分和假说验证结果，生成：
  - 层级别配置建议（overweight / neutral / underweight）
  - 公司级别推荐
  - 关键预警
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

from src.industry_chain.models import (
    ChainLayer,
    CompanyFinancials,
    CompanyRecommendation,
    CompanySignal,
    LayerAllocation,
    LayerScoreCard,
    ScoreDimension,
    SignalOutput,
    ThesisStatus,
    ThesisValidationReport,
)

logger = logging.getLogger(__name__)


class SignalGenerator:
    """信号生成器

    基于评分卡和假说验证结果生成可操作的投资信号。
    """

    def generate(
        self,
        score_cards: List[LayerScoreCard],
        thesis_report: Optional[ThesisValidationReport] = None,
        financials: Optional[List[CompanyFinancials]] = None,
    ) -> SignalOutput:
        """生成完整信号"""
        output = SignalOutput()

        # 1. 层配置建议
        output.layer_allocations = self._generate_layer_allocations(score_cards, thesis_report)

        # 2. 公司推荐
        if financials:
            output.company_recommendations = self._generate_company_recos(
                score_cards, financials
            )

        # 3. 关键预警
        output.key_alerts = self._generate_alerts(score_cards, thesis_report)

        return output

    # ---------------------------------------------------------------
    # 层配置建议
    # ---------------------------------------------------------------

    def _generate_layer_allocations(
        self,
        score_cards: List[LayerScoreCard],
        thesis_report: Optional[ThesisValidationReport] = None,
    ) -> List:
        """根据综合评分生成层配置建议"""
        # 排序
        sorted_cards = sorted(score_cards, key=lambda c: c.composite_score, reverse=True)

        allocations: List = []
        for i, card in enumerate(sorted_cards):
            # 前 3 名 → overweight
            if i < 3:
                allocation = LayerAllocation.OVERWEIGHT
                confidence = round(0.5 + 0.3 * (1 - i / len(sorted_cards)), 2)
            # 中间 → neutral
            elif i < len(sorted_cards) - 2:
                allocation = LayerAllocation.NEUTRAL
                confidence = 0.5
            # 后 2 名 → underweight
            else:
                allocation = LayerAllocation.UNDERWEIGHT
                confidence = round(0.5 + 0.2 * (i / len(sorted_cards)), 2)

            # 如果假说验证中有 pass/fail 信息，可调整置信度
            if thesis_report:
                for thesis in thesis_report.theses:
                    # 如果"应用层最容易卷"通过 → 提高应用层 underweight 信心
                    if thesis.thesis_id == "application_lowest_margin" \
                            and thesis.status == ThesisStatus.PASS \
                            and card.layer == ChainLayer.APPLICATION_SAAS:
                        if allocation == LayerAllocation.UNDERWEIGHT:
                            confidence = min(1.0, confidence + 0.15)

            allocations.append(
                type("AllocationSignal", (), {
                    "layer": card.layer,
                    "allocation": allocation,
                    "confidence": confidence,
                    "reasoning": f"综合评分 {card.composite_score}，排名 {card.composite_rank}/8。{card.summary}",
                })()
            )

        return allocations

    # ---------------------------------------------------------------
    # 公司推荐
    # ---------------------------------------------------------------

    def _generate_company_recos(
        self,
        score_cards: List[LayerScoreCard],
        financials: List[CompanyFinancials],
    ) -> List[CompanyRecommendation]:
        """生成公司级别推荐"""
        # 建立层评分映射
        layer_scores: Dict[ChainLayer, float] = {
            card.layer: card.composite_score for card in score_cards
        }

        recommendations: List[CompanyRecommendation] = []
        for fin in financials:
            if fin.revenue is None:
                continue

            layer_score = layer_scores.get(fin.layer, 50)
            signal, reasoning = self._judge_company(fin, layer_score)

            recommendations.append(CompanyRecommendation(
                ticker=fin.ticker,
                name=fin.name,
                layer=fin.layer,
                signal=signal,
                reasoning=reasoning,
                confidence=self._reco_confidence(fin, layer_score),
            ))

        return recommendations

    def _judge_company(
        self, fin: CompanyFinancials, layer_score: float
    ) -> tuple:
        """判断单个公司的信号"""
        signals: List[str] = []

        # 层评分高 → 加分
        if layer_score >= 75:
            signals.append("层评分高")
        elif layer_score <= 40:
            signals.append("层评分低")

        # 毛利率高 → 加分
        if fin.gross_margin is not None:
            if fin.gross_margin > 60:
                signals.append(f"高毛利({fin.gross_margin}%)")
            elif fin.gross_margin < 15:
                signals.append(f"低毛利({fin.gross_margin}%)")

        # 收入增速高 → 加分
        if fin.revenue_growth is not None:
            if fin.revenue_growth > 30:
                signals.append(f"高速增长({fin.revenue_growth}%)")
            elif fin.revenue_growth < 0:
                signals.append(f"负增长({fin.revenue_growth}%)")

        # 估值判断
        if fin.pe_ratio is not None:
            if fin.pe_ratio < 0:
                signals.append("亏损")
            elif fin.pe_ratio > 60:
                signals.append(f"高估值(PE {fin.pe_ratio})")

        # 综合判断
        positive = sum(1 for s in signals if any(k in s for k in ["高", "增长", "层评分高"]))
        negative = sum(1 for s in signals if any(k in s for k in ["低", "负", "亏损", "高估值"]))

        # 计算净得分
        net = positive - negative

        if net >= 2:
            return CompanySignal.STRONG_BUY, "; ".join(signals)
        if net >= 1:
            return CompanySignal.BUY, "; ".join(signals)
        if net == 0:
            return CompanySignal.HOLD, "; ".join(signals) if signals else "中性"
        if net >= -1:
            return CompanySignal.SELL, "; ".join(signals)

        return CompanySignal.STRONG_SELL, "; ".join(signals)

    @staticmethod
    def _reco_confidence(fin: CompanyFinancials, layer_score: float) -> float:
        """推荐置信度"""
        base = 0.5
        if fin.data_completeness == "full":
            base += 0.2
        elif fin.data_completeness == "partial":
            base += 0.1

        # 层评分极端时置信度更高
        if layer_score >= 80 or layer_score <= 30:
            base += 0.1

        return round(min(1.0, base), 2)

    # ---------------------------------------------------------------
    # 预警
    # ---------------------------------------------------------------

    def _generate_alerts(
        self,
        score_cards: List[LayerScoreCard],
        thesis_report: Optional[ThesisValidationReport] = None,
    ) -> List[str]:
        """生成关键预警信息"""
        alerts: List[str] = []

        for card in score_cards:
            # 低分预警
            if card.composite_score < 30:
                alerts.append(
                    f"⚠️ {card.layer.display_name} 综合评分仅 {card.composite_score}，"
                    f"注意行业风险"
                )

        # 假说验证预警
        if thesis_report:
            for thesis in thesis_report.theses:
                if thesis.status == ThesisStatus.FAIL:
                    alerts.append(
                        f"📌 框架假说「{thesis.title}」未通过验证：{thesis.evidence}"
                    )

        return alerts
