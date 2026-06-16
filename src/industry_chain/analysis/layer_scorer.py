# -*- coding: utf-8 -*-
"""
AI 产业链链层评分引擎

按层聚合财务数据，从 5 个维度评分并排序：
  1. 利润率（毛利率 + 运营利润率）
  2. 竞争壁垒（HHI + 玩家数量 + 技术门槛）
  3. 供给瓶颈度（稀缺性 + 产能约束）
  4. 增长动能（收入增速 + Capex 趋势）
  5. 估值压力（PE 分位数）
"""

from __future__ import annotations

import logging
from statistics import mean, median
from typing import Dict, List, Optional

from src.industry_chain.models import (
    ChainLayer,
    CompanyFinancials,
    LayerFinancialSnapshot,
    LayerScore,
    LayerScoreCard,
    ScoreDimension,
)

logger = logging.getLogger(__name__)


# ============================================================
# 技术门槛系数（每层的技术/准入壁垒程度，0-1）
# 这个系数是框架的定性判断，用于补充 HHI 的不足
# ============================================================
_TECH_BARRIER: Dict[ChainLayer, float] = {
    ChainLayer.SEMI_EQUIPMENT: 0.95,       # EUV 光刻机不可替代，EDA 生态壁垒极高
    ChainLayer.FOUNDRY_PACKAGE: 0.90,       # 先进制程只有 TSMC 能规模量产
    ChainLayer.AI_ACCELERATOR: 0.95,        # CUDA 生态 + 互联系统，软硬一体
    ChainLayer.HBM_MEMORY: 0.75,            # HBM 设计/封装难度大，但存储周期性
    ChainLayer.SERVER_NETWORK: 0.40,        # 硬件集成壁垒低，但网络/光模块有壁垒
    ChainLayer.CLOUD_IAAS: 0.80,            # 规模效应 + 客户锁定，但投资极重
    ChainLayer.BASE_MODEL_API: 0.50,        # 需要顶尖人才和数据，但开源在追赶
    ChainLayer.APPLICATION_SAAS: 0.25,      # 创业门槛低，功能同质化快
}

# 供给稀缺性系数（0-1），反映该层产能是否限制行业总产出
_BOTTLENECK_RATING: Dict[ChainLayer, float] = {
    ChainLayer.SEMI_EQUIPMENT: 0.85,        # EUV 产能限制全行业
    ChainLayer.FOUNDRY_PACKAGE: 0.90,       # CoWoS / N3 产能是当前最关键的物理瓶颈
    ChainLayer.AI_ACCELERATOR: 0.60,        # 设计/生态壁垒高但不像物理制造那样受限
    ChainLayer.HBM_MEMORY: 0.85,            # HBM 产能是显存瓶颈
    ChainLayer.SERVER_NETWORK: 0.50,        # 电力/液冷/光模块有局部瓶颈
    ChainLayer.CLOUD_IAAS: 0.30,            # 云容量可通过扩张缓解
    ChainLayer.BASE_MODEL_API: 0.20,        # 模型数量不受物理限制
    ChainLayer.APPLICATION_SAAS: 0.10,      # 应用供给几乎无物理限制
}


