# -*- coding: utf-8 -*-
"""
AI 产业链公司注册表

按照框架的 8 层结构，每层列出全球核心玩家和中国相关玩家，
覆盖研究框架表格中的所有公司。

查询方法:
  - get_all_companies() -> List[ChainCompany]
  - get_companies_by_layer(layer) -> List[ChainCompany]
  - get_company(ticker) -> ChainCompany
  - get_core_players(layer) -> List[ChainCompany]
  - get_layers() -> List[ChainLayer]
"""

from __future__ import annotations

from typing import Dict, List, Optional

from src.industry_chain.models import ChainCompany, ChainLayer, Region


# ============================================================
# 1. 半导体设备与材料
# ============================================================

_SEMI_EQUIPMENT = [
    ChainCompany(
        code="ASML", name="阿斯麦", name_en="ASML Holding",
        layer=ChainLayer.SEMI_EQUIPMENT, region=Region.NL,
        ticker_yf="ASML",
        description="EUV 光刻机垄断供应商，先进制程必备",
        notes="5nm 以下制程唯一供应商，EUV 产能决定了整个产业链的制造瓶颈",
    ),
    ChainCompany(
        code="AMAT", name="应用材料", name_en="Applied Materials",
        layer=ChainLayer.SEMI_EQUIPMENT, region=Region.US,
        ticker_yf="AMAT",
        description="半导体沉积、刻蚀、离子注入设备龙头",
    ),
    ChainCompany(
        code="LRCX", name="泛林半导体", name_en="Lam Research",
        layer=ChainLayer.SEMI_EQUIPMENT, region=Region.US,
        ticker_yf="LRCX",
        description="刻蚀与薄膜沉积设备龙头",
    ),
    ChainCompany(
        code="KLAC", name="科磊", name_en="KLA Corporation",
        layer=ChainLayer.SEMI_EQUIPMENT, region=Region.US,
        ticker_yf="KLAC",
        description="半导体量测与检测设备龙头",
    ),
    ChainCompany(
        code="SNPS", name="新思科技", name_en="Synopsys",
        layer=ChainLayer.SEMI_EQUIPMENT, region=Region.US,
        ticker_yf="SNPS",
        description="EDA 软件龙头，芯片设计必备工具",
    ),
    ChainCompany(
        code="CDNS", name="Cadence", name_en="Cadence Design Systems",
        layer=ChainLayer.SEMI_EQUIPMENT, region=Region.US,
        ticker_yf="CDNS",
        description="EDA 软件第二大供应商",
    ),
    ChainCompany(
        code="TEL", name="东京电子", name_en="Tokyo Electron",
        layer=ChainLayer.SEMI_EQUIPMENT, region=Region.JP,
        ticker_yf="TEL",
        description="日本半导体设备龙头，涂布显影/刻蚀/沉积",
        notes="TYO:8035, yfinance 可能需要确认 ticker",
        is_core_player=False,
    ),
    # 中国相关
    ChainCompany(
        code="002371", name="北方华创", name_en="NAURA Technology",
        layer=ChainLayer.SEMI_EQUIPMENT, region=Region.CN,
        ticker_yf="002371.SZ",
        ticker_cn="002371",
        description="中国半导体设备综合龙头，刻蚀/薄膜/清洗/炉管",
        is_core_player=False,
    ),
    ChainCompany(
        code="688012", name="中微公司", name_en="AMEC",
        layer=ChainLayer.SEMI_EQUIPMENT, region=Region.CN,
        ticker_yf="688012.SS",
        ticker_cn="688012",
        description="中国刻蚀/MOCVD 设备龙头",
        is_core_player=False,
    ),
    ChainCompany(
        code="301269", name="华大九天", name_en="Empyrean Technology",
        layer=ChainLayer.SEMI_EQUIPMENT, region=Region.CN,
        ticker_yf="301269.SZ",
        ticker_cn="301269",
        description="国产 EDA 龙头",
        is_core_player=False,
    ),
]

# ============================================================
# 2. 晶圆代工与先进封装
# ============================================================

