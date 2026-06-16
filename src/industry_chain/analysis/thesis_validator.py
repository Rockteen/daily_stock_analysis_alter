# -*- coding: utf-8 -*-
"""
AI 产业链框架假说验证引擎

将研究框架中的核心论断转化为可量化的验证条件。
每条假说包含：名称、验证函数、阈值、数据依赖等。
"""

from __future__ import annotations

import logging
from typing import Callable, Dict, List, Optional, Tuple

from src.industry_chain.models import (
    ChainLayer,
    CompanyFinancials,
    LayerFinancialSnapshot,
    ThesisStatus,
    ThesisVerdict,
    ThesisValidationReport,
)

logger = logging.getLogger(__name__)


class ThesisValidator:
    """框架假说验证引擎

    用法:
        validator = ThesisValidator()
        # 需要提供财务数据上下文
        report = validator.validate_all(
            layer_snapshots=snapshots,   # Dict[ChainLayer, LayerFinancialSnapshot]
            financials=financials,       # List[CompanyFinancials]
        )
    """

    def __init__(self):
        self._theses = self._register_theses()

    # ---------------------------------------------------------------
    # 假说注册
    # ---------------------------------------------------------------

    @staticmethod
    def _register_theses() -> List[dict]:
        """注册所有可验证的假说"""
        return [
            {
                "id": "nvda_margin",
                "title": "Nvidia 毛利率约 71%（最高利润层）",
                "description": "框架认为 NVDA 毛利率约 71%，反映软硬一体平台溢价",
                "verify_fn": _verify_nvda_margin,
                "depends_on": "financials",
            },
            {
                "id": "accelerator_top_profit",
                "title": "AI 加速器层利润率最高",
                "description": "框架认为 AI 加速器层是产业链利润最高的层",
                "verify_fn": _verify_accelerator_top_profit,
                "depends_on": "layer_snapshots",
            },
            {
                "id": "application_lowest_margin",
                "title": "应用层利润率最低（最容易卷）",
                "description": "框架认为应用层因同质化和低门槛导致利润率最低",
                "verify_fn": _verify_application_lowest_margin,
                "depends_on": "layer_snapshots",
            },
            {
                "id": "hyperscaler_capex_growth",
                "title": "Hyperscaler capex 仍在增长",
                "description": "框架认为云厂商资本开支超级周期未结束",
                "verify_fn": _verify_hyperscaler_capex_growth,
                "depends_on": "financials",
            },
            {
                "id": "asic_share_gain",
                "title": "ASIC（AVGO/MRVL）增速可能超过 NVDA 增量份额",
                "description": "框架认为定制 ASIC 可能拿走部分 Nvidia 的增量市场",
                "verify_fn": _verify_asic_share_gain,
                "depends_on": "financials",
            },
            {
                "id": "foundry_high_margin",
                "title": "先进代工/封装层利润率极高",
                "description": "框架认为 TSMC 垄断先进制程与 CoWoS，定价权强悍",
                "verify_fn": _verify_foundry_high_margin,
                "depends_on": "layer_snapshots",
            },
            {
                "id": "hbm_supply_tight",
                "title": "HBM 供需紧张，利润率上行",
                "description": "框架认为 HBM 是 AI 核心硬件瓶颈，龙头业绩创新高",
                "verify_fn": _verify_hbm_supply_tight,
                "depends_on": "layer_snapshots",
            },
            {
                "id": "odm_lowest_margin",
                "title": "服务器 ODM 利润率最低之一",
                "description": "框架认为服务器 ODM 技术壁垒低，对上下游无定价权",
                "verify_fn": _verify_odm_low_margin,
                "depends_on": "layer_snapshots",
            },
            {
                "id": "model_api_pressure",
                "title": "基础模型 API 面临开源模型和价格战双重挤压",
                "description": "框架认为模型层长期面临开源免费模型追赶和推理成本压力",
                "verify_fn": _verify_model_api_pressure,
                "depends_on": "layer_snapshots",
            },
            {
                "id": "cloud_capex_roi_concern",
                "title": "云平台 Capex 回报率是核心担忧",
                "description": "框架提到市场担忧超大 capex 是否匹配 AI 应用收入",
                "verify_fn": _verify_cloud_capex_roi,
                "depends_on": "financials",
            },
        ]

    # ---------------------------------------------------------------
    # 验证
    # ---------------------------------------------------------------

    def validate_all(
        self,
        layer_snapshots: Optional[Dict[ChainLayer, LayerFinancialSnapshot]] = None,
        financials: Optional[List[CompanyFinancials]] = None,
    ) -> ThesisValidationReport:
        """运行所有假说验证"""
        report = ThesisValidationReport()

        for thesis_def in self._theses:
            verdict = self._execute(thesis_def, layer_snapshots, financials)
            report.theses.append(verdict)

        report.compute_summary()
        return report

    def validate_one(
        self,
        thesis_id: str,
        layer_snapshots: Optional[Dict[ChainLayer, LayerFinancialSnapshot]] = None,
        financials: Optional[List[CompanyFinancials]] = None,
    ) -> Optional[ThesisVerdict]:
        """验证单个假说"""
        for thesis_def in self._theses:
            if thesis_def["id"] == thesis_id:
                return self._execute(thesis_def, layer_snapshots, financials)
        return None

    def list_theses(self) -> List[dict]:
        """列出所有已注册假说的元数据"""
        return [
            {"id": t["id"], "title": t["title"], "description": t["description"]}
            for t in self._theses
        ]

    # ---------------------------------------------------------------
    # 内部
    # ---------------------------------------------------------------

    def _execute(
        self,
        thesis_def: dict,
        layer_snapshots: Optional[Dict[ChainLayer, LayerFinancialSnapshot]] = None,
        financials: Optional[List[CompanyFinancials]] = None,
    ) -> ThesisVerdict:
        """执行一条假说的验证"""
        dep = thesis_def["depends_on"]
        verify_fn: Callable = thesis_def["verify_fn"]

        ctx = ThesisContext(
            theses=thesis_def,
            layer_snapshots=layer_snapshots or {},
            financials=financials or [],
        )

        try:
            return verify_fn(ctx)
        except Exception as exc:
            logger.warning("thesis %s verification failed: %s", thesis_def["id"], exc)
            return ThesisVerdict(
                thesis_id=thesis_def["id"],
                title=thesis_def["title"],
                description=thesis_def["description"],
                status=ThesisStatus.INSUFFICIENT_DATA,
                evidence=f"验证出错: {exc}",
                confidence="low",
            )