class LayerScorer:
    """链层评分引擎

    用法:
        scorer = LayerScorer()
        financials = fetcher.full_snapshot()         # 从 Phase 2 获取
        snapshots = scorer.build_layer_snapshots(financials)
        cards = scorer.score_all(snapshots)
    """

    def build_layer_snapshots(
        self, financials_list: List[CompanyFinancials]
    ) -> Dict[ChainLayer, LayerFinancialSnapshot]:
        """将公司财务数据聚合到层级别"""
        # 按层分组
        by_layer: Dict[ChainLayer, List[CompanyFinancials]] = {}
        for fin in financials_list:
            by_layer.setdefault(fin.layer, []).append(fin)

        snapshots: Dict[ChainLayer, LayerFinancialSnapshot] = {}
        for layer, companies in by_layer.items():
            snapshots[layer] = self._aggregate(layer, companies)

        return snapshots

    def score_all(
        self, snapshots: Dict[ChainLayer, LayerFinancialSnapshot]
    ) -> List[LayerScoreCard]:
        """对所有链层进行评分，返回排序后的评分卡"""
        cards: List[LayerScoreCard] = []

        for layer, snapshot in snapshots.items():
            card = self._score_single_layer(layer, snapshot)
            cards.append(card)

        # 计算排名
        self._assign_ranks(cards)

        return cards

    def score_single(
        self, layer: ChainLayer, snapshot: LayerFinancialSnapshot
    ) -> LayerScoreCard:
        """评分单个链层"""
        card = self._score_single_layer(layer, snapshot)
        return card

    # ---------------------------------------------------------------
    # 聚合
    # ---------------------------------------------------------------

    def _aggregate(self, layer: ChainLayer, companies: List[CompanyFinancials]) -> LayerFinancialSnapshot:
        """聚合单层公司的财务指标"""
        gms = [c.gross_margin for c in companies if c.gross_margin is not None]
        oms = [c.operating_margin for c in companies if c.operating_margin is not None]
        nms = [c.net_margin for c in companies if c.net_margin is not None]
        rev_growth = [c.revenue_growth for c in companies if c.revenue_growth is not None]
        pes = [c.pe_ratio for c in companies if c.pe_ratio is not None]
        pss = [c.ps_ratio for c in companies if c.ps_ratio is not None]
        mcaps = [c.market_cap for c in companies if c.market_cap is not None]
        revs = [c.revenue for c in companies if c.revenue is not None]
        capes = [c.capex for c in companies if c.capex is not None]

        core_count = sum(1 for c in companies if getattr(c, "_is_core", True))

        # 计算 HHI（基于收入的市场集中度）
        total_rev = sum(revs) if revs else None
        hhi = None
        if total_rev and total_rev > 0:
            shares = [(r / total_rev) ** 2 for r in revs]
            hhi = round(sum(shares) * 10000, 2)

        return LayerFinancialSnapshot(
            layer=layer,
            company_count=len(companies),
            core_player_count=core_count,
            avg_gross_margin=round(mean(gms), 2) if gms else None,
            avg_operating_margin=round(mean(oms), 2) if oms else None,
            avg_net_margin=round(mean(nms), 2) if nms else None,
            avg_revenue_growth=round(mean(rev_growth), 2) if rev_growth else None,
            avg_pe_ratio=round(mean(pes), 2) if pes else None,
            avg_ps_ratio=round(mean(pss), 2) if pss else None,
            median_gross_margin=round(median(gms), 2) if gms else None,
            median_revenue_growth=round(median(rev_growth), 2) if rev_growth else None,
            total_market_cap=round(sum(mcaps), 2) if mcaps else None,
            total_revenue=round(total_rev, 2) if total_rev else None,
            total_capex=round(sum(capes), 2) if capes else None,
            herfindahl_index=hhi,
            margin_std=round(__import__("statistics").stdev(gms), 2) if len(gms) >= 2 else None,
            company_details=companies,
        )

    # ---------------------------------------------------------------
    # 评分
    # ---------------------------------------------------------------

    def _score_single_layer(self, layer: ChainLayer, snapshot: LayerFinancialSnapshot) -> LayerScoreCard:
        """对单层进行 5 维评分"""
        scores: List[LayerScore] = [
            self._score_profitability(layer, snapshot),
            self._score_moat(layer, snapshot),
            self._score_bottleneck(layer),
            self._score_growth(layer, snapshot),
            self._score_valuation(layer, snapshot),
        ]

        # 计算加权综合得分
        total_weight = sum(s.weight for s in scores)
        composite = sum(s.score * s.weight for s in scores) / total_weight if total_weight > 0 else 0
        composite = round(composite, 2)

        # 竞争强度判断
        intensity = self._judge_intensity(layer, snapshot, scores)

        return LayerScoreCard(
            layer=layer,
            dimension_scores=scores,
            composite_score=composite,
            summary=self._build_summary(layer, composite, intensity),
            competitive_intensity=intensity,
        )

    def _score_profitability(self, layer: ChainLayer, snapshot: LayerFinancialSnapshot) -> LayerScore:
        """利润率评分：毛利率 60% + 运营利润率 40%"""
        gm = snapshot.avg_gross_margin or 0
        om = snapshot.avg_operating_margin or 0

        # 毛利率评分：30% → 50分，50% → 70分，70%+ → 95分
        gm_score = min(95, max(0, gm * 1.0 + 20))
        # 运营利润率评分
        om_score = min(95, max(0, om * 1.2 + 20))
        combined = round(gm_score * 0.6 + om_score * 0.4, 2)

        return LayerScore(
            dimension=ScoreDimension.PROFITABILITY,
            score=combined,
            weight=0.25,
            explanation=(
                f"毛利率 {gm}% ×0.6 + 运营利润率 {om}% ×0.4 = {combined}"
            ),
        )

    def _score_moat(self, layer: ChainLayer, snapshot: LayerFinancialSnapshot) -> LayerScore:
        """竞争壁垒评分：HHI + 玩家数 + 技术门槛"""
        hhi = snapshot.herfindahl_index or 0
        n = snapshot.company_count or 1
        tech = _TECH_BARRIER.get(layer, 0.5)

        # HHI 评分：>2500 → 90分, 1500-2500 → 70分, <1500 → 40分
        if hhi >= 2500:
            hhi_score = 90
        elif hhi >= 1500:
            hhi_score = 70
        elif hhi >= 1000:
            hhi_score = 50
        else:
            hhi_score = 30

        # 玩家数量评分：越少分越高
        if n <= 2:
            n_score = 90
        elif n <= 4:
            n_score = 70
        elif n <= 8:
            n_score = 50
        else:
            n_score = 30

        # 技术门槛评分直接使用系数
        tech_score = tech * 100

        # 综合
        combined = round(hhi_score * 0.3 + n_score * 0.2 + tech_score * 0.5, 2)
        intensity = "高" if tech > 0.8 else "中高" if tech > 0.6 else "中" if tech > 0.3 else "低"

        return LayerScore(
            dimension=ScoreDimension.MOAT,
            score=combined,
            weight=0.25,
            explanation=(
                f"HHI {hhi}/10000 ({hhi_score}) ×0.3 + "
                f"玩家数 {n} ({n_score}) ×0.2 + "
                f"技术门槛 {tech:.2f} ({tech_score}) ×0.5 = {combined} "
                f"(竞争强度: {intensity})"
            ),
        )

    def _score_bottleneck(self, layer: ChainLayer) -> LayerScore:
        """供给瓶颈度评分"""
        rating = _BOTTLENECK_RATING.get(layer, 0.3)
        score = round(rating * 100, 2)

        return LayerScore(
            dimension=ScoreDimension.BOTTLENECK,
            score=score,
            weight=0.20,
            explanation=(
                f"供给稀缺系数 {rating:.2f} × 100 = {score}"
            ),
        )

    def _score_growth(self, layer: ChainLayer, snapshot: LayerFinancialSnapshot) -> LayerScore:
        """增长动能评分：收入增速 + Capex 趋势"""
        rev_g = snapshot.avg_revenue_growth or 0

        # 增速评分：>50% → 95, 20-50% → 75, 0-20% → 50, <0 → 20
        if rev_g > 50:
            base = 95
        elif rev_g > 20:
            base = 75
        elif rev_g > 0:
            base = 50
        elif rev_g > -10:
            base = 30
        else:
            base = 15

        score = round(min(95, max(5, base)), 2)

        return LayerScore(
            dimension=ScoreDimension.GROWTH,
            score=score,
            weight=0.15,
            explanation=(
                f"收入增速 {rev_g}% → 得分 {score}"
            ),
        )

    def _score_valuation(self, layer: ChainLayer, snapshot: LayerFinancialSnapshot) -> LayerScore:
        """估值压力评分：PE 越低分越高（估值压力小）"""
        pe = snapshot.avg_pe_ratio or 0
        ps = snapshot.avg_ps_ratio or 0

        # PE 评分
        if pe <= 0:
            pe_score = 50  # 亏损，中性
        elif pe <= 15:
            pe_score = 85  # 低估
        elif pe <= 25:
            pe_score = 70  # 合理
        elif pe <= 40:
            pe_score = 50  # 偏高
        elif pe <= 60:
            pe_score = 35  # 高估
        else:
            pe_score = 20  # 极高

        # 注意：这里是"估值压力"评分——PE越低说明越没估值压力，分越高
        score = round(pe_score, 2)

        return LayerScore(
            dimension=ScoreDimension.VALUATION,
            score=score,
            weight=0.15,
            explanation=(
                f"PE {pe} → 估值压力评分 {score}（越高越安全）"
            ),
        )

    # ---------------------------------------------------------------
    # 排名和摘要
    # ---------------------------------------------------------------

    def _assign_ranks(self, cards: List[LayerScoreCard]) -> None:
        """按综合得分从高到低排名"""
        sorted_cards = sorted(cards, key=lambda c: c.composite_score, reverse=True)
        for rank, card in enumerate(sorted_cards, 1):
            card.composite_rank = rank

        # 各维度排名
        for dim in ScoreDimension:
            sorted_by_dim = sorted(
                cards,
                key=lambda c: next(
                    (s.score for s in c.dimension_scores if s.dimension == dim), 0
                ),
                reverse=True,
            )
            for rank, card in enumerate(sorted_by_dim, 1):
                for s in card.dimension_scores:
                    if s.dimension == dim:
                        s.rank = rank
                        break

    def _judge_intensity(
        self,
        layer: ChainLayer,
        snapshot: LayerFinancialSnapshot,
        scores: List[LayerScore],
    ) -> str:
        """判断竞争强度"""
        moat_score = next(
            (s.score for s in scores if s.dimension == ScoreDimension.MOAT), 50
        )
        n = snapshot.company_count

        if n >= 10 and moat_score < 50:
            return "很高"
        if n >= 6 and moat_score < 40:
            return "高"
        if moat_score > 80:
            return "低"
        if moat_score > 60:
            return "中低"
        return "中"

    def _build_summary(self, layer: ChainLayer, composite: float, intensity: str) -> str:
        judges = {
            "很高": "竞争激烈，利润微薄，需精选个股",
            "高": "进入壁垒较低，关注成本领先或差异化能力",
            "中": "有一定壁垒，关注份额提升的龙头",
            "中低": "壁垒明显，龙头享受定价权溢价",
            "低": "寡头格局，利润率稳定且可持续",
        }
        judge = judges.get(intensity, "")
        return f"{layer.display_name}: 综合评分 {composite}，竞争强度「{intensity}」，{judge}"