_FOUNDRY = [
    ChainCompany(
        code="TSM", name="台积电", name_en="TSMC",
        layer=ChainLayer.FOUNDRY_PACKAGE, region=Region.TW,
        ticker_yf="TSM",
        description="全球最先进制程代工厂，N3/N2 及 CoWoS 封装",
        notes="CoWoS 产能是 AI 芯片供给的物理瓶颈之一",
    ),
    ChainCompany(
        code="INTC", name="英特尔", name_en="Intel",
        layer=ChainLayer.FOUNDRY_PACKAGE, region=Region.US,
        ticker_yf="INTC",
        description="IDM+代工转型中，Intel Foundry 目标先进制程",
        is_core_player=False,
    ),
    # 中国相关
    ChainCompany(
        code="0981.HK", name="中芯国际", name_en="SMIC",
        layer=ChainLayer.FOUNDRY_PACKAGE, region=Region.CN,
        ticker_yf="0981.HK",
        description="中国大陆最大晶圆代工厂，N+2 制程追赶中",
        is_core_player=False,
    ),
    ChainCompany(
        code="600584", name="长电科技", name_en="JCET Group",
        layer=ChainLayer.FOUNDRY_PACKAGE, region=Region.CN,
        ticker_yf="600584.SS",
        ticker_cn="600584",
        description="中国先进封装龙头",
        is_core_player=False,
    ),
    ChainCompany(
        code="002156", name="通富微电", name_en="TongFu Microelectronics",
        layer=ChainLayer.FOUNDRY_PACKAGE, region=Region.CN,
        ticker_yf="002156.SZ",
        ticker_cn="002156",
        description="先进封装与 AMD 深度绑定",
        is_core_player=False,
    ),
]

# ============================================================
# 3. AI 芯片与加速器
# ============================================================

_AI_ACCELERATOR = [
    ChainCompany(
        code="NVDA", name="英伟达", name_en="NVIDIA",
        layer=ChainLayer.AI_ACCELERATOR, region=Region.US,
        ticker_yf="NVDA",
        description="AI GPU 绝对龙头，CUDA 生态壁垒，软硬一体平台",
        notes="FY2026 毛利率 ~71%，当前产业链最大利润池",
    ),
    ChainCompany(
        code="AMD", name="超微半导体", name_en="Advanced Micro Devices",
        layer=ChainLayer.AI_ACCELERATOR, region=Region.US,
        ticker_yf="AMD",
        description="MI 系列 AI GPU，Instinct 加速器追赶者",
    ),
    ChainCompany(
        code="AVGO", name="博通", name_en="Broadcom",
        layer=ChainLayer.AI_ACCELERATOR, region=Region.US,
        ticker_yf="AVGO",
        description="定制 AI ASIC（Google TPU 等）及网络芯片龙头",
        notes="FY2025 AI 半导体收入同比增长 74%，ASIC 份额持续扩大",
    ),
    ChainCompany(
        code="MRVL", name="美满电子", name_en="Marvell Technology",
        layer=ChainLayer.AI_ACCELERATOR, region=Region.US,
        ticker_yf="MRVL",
        description="定制 ASIC（Amazon Trainium2 等）及数据中心连接",
        is_core_player=False,
    ),
    # 中国相关
    ChainCompany(
        code="002049", name="紫光国微", name_en="Unigroup Guoxin",
        layer=ChainLayer.AI_ACCELERATOR, region=Region.CN,
        ticker_yf="002049.SZ",
        ticker_cn="002049",
        description="国产 FPGA / 特种芯片",
        is_core_player=False,
    ),
]

# ============================================================
# 4. HBM、内存与存储
# ============================================================

_HBM_MEMORY = [
    ChainCompany(
        code="000660.KS", name="SK 海力士", name_en="SK Hynix",
        layer=ChainLayer.HBM_MEMORY, region=Region.KR,
        ticker_yf="000660.KS",
        description="HBM 龙头，HBM3E 率先大规模量产",
        notes="AI 显存瓶颈的直接受益者，HBM 收入占比持续提升",
    ),
    ChainCompany(
        code="SSNLF", name="三星电子", name_en="Samsung Electronics",
        layer=ChainLayer.HBM_MEMORY, region=Region.KR,
        ticker_yf="SSNLF",
        description="HBM 第二大供应商，存储与代工综合龙头",
    ),
    ChainCompany(
        code="MU", name="美光科技", name_en="Micron Technology",
        layer=ChainLayer.HBM_MEMORY, region=Region.US,
        ticker_yf="MU",
        description="HBM 第三极，HBM3E 追赶中",
    ),
    ChainCompany(
        code="WDC", name="西部数据", name_en="Western Digital",
        layer=ChainLayer.HBM_MEMORY, region=Region.US,
        ticker_yf="WDC",
        description="NAND 闪存与 HDD 龙头",
        is_core_player=False,
    ),
    # 中国相关
    ChainCompany(
        code="688981", name="中芯集成", name_en="NXPI? earmark",
        layer=ChainLayer.HBM_MEMORY, region=Region.CN,
        ticker_yf="",
        description="HBM 国产替代尚未上市，此为预留位",
        is_core_player=False,
    ),
]