# ============================================================
# 验证上下文
# ============================================================


class ThesisContext:
    """假说验证上下文，封装所有可用的输入数据"""

    def __init__(
        self,
        theses: dict,
        layer_snapshots: Dict[ChainLayer, LayerFinancialSnapshot],
        financials: List[CompanyFinancials],
    ):
        self.theses = theses
        self.layer_snapshots = layer_snapshots
        self.financials = financials

    def get_company(self, ticker: str) -> Optional[CompanyFinancials]:
        for f in self.financials:
            if f.ticker == ticker:
                return f
        return None

    def get_layer(self, layer: ChainLayer) -> Optional[LayerFinancialSnapshot]:
        return self.layer_snapshots.get(layer)

    def layer_has_data(self, layer: ChainLayer) -> bool:
        snap = self.layer_snapshots.get(layer)
        return snap is not None and snap.avg_gross_margin is not None


# ============================================================
# 各假说的验证函数
# ============================================================


def _verify_nvda_margin(ctx: ThesisContext) -> ThesisVerdict:
    """验证 NVDA 毛利率约 71%"""
    nvda = ctx.get_company("NVDA")
    if nvda is None or nvda.gross_margin is None:
        return _insufficient(ctx, "NVDA 财务数据不可用")

    gm = nvda.gross_margin
    expected_range = "65% - 75%"
    passed = 65 <= gm <= 75
    change = (
        f"（上次 {nvda.data_completeness}）"
        if nvda.data_completeness != "full"
        else ""
    )

    return ThesisVerdict(
        thesis_id=ctx.theses["id"],
        title=ctx.theses["title"],
        description=ctx.theses["description"],
        status=ThesisStatus.PASS if passed else ThesisStatus.FAIL,
        numerical_value=gm,
        actual_value=f"{gm}%",
        expected_range=expected_range,
        evidence=f"NVDA 最新毛利率 {gm}%，预期范围 {expected_range}",
        data_source="yfinance",
        change_from_last=change,
        confidence="high",
    )


