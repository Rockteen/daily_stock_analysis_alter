# -*- coding: utf-8 -*-
"""
AI 产业链核心数据模型

定义链层枚举、公司、财务快照、评分、关键变量和假说验证的数据结构。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any, Dict, List, Optional


class ChainLayer(Enum):
    """AI 产业链 8 层结构"""

    SEMI_EQUIPMENT = "semiconductor_equipment"
    FOUNDRY_PACKAGE = "foundry_and_advanced_packaging"
    AI_ACCELERATOR = "ai_accelerator"
    HBM_MEMORY = "hbm_memory_and_storage"
    SERVER_NETWORK = "server_network_cooling_power"
    CLOUD_IAAS = "cloud_platform_and_iaas"
    BASE_MODEL_API = "foundation_model_and_api"
    APPLICATION_SAAS = "application_agent_and_saas"

    @property
    def display_name(self) -> str:
        return _LAYER_DISPLAY_NAMES[self]

    @property
    def sort_order(self) -> int:
        return _LAYER_SORT_ORDERS[self]


_LAYER_DISPLAY_NAMES = {
    ChainLayer.SEMI_EQUIPMENT: "半导体设备与材料",
    ChainLayer.FOUNDRY_PACKAGE: "晶圆代工与先进封装",
    ChainLayer.AI_ACCELERATOR: "AI 芯片与加速器",
    ChainLayer.HBM_MEMORY: "HBM、内存与存储",
    ChainLayer.SERVER_NETWORK: "服务器、网络、液冷与电力",
    ChainLayer.CLOUD_IAAS: "云平台与 IaaS",
    ChainLayer.BASE_MODEL_API: "基础模型与 API",
    ChainLayer.APPLICATION_SAAS: "应用层、Agent 与 SaaS",
}

_LAYER_SORT_ORDERS = {
    ChainLayer.SEMI_EQUIPMENT: 1,
    ChainLayer.FOUNDRY_PACKAGE: 2,
    ChainLayer.AI_ACCELERATOR: 3,
    ChainLayer.HBM_MEMORY: 4,
    ChainLayer.SERVER_NETWORK: 5,
    ChainLayer.CLOUD_IAAS: 6,
    ChainLayer.BASE_MODEL_API: 7,
    ChainLayer.APPLICATION_SAAS: 8,
}


class Region(Enum):
    """公司所属区域"""
    US = "us"
    CN = "cn"
    KR = "kr"
    TW = "tw"
    EU = "eu"
    JP = "jp"
    NL = "nl"


_REGION_DISPLAY = {
    Region.US: "美国",
    Region.CN: "中国",
    Region.KR: "韩国",
    Region.TW: "中国台湾",
    Region.EU: "欧洲",
    Region.JP: "日本",
    Region.NL: "荷兰",
}


def region_display(r: Region) -> str:
    return _REGION_DISPLAY.get(r, r.value)


# ============================================================
# 公司与财务模型
# ============================================================


@dataclass
class ChainCompany:
    """产业链中的一个公司"""

    code: str                           # 内部唯一代码
    name: str                           # 中文名
    name_en: str                        # 英文名
    layer: ChainLayer                   # 所属链层
    region: Region                      # 区域
    ticker_yf: str                      # yfinance ticker
    ticker_cn: Optional[str] = None     # A 股代码（如有）
    is_core_player: bool = True         # 是否核心玩家
    description: str = ""               # 在该层的角色描述
    notes: str = ""                     # 其他备注（竞争地位、催化剂等）


@dataclass
class CompanyFinancials:
    """单个公司的财务数据快照"""

    ticker: str
    name: str
    layer: ChainLayer
    trade_date: Optional[date] = None

    # 利润表
    revenue: Optional[float] = None             # 总收入（最新财年，百万 USD）
    revenue_growth: Optional[float] = None      # 收入同比增速（%）
    gross_margin: Optional[float] = None        # 毛利率（%）
    operating_margin: Optional[float] = None    # 运营利润率（%）
    net_margin: Optional[float] = None          # 净利率（%）

    # 资产负债表 / 现金流
    capex: Optional[float] = None               # 资本开支（百万 USD）
    free_cash_flow: Optional[float] = None      # 自由现金流（百万 USD）
    market_cap: Optional[float] = None          # 市值（百万 USD）
    enterprise_value: Optional[float] = None    # 企业价值（百万 USD）

    # 估值
    pe_ratio: Optional[float] = None            # 市盈率
    ps_ratio: Optional[float] = None            # 市销率
    pb_ratio: Optional[float] = None            # 市净率

    # 元数据
    data_completeness: str = "partial"          # full / partial / minimal
    errors: List[str] = field(default_factory=list)


# ============================================================
# 层聚合与评分模型
# ============================================================


@dataclass
class LayerFinancialSnapshot:
    """单层的财务聚合快照"""

    layer: ChainLayer
    company_count: int = 0
    core_player_count: int = 0

    # 聚合指标（均值）
    avg_gross_margin: Optional[float] = None
    avg_operating_margin: Optional[float] = None
    avg_net_margin: Optional[float] = None
    avg_revenue_growth: Optional[float] = None
    avg_pe_ratio: Optional[float] = None
    avg_ps_ratio: Optional[float] = None

    # 中位数指标
    median_gross_margin: Optional[float] = None
    median_revenue_growth: Optional[float] = None

    # 市场规模
    total_market_cap: Optional[float] = None
    total_revenue: Optional[float] = None
    total_capex: Optional[float] = None

    # 结构
    herfindahl_index: Optional[float] = None       # HHI 集中度（基于收入）
    margin_std: Optional[float] = None             # 毛利率标准差

    # 各公司详细数据
    company_details: List[CompanyFinancials] = field(default_factory=list)


class ScoreDimension(Enum):
    """评分维度"""
    PROFITABILITY = "profitability"          # 利润率维度
    MOAT = "competitive_moat"                # 竞争壁垒
    BOTTLENECK = "bottleneck"                # 供给瓶颈度
    GROWTH = "growth_momentum"               # 增长动能
    VALUATION = "valuation_pressure"         # 估值压力


_SCORE_DIMENSION_DISPLAY = {
    ScoreDimension.PROFITABILITY: "利润率",
    ScoreDimension.MOAT: "竞争壁垒",
    ScoreDimension.BOTTLENECK: "供给瓶颈度",
    ScoreDimension.GROWTH: "增长动能",
    ScoreDimension.VALUATION: "估值压力",
}


def score_dimension_display(d: ScoreDimension) -> str:
    return _SCORE_DIMENSION_DISPLAY.get(d, d.value)


@dataclass
class LayerScore:
    """单层的一个评分维度结果"""

    dimension: ScoreDimension
    score: float                       # 0-100
    weight: float = 1.0                # 综合评分中的权重
    explanation: str = ""              # 评分理由
    rank: Optional[int] = None         # 在该维度上的排名


@dataclass
class LayerScoreCard:
    """单层的完整评分卡"""

    layer: ChainLayer
    dimension_scores: List[LayerScore] = field(default_factory=list)
    composite_score: float = 0.0       # 加权综合得分
    composite_rank: Optional[int] = None
    profit_capture_rank: Optional[int] = None
    competitive_intensity: str = ""    # 高/中高/中/低
    summary: str = ""


# ============================================================
# 关键变量模型
# ============================================================


class VariableSource(Enum):
    """关键变量数据来源"""
    AUTO_FINANCIAL = "auto_financial"          # 从财报自动获取
    AUTO_MARKET = "auto_market"                # 从行情数据自动获取
    MANUAL = "manual"                          # 需要手动更新
    DERIVED = "derived"                        # 由其他数据计算得出


@dataclass
class KeyVariable:
    """一个关键监控变量"""

    name: str
    display_name: str
    category: str                              # capex / supply / demand / pricing / policy
    source: VariableSource
    unit: str = ""                             # billion USD / % / weeks
    current_value: Optional[float] = None
    previous_value: Optional[float] = None
    previous_date: Optional[date] = None
    change_pct: Optional[float] = None
    trend: str = "stable"                      # up / down / stable
    signal: str = "neutral"                    # bullish / bearish / neutral
    is_automated: bool = False                 # 是否可自动更新
    data_source_desc: str = ""                 # 数据来源描述
    notes: str = ""


@dataclass
class VariableSnapshot:
    """所有关键变量的快照"""

    variables: List[KeyVariable] = field(default_factory=list)
    snapshot_date: date = field(default_factory=date.today)

    def get_by_category(self, cat: str) -> List[KeyVariable]:
        return [v for v in self.variables if v.category == cat]

    def get_signal_summary(self) -> Dict[str, int]:
        counts: Dict[str, int] = {"bullish": 0, "bearish": 0, "neutral": 0}
        for v in self.variables:
            s = v.signal if v.signal in counts else "neutral"
            counts[s] += 1
        return counts


# ============================================================
# 假说验证模型
# ============================================================


class ThesisStatus(Enum):
    """假说验证状态"""
    PASS = "pass"
    FAIL = "fail"
    INSUFFICIENT_DATA = "insufficient_data"
    NOT_TESTED = "not_tested"


@dataclass
class ThesisVerdict:
    """一条框架假说的验证结果"""

    thesis_id: str
    title: str
    description: str
    status: ThesisStatus
    evidence: str = ""                         # 数值证据描述
    numerical_value: Optional[float] = None    # 核心数值
    expected_range: str = ""                   # 预期范围（如 "> 65%"）
    actual_value: str = ""                     # 实际值（如 "71.3%"）
    data_source: str = ""
    change_from_last: Optional[str] = None     # 环比变化
    confidence: str = "medium"                 # high / medium / low


@dataclass
class ThesisValidationReport:
    """假说验证报告"""

    theses: List[ThesisVerdict] = field(default_factory=list)
    validation_date: date = field(default_factory=date.today)
    pass_count: int = 0
    fail_count: int = 0
    insufficient_count: int = 0

    def compute_summary(self) -> None:
        self.pass_count = sum(1 for t in self.theses if t.status == ThesisStatus.PASS)
        self.fail_count = sum(1 for t in self.theses if t.status == ThesisStatus.FAIL)
        self.insufficient_count = sum(
            1 for t in self.theses if t.status == ThesisStatus.INSUFFICIENT_DATA
        )


# ============================================================
# 投资信号
# ============================================================


class LayerAllocation(Enum):
    """层级别配置建议"""
    OVERWEIGHT = "overweight"
    NEUTRAL = "neutral"
    UNDERWEIGHT = "underweight"


class CompanySignal(Enum):
    """公司级别信号"""
    STRONG_BUY = "strong_buy"
    BUY = "buy"
    HOLD = "hold"
    SELL = "sell"
    STRONG_SELL = "strong_sell"
    NOT_COVERED = "not_covered"


@dataclass
class AllocationSignal:
    """一条配置信号"""

    layer: ChainLayer
    allocation: LayerAllocation
    confidence: float = 0.5                    # 0-1
    reasoning: str = ""


@dataclass
class CompanyRecommendation:
    """一条公司推荐"""

    ticker: str
    name: str
    layer: ChainLayer
    signal: CompanySignal
    target_price: Optional[float] = None
    reasoning: str = ""
    confidence: float = 0.5


@dataclass
class SignalOutput:
    """完整信号输出"""

    layer_allocations: List[AllocationSignal] = field(default_factory=list)
    company_recommendations: List[CompanyRecommendation] = field(default_factory=list)
    key_alerts: List[str] = field(default_factory=list)
    generated_date: date = field(default_factory=date.today)


# ============================================================
# 全量扫描结果
# ============================================================


@dataclass
class ChainScanResult:
    """一次完整产业链扫描的输出"""

    scan_date: date = field(default_factory=date.today)
    status: str = "success"                    # success / partial / failed

    # 各子模块输出
    financials: Optional[LayerFinancialSnapshot] = None
    score_cards: List[LayerScoreCard] = field(default_factory=list)
    thesis_report: Optional[ThesisValidationReport] = None
    variables: Optional[VariableSnapshot] = None
    signals: Optional[SignalOutput] = None

    # 元数据
    company_count: int = 0
    companies_with_data: int = 0
    errors: List[str] = field(default_factory=list)
    duration_seconds: Optional[float] = None