# ============================================================
# 5. 服务器、网络、液冷与电力
# ============================================================

_SERVER_NETWORK = [
    ChainCompany(
        code="DELL", name="戴尔", name_en="Dell Technologies",
        layer=ChainLayer.SERVER_NETWORK, region=Region.US,
        ticker_yf="DELL",
        description="AI 服务器（PowerEdge 系列）头部厂商",
    ),
    ChainCompany(
        code="SMCI", name="超微电脑", name_en="Super Micro Computer",
        layer=ChainLayer.SERVER_NETWORK, region=Region.US,
        ticker_yf="SMCI",
        description="AI 服务器与液冷方案领先者",
    ),
    ChainCompany(
        code="ANET", name="Arista Networks", name_en="Arista Networks",
        layer=ChainLayer.SERVER_NETWORK, region=Region.US,
        ticker_yf="ANET",
        description="数据中心高速交换机龙头",
    ),
    ChainCompany(
        code="CSCO", name="思科", name_en="Cisco Systems",
        layer=ChainLayer.SERVER_NETWORK, region=Region.US,
        ticker_yf="CSCO",
        description="传统网络设备巨头，AI 网络转型中",
        is_core_player=False,
    ),
    ChainCompany(
        code="VRT", name="Vertiv", name_en="Vertiv Holdings",
        layer=ChainLayer.SERVER_NETWORK, region=Region.US,
        ticker_yf="VRT",
        description="数据中心电力与热管理龙头",
    ),
    ChainCompany(
        code="ETN", name="伊顿", name_en="Eaton Corporation",
        layer=ChainLayer.SERVER_NETWORK, region=Region.US,
        ticker_yf="ETN",
        description="电气与数据中心电力管理",
        is_core_player=False,
    ),
    # 中国相关
    ChainCompany(
        code="601138", name="工业富联", name_en="Foxconn Industrial Internet",
        layer=ChainLayer.SERVER_NETWORK, region=Region.CN,
        ticker_yf="601138.SS",
        ticker_cn="601138",
        description="AI 服务器 ODM 龙头，Nvidia 合作紧密",
    ),
    ChainCompany(
        code="000977", name="浪潮信息", name_en="Inspur",
        layer=ChainLayer.SERVER_NETWORK, region=Region.CN,
        ticker_yf="000977.SZ",
        ticker_cn="000977",
        description="中国 AI 服务器龙头",
    ),
    ChainCompany(
        code="300308", name="中际旭创", name_en="Zhongji Innolight",
        layer=ChainLayer.SERVER_NETWORK, region=Region.CN,
        ticker_yf="300308.SZ",
        ticker_cn="300308",
        description="800G/1.6T 光模块龙头",
    ),
    ChainCompany(
        code="300502", name="新易盛", name_en="Eoptolink",
        layer=ChainLayer.SERVER_NETWORK, region=Region.CN,
        ticker_yf="300502.SZ",
        ticker_cn="300502",
        description="高速光模块领先供应商",
        is_core_player=False,
    ),
    ChainCompany(
        code="002837", name="英维克", name_en="Envicool",
        layer=ChainLayer.SERVER_NETWORK, region=Region.CN,
        ticker_yf="002837.SZ",
        ticker_cn="002837",
        description="液冷与热管理龙头",
        is_core_player=False,
    ),
]

# ============================================================
# 6. 云平台与 IaaS
# ============================================================