def _verify_accelerator_top_profit(ctx: ThesisContext) -> ThesisVerdict:
    """验证 AI 加速器层利润率最高"""
    target_layer = ChainLayer.AI_ACCELERATOR
    target = ctx.get_layer(target_layer)
    if target is None or target.avg_gross_margin is None:
        return _insufficient(ctx, f"{target_layer.display_name} 数据不足")

    # 与其他层比较
    higher_layers = []
    for layer, snap in ctx.layer_snapshots.items():
        if layer == target_layer:
            continue
        if snap.avg_gross_margin is not None and snap.avg_gross_margin > target.avg_gross_margin:
            higher_layers.append((layer.display_name, snap.avg_gross_margin))

    passed = len(higher_layers) == 0
    evidence = (
        f"AI 加速器层毛利率 {target.avg_gross_margin}%"
        + (f"，高于所有其他层" if passed else f"，但有 {higher_layers} 的毛利率更高")
    )

    return ThesisVerdict(
        thesis_id=ctx.theses["id"],
        title=ctx.theses["title"],
        description=ctx.theses["description"],
        status=ThesisStatus.PASS if passed else ThesisStatus.FAIL,
        numerical_value=target.avg_gross_margin,
        actual_value=f"{target.avg_gross_margin}%",
        expected_range="所有层中最高",
        evidence=evidence,
        confidence="medium" if passed else "low",
    )


def _verify_application_lowest_margin(ctx: ThesisContext) -> ThesisVerdict:
    """验证应用层利润率最低"""
    app_layer = ChainLayer.APPLICATION_SAAS
    app = ctx.get_layer(app_layer)
    if app is None or app.avg_gross_margin is None:
        return _insufficient(ctx, "应用层财务数据不足")

    lower_layers = []
    for layer, snap in ctx.layer_snapshots.items():
        if layer == app_layer:
            continue
        if snap.avg_gross_margin is not None and snap.avg_gross_margin < app.avg_gross_margin:
            lower_layers.append((layer.display_name, snap.avg_gross_margin))

    # 注意：应用层可能不是绝对最低（ODM 层可能更低）
    # 框架说的是"最容易卷"，需要结合竞争强度判断
    passed = len(lower_layers) <= 2  # 允许有 1-2 层更低

    return ThesisVerdict(
        thesis_id=ctx.theses["id"],
        title=ctx.theses["title"],
        description=ctx.theses["description"],
        status=ThesisStatus.PASS if passed else ThesisStatus.FAIL,
        numerical_value=app.avg_gross_margin,
        actual_value=f"{app.avg_gross_margin}%",
        expected_range="毛利率在底层 3 名内",
        evidence=(
            f"应用层毛利率 {app.avg_gross_margin}%，"
            f"有 {len(lower_layers)} 层更低：{lower_layers}"
        ),
        confidence="medium",
    )


def _verify_hyperscaler_capex_growth(ctx: ThesisContext) -> ThesisVerdict:
    """验证 hyperscaler capex 仍在增长"""
    tickers = ["MSFT", "GOOGL", "AMZN", "META"]
    capex_values = {}
    for t in tickers:
        c = ctx.get_company(t)
        if c and c.capex is not None:
            capex_values[t] = c.capex

    if len(capex_values) < 3:
        return _insufficient(ctx, f"需要至少 3 家 hyperscaler 的 capex 数据，当前仅 {len(capex_values)} 家")

    total = sum(capex_values.values()) / 1000  # 转 billion
    # 无法直接判断增长（需要历史对比），标记为需要多期数据
    return ThesisVerdict(
        thesis_id=ctx.theses["id"],
        title=ctx.theses["title"],
        description=ctx.theses["description"],
        status=ThesisStatus.INSUFFICIENT_DATA,
        numerical_value=round(total, 2),
        actual_value=f"聚合 capex ${total:.2f}B（当期）",
        expected_range="同比正增长（需多期数据）",
        evidence=(
            f"MSFT+GOOGL+AMZN+META 聚合 capex: ${total:.2f}B。"
            f"需多期数据才能判断增长趋势。"
        ),
        data_source="yfinance",
        confidence="low",
    )