_CLOUD_IAAS = [
    ChainCompany(
        code="AMZN", name="亚马逊", name_en="Amazon.com",
        layer=ChainLayer.CLOUD_IAAS, region=Region.US,
        ticker_yf="AMZN",
        description="AWS 全球云服务份额第一，Trainium 自研芯片",
    ),
    ChainCompany(
        code="MSFT", name="微软", name_en="Microsoft",
        layer=ChainLayer.CLOUD_IAAS, region=Region.US,
        ticker_yf="MSFT",
        description="Azure 云服务 + OpenAI 深度合作，AI Copilot 生态",
        notes="FY2025 capex ~646 亿美元，最大云资本开支之一",
    ),
    ChainCompany(
        code="GOOGL", name="谷歌", name_en="Alphabet (Google)",
        layer=ChainLayer.CLOUD_IAAS, region=Region.US,
        ticker_yf="GOOGL",
        description="GCP + TPU 自研芯片 + Gemini 模型，AI 全栈布局",
    ),
    ChainCompany(
        code="ORCL", name="甲骨文", name_en="Oracle",
        layer=ChainLayer.CLOUD_IAAS, region=Region.US,
        ticker_yf="ORCL",
        description="OCI 云服务，AI 推理与数据库云化受益者",
        is_core_player=False,
    ),
    # 中国相关
    ChainCompany(
        code="9988.HK", name="阿里巴巴", name_en="Alibaba Group",
        layer=ChainLayer.CLOUD_IAAS, region=Region.CN,
        ticker_yf="9988.HK",
        description="阿里云 + 通义千问模型，中国云市场龙头",
    ),
    ChainCompany(
        code="0700.HK", name="腾讯", name_en="Tencent Holdings",
        layer=ChainLayer.CLOUD_IAAS, region=Region.CN,
        ticker_yf="0700.HK",
        description="腾讯云 + 混元大模型",
    ),
    ChainCompany(
        code="BIDU", name="百度", name_en="Baidu",
        layer=ChainLayer.CLOUD_IAAS, region=Region.CN,
        ticker_yf="BIDU",
        description="百度智能云 + 文心一言，AI 云布局",
        is_core_player=False,
    ),
]

# ============================================================
# 7. 基础模型与 API
# ============================================================

_BASE_MODEL = [
    # OpenAI 非上市公司，无公开 ticker，通过 MSFT 间接投
    ChainCompany(
        code="META", name="Meta", name_en="Meta Platforms",
        layer=ChainLayer.BASE_MODEL_API, region=Region.US,
        ticker_yf="META",
        description="Llama 开源模型系列，开源生态领导者",
        notes="2025 capex $722 亿，最大 AI 基建投入者之一",
    ),
    ChainCompany(
        code="MSFT", name="微软 (OpenAI)", name_en="Microsoft (OpenAI)",
        layer=ChainLayer.BASE_MODEL_API, region=Region.US,
        ticker_yf="MSFT",
        description="OpenAI 独家云伙伴，GPT 系列模型商业化",
        notes="通过 Azure 分发 OpenAI API，与 Cloud IaaS 层同公司",
    ),
    ChainCompany(
        code="GOOGL", name="谷歌 DeepMind", name_en="Google DeepMind",
        layer=ChainLayer.BASE_MODEL_API, region=Region.US,
        ticker_yf="GOOGL",
        description="Gemini 系列模型，从头训练 + 全栈布局",
        notes="与 Cloud IaaS 层同公司",
    ),
    # 中国相关
    ChainCompany(
        code="9988.HK", name="阿里通义", name_en="Alibaba Tongyi",
        layer=ChainLayer.BASE_MODEL_API, region=Region.CN,
        ticker_yf="9988.HK",
        description="通义千问大模型系列，开源 Qwen",
        is_core_player=False,
    ),
    ChainCompany(
        code="0700.HK", name="腾讯混元", name_en="Tencent Hunyuan",
        layer=ChainLayer.BASE_MODEL_API, region=Region.CN,
        ticker_yf="0700.HK",
        description="混元大模型",
        is_core_player=False,
    ),
]

# ============================================================
# 8. 应用层、Agent 与 SaaS
# ============================================================

_APPLICATION_SAAS = [
    ChainCompany(
        code="ADBE", name="Adobe", name_en="Adobe Inc.",
        layer=ChainLayer.APPLICATION_SAAS, region=Region.US,
        ticker_yf="ADBE",
        description="Firefly AI 创意工具，SaaS 订阅模式成熟",
    ),
    ChainCompany(
        code="CRM", name="Salesforce", name_en="Salesforce",
        layer=ChainLayer.APPLICATION_SAAS, region=Region.US,
        ticker_yf="CRM",
        description="Agentforce AI Agent 平台，CRM SaaS 龙头",
    ),
    ChainCompany(
        code="NOW", name="ServiceNow", name_en="ServiceNow",
        layer=ChainLayer.APPLICATION_SAAS, region=Region.US,
        ticker_yf="NOW",
        description="ITSM 平台 + AI Agent 工作流",
    ),
    ChainCompany(
        code="PLTR", name="Palantir", name_en="Palantir Technologies",
        layer=ChainLayer.APPLICATION_SAAS, region=Region.US,
        ticker_yf="PLTR",
        description="AIP 平台将 LLM 集成到企业决策工作流",
    ),
    ChainCompany(
        code="SNOW", name="Snowflake", name_en="Snowflake Inc.",
        layer=ChainLayer.APPLICATION_SAAS, region=Region.US,
        ticker_yf="SNOW",
        description="AI 数据云平台 + Cortex AI 推理",
    ),
    ChainCompany(
        code="DDOG", name="Datadog", name_en="Datadog Inc.",
        layer=ChainLayer.APPLICATION_SAAS, region=Region.US,
        ticker_yf="DDOG",
        description="可观测性平台 + AI 运维 Agent",
        is_core_player=False,
    ),
    ChainCompany(
        code="HUBS", name="HubSpot", name_en="HubSpot Inc.",
        layer=ChainLayer.APPLICATION_SAAS, region=Region.US,
        ticker_yf="HUBS",
        description="CRM/营销 SaaS + AI 内容工具",
        is_core_player=False,
    ),
    # 中国相关
    ChainCompany(
        code="688111", name="金山办公", name_en="Kingsoft Office",
        layer=ChainLayer.APPLICATION_SAAS, region=Region.CN,
        ticker_yf="688111.SS",
        ticker_cn="688111",
        description="WPS + AI 办公 Copilot",
    ),
    ChainCompany(
        code="002230", name="科大讯飞", name_en="iFlytek",
        layer=ChainLayer.APPLICATION_SAAS, region=Region.CN,
        ticker_yf="002230.SZ",
        ticker_cn="002230",
        description="星火大模型 + AI 语音/教育/医疗应用",
    ),
    ChainCompany(
        code="300033", name="同花顺", name_en="Flush",
        layer=ChainLayer.APPLICATION_SAAS, region=Region.CN,
        ticker_yf="300033.SZ",
        ticker_cn="300033",
        description="AI 金融信息服务 + 投研助手",
        is_core_player=False,
    ),
    ChainCompany(
        code="300418", name="昆仑万维", name_en="Kunlun Tech",
        layer=ChainLayer.APPLICATION_SAAS, region=Region.CN,
        ticker_yf="300418.SZ",
        ticker_cn="300418",
        description="天工大模型 + AI 社交/搜索应用",
        is_core_player=False,
    ),
]

# ============================================================
# 注册表构建
# ============================================================

# 完整列表
_ALL_COMPANIES: list = (
    _SEMI_EQUIPMENT
    + _FOUNDRY
    + _AI_ACCELERATOR
    + _HBM_MEMORY
    + _SERVER_NETWORK
    + _CLOUD_IAAS
    + _BASE_MODEL
    + _APPLICATION_SAAS
)

# 索引
_BY_TICKER: Dict[str, ChainCompany] = {}
_BY_LAYER: Dict[ChainLayer, List[ChainCompany]] = {}

for _c in _ALL_COMPANIES:
    _BY_TICKER[_c.ticker_yf] = _c
    _BY_LAYER.setdefault(_c.layer, []).append(_c)


def get_all_companies() -> List[ChainCompany]:
    """返回所有已注册的公司列表"""
    return list(_ALL_COMPANIES)


def get_companies_by_layer(layer: ChainLayer) -> List[ChainCompany]:
    """获取指定链层的所有公司"""
    return list(_BY_LAYER.get(layer, []))


def get_core_players(layer: ChainLayer) -> List[ChainCompany]:
    """获取指定链层的核心玩家（is_core_player=True）"""
    return [c for c in _BY_LAYER.get(layer, []) if c.is_core_player]


def get_company(ticker: str) -> Optional[ChainCompany]:
    """根据 yfinance ticker 查找公司"""
    return _BY_TICKER.get(ticker)


def get_layers() -> List[ChainLayer]:
    """返回所有链层，按上下游顺序排列"""
    return sorted(ChainLayer, key=lambda x: x.sort_order)


def count_companies() -> int:
    """返回公司总数"""
    return len(_ALL_COMPANIES)


def count_by_layer() -> Dict[str, int]:
    """返回每层的公司数量"""
    return {layer.display_name: len(companies) for layer, companies in _BY_LAYER.items()}


def get_tickers() -> List[str]:
    """返回所有 yfinance ticker 列表，过滤掉空字符串"""
    return [c.ticker_yf for c in _ALL_COMPANIES if c.ticker_yf]