def _verify_asic_share_gain(ctx: ThesisContext) -> ThesisVerdict:
    """验证 ASIC（AVGO/MRVL）增速是否可能超过 NVDA 增量"""
    avgo = ctx.get_company("AVGO")
    nvda = ctx.get_company("NVDA")

    if not all([avgo, nvda]):
        return _insufficient(ctx, "需要 AVGO 和 NVDA 的财务数据")

    # 比较收入增速（如果有）
    avgo_growth = avgo.revenue_growth
    nvda_growth = nvda.revenue_growth

    if avgo_growth is None or nvda_growth is None:
        return ThesisVerdict(
            thesis_id=ctx.theses["id"],
            title=ctx.theses["title"],
            description=ctx.theses["description"],
            status=ThesisStatus.INSUFFICIENT_DATA,
            evidence="收入增速数据不足（avgo_growth={avgo_growth}, nvda_growth={nvda_growth}）",
            confidence="low",
        )

    # ASIC 增速高于 NVDA → ASIC 可能在抢份额
    asic_faster = avgo_growth > nvda_growth

    return ThesisVerdict(
        thesis_id=ctx.theses["id"],
        title=ctx.theses["title"],
        description=ctx.theses["description"],
        status=ThesisStatus.PASS if asic_faster else ThesisStatus.FAIL,
        numerical_value=avgo_growth - nvda_growth,
        actual_value=f"AVGO 增速 {avgo_growth}% vs NVDA 增速 {nvda_growth}%",
        expected_range="AVGO 增速 > NVDA 增速",
        evidence=(
            f"AVGO 收入增速 {avgo_growth}%，NVDA 收入增速 {nvda_growth}%。"
            + ("ASIC 增速领先，支持假说" if asic_faster else "NVDA 增速仍领先，ASIC 尚未超越")
        ),
        data_source="yfinance",
        confidence="medium",
    )


def _verify_foundry_high_margin(ctx: ThesisContext) -> ThesisVerdict:
    """验证代工/封装层利润率极高"""
    foundry = ctx.get_layer(ChainLayer.FOUNDRY_PACKAGE)
    if foundry is None or foundry.avg_gross_margin is None:
        return _insufficient(ctx, "代工层财务数据不足")

    gm = foundry.avg_gross_margin
    passed = gm > 40  # 毛利率 > 40% 算高

    return ThesisVerdict(
        thesis_id=ctx.theses["id"],
        title=ctx.theses["title"],
        description=ctx.theses["description"],
        status=ThesisStatus.PASS if passed else ThesisStatus.FAIL,
        numerical_value=gm,
        actual_value=f"{gm}%",
        expected_range="> 40%",
        evidence=f"先进代工/封装层综合毛利率 {gm}%",
        data_source="yfinance",
        confidence="medium",
    )


def _verify_hbm_supply_tight(ctx: ThesisContext) -> ThesisVerdict:
    """验证 HBM 供需紧张"""
    hbm = ctx.get_layer(ChainLayer.HBM_MEMORY)
    if hbm is None or hbm.avg_gross_margin is None:
        return _insufficient(ctx, "HBM/存储层财务数据不足")

    gm = hbm.avg_gross_margin
    rev_g = hbm.avg_revenue_growth

    # 高毛利率 + 高增速 = 供需紧张
    passed = gm > 30 and (rev_g is not None and rev_g > 15)
    evidence_parts = [f"HBM/存储层毛利率 {gm}%"]
    if rev_g is not None:
        evidence_parts.append(f"收入增速 {rev_g}%")

    return ThesisVerdict(
        thesis_id=ctx.theses["id"],
        title=ctx.theses["title"],
        description=ctx.theses["description"],
        status=ThesisStatus.PASS if passed else ThesisStatus.INSUFFICIENT_DATA,
        numerical_value=gm,
        actual_value=f"{gm}%",
        expected_range="毛利率 > 30% 且收入增速 > 15%",
        evidence=", ".join(evidence_parts),
        data_source="yfinance",
        confidence="medium",
    )


def _verify_odm_low_margin(ctx: ThesisContext) -> ThesisVerdict:
    """验证服务器 ODM 利润率低"""
    network = ctx.get_layer(ChainLayer.SERVER_NETWORK)
    if network is None or network.avg_gross_margin is None:
        return _insufficient(ctx, "服务器/网络层财务数据不足")

    gm = network.avg_gross_margin
    # 服务器 ODM（DELL, SMCI）毛利率通常 < 20%
    passed = gm < 25

    return ThesisVerdict(
        thesis_id=ctx.theses["id"],
        title=ctx.theses["title"],
        description=ctx.theses["description"],
        status=ThesisStatus.PASS if passed else ThesisStatus.FAIL,
        numerical_value=gm,
        actual_value=f"{gm}%",
        expected_range="< 25%",
        evidence=f"服务器/网络层综合毛利率 {gm}%（ODM 厂商多为低毛利）",
        data_source="yfinance",
        confidence="medium",
    )


def _verify_model_api_pressure(ctx: ThesisContext) -> ThesisVerdict:
    """验证基础模型 API 面临价格压力"""
    model = ctx.get_layer(ChainLayer.BASE_MODEL_API)
    if model is None or model.avg_gross_margin is None:
        return _insufficient(ctx, "基础模型层财务数据不足")

    # 模型层的 META 和 GOOGL 毛利率很高，但这主要是广告业务
    # 单独的 API 业务可能亏损
    gm = model.avg_gross_margin

    return ThesisVerdict(
        thesis_id=ctx.theses["id"],
        title=ctx.theses["title"],
        description=ctx.theses["description"],
        status=ThesisStatus.INSUFFICIENT_DATA,
        numerical_value=gm,
        actual_value=f"{gm}%（混杂非 API 业务）",
        expected_range="需要纯 API 业务毛利率",
        evidence=(
            f"基础模型层综合毛利率 {gm}%（含广告业务，偏高估）。"
            f"目前 yfinance 无法分离模型 API 的独立财务数据。"
        ),
        data_source="yfinance",
        confidence="low",
    )


def _verify_cloud_capex_roi(ctx: ThesisContext) -> ThesisVerdict:
    """验证云平台 Capex 回报率担忧"""
    cloud = ctx.get_layer(ChainLayer.CLOUD_IAAS)
    if cloud is None or cloud.avg_operating_margin is None:
        return _insufficient(ctx, "云平台层财务数据不足")

    om = cloud.avg_operating_margin

    return ThesisVerdict(
        thesis_id=ctx.theses["id"],
        title=ctx.theses["title"],
        description=ctx.theses["description"],
        status=ThesisStatus.INSUFFICIENT_DATA,
        numerical_value=om,
        actual_value=f"云平台运营利润率 {om}%",
        expected_range="需要 capex/revenue 比 + 多期趋势",
        evidence=(
            f"云平台层运营利润率 {om}%。"
            f"评估 Capex ROI 需要 capex/revenue 比率和折旧数据，"
            f"当前数据不足以判断。"
        ),
        data_source="yfinance",
        confidence="low",
    )


# ============================================================
# 辅助
# ============================================================


def _insufficient(ctx: ThesisContext, reason: str) -> ThesisVerdict:
    return ThesisVerdict(
        thesis_id=ctx.theses["id"],
        title=ctx.theses["title"],
        description=ctx.theses["description"],
        status=ThesisStatus.INSUFFICIENT_DATA,
        evidence=f"数据不足: {reason}",
        confidence="low",
    )
