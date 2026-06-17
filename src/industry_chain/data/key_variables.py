# -*- coding: utf-8 -*-
"""
AI 产业链关键变量追踪

跟踪框架中定义的 10 个关键变量，自动从可获取的数据源拉取，
部分变量标记为手动更新。

支持变量：
  - hyperscaler capex（从 MSFT/GOOG/AMZN/META 财报自动获取）
  - GPU 交付周期（手动更新）
  - HBM 价格趋势（手动更新）
  - CoWoS 产能（手动更新）
  - 推理 token 增速（手动更新）
  - API 定价趋势（手动更新）
  - 数据中心电力容量（手动更新）
  - 出口管制政策变更（手动更新）
  - 开源模型 benchmark 对比（手动更新）
  - 企业 AI 付费转化率（手动更新）
"""

from __future__ import annotations

import json
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.industry_chain.models import KeyVariable, VariableSource, VariableSnapshot

logger = logging.getLogger(__name__)

# 缓存路径
_VARIABLE_CACHE_DIR = Path(__file__).parent.parent.parent.parent / "data" / "cache" / "industry_chain"
_MANUAL_OVERRIDE_FILE = _VARIABLE_CACHE_DIR / "manual_variables.json"


def _build_hyperscaler_capex() -> KeyVariable:
    """构建 hyperscaler capex 变量定义（值从 yfinance 获取）"""
    return KeyVariable(
        name="hyperscaler_capex",
        display_name="Hyperscaler 资本开支",
        category="capex",
        source=VariableSource.AUTO_FINANCIAL,
        unit="billion USD (aggregate)",
        is_automated=True,
        data_source_desc="MSFT + GOOGL + AMZN + META 财年 capex 之和",
        notes="当前最大的 AI 需求驱动力，capex 持续增长是产业链繁荣的基座",
    )


def _build_gpu_delivery_lead_time() -> KeyVariable:
    return KeyVariable(
        name="gpu_delivery_lead_time",
        display_name="GPU 交付周期",
        category="supply",
        source=VariableSource.MANUAL,
        unit="weeks",
        is_automated=False,
        data_source_desc="通常由供应链调研/第三方报告提供",
        notes="Nvidia H100/B200 交付周期反映供需紧张程度",
    )


def _build_hbm_price_trend() -> KeyVariable:
    return KeyVariable(
        name="hbm_price_trend",
        display_name="HBM 价格趋势",
        category="pricing",
        source=VariableSource.MANUAL,
        unit="% QoQ",
        is_automated=False,
        data_source_desc="DRAMeXchange / TrendForce 报告",
        notes="HBM3E 供需状况的实时指标",
    )


def _build_cowos_capacity() -> KeyVariable:
    return KeyVariable(
        name="cowos_capacity",
        display_name="CoWoS 产能",
        category="supply",
        source=VariableSource.MANUAL,
        unit="kwpm (千片/月)",
        is_automated=False,
        data_source_desc="TSMC 法说会 / 供应链调研",
        notes="AI 芯片封装物理瓶颈，TSMC CoWoS 产能扩张进度",
    )


def _build_inference_token_growth() -> KeyVariable:
    return KeyVariable(
        name="inference_token_growth",
        display_name="推理 Token 增速",
        category="demand",
        source=VariableSource.MANUAL,
        unit="% QoQ",
        is_automated=False,
        data_source_desc="OpenAI / Anthropic / 云厂商披露",
        notes="框架核心假设：推理需求爆发式增长支撑长期需求",
    )


def _build_api_pricing_trend() -> KeyVariable:
    return KeyVariable(
        name="api_pricing_trend",
        display_name="模型 API 定价趋势",
        category="pricing",
        source=VariableSource.MANUAL,
        unit="% per token per year",
        is_automated=False,
        data_source_desc="各模型 API 官方定价跟踪",
        notes="每 token 成本下降速度影响产业链价值分布",
    )


def _build_data_center_power_capacity() -> KeyVariable:
    return KeyVariable(
        name="data_center_power_capacity",
        display_name="数据中心电力容量",
        category="supply",
        source=VariableSource.MANUAL,
        unit="GW",
        is_automated=False,
        data_source_desc="EIA / 云厂商披露 / McKinsey 报告",
        notes="电力已成为 AI 数据中心扩张的新瓶颈",
    )


def _build_export_control_policy() -> KeyVariable:
    return KeyVariable(
        name="export_control_policy",
        display_name="出口管制政策",
        category="policy",
        source=VariableSource.MANUAL,
        unit="enum (tightening/stable/loosening)",
        is_automated=False,
        data_source_desc="BIS 规则更新 / 政策新闻",
        notes="影响 NVDA 中国收入、中国国产替代进度",
    )


def _build_open_source_benchmark_gap() -> KeyVariable:
    return KeyVariable(
        name="open_source_benchmark_gap",
        display_name="开源 vs 闭源 Benchmark 差距",
        category="pricing",
        source=VariableSource.MANUAL,
        unit="% gap",
        is_automated=False,
        data_source_desc="LMSYS / MMLU / HumanEval 等榜单",
        notes="开源模型追赶速度影响闭源 API 定价权",
    )


def _build_enterprise_ai_adoption() -> KeyVariable:
    return KeyVariable(
        name="enterprise_ai_adoption",
        display_name="企业 AI 付费转化率",
        category="demand",
        source=VariableSource.MANUAL,
        unit="% of enterprises with paying AI workloads",
        is_automated=False,
        data_source_desc="MSFT / Salesforce / ServiceNow 财报电话会",
        notes="应用层收入的先行指标",
    )


# 所有变量定义
_DEFAULT_VARIABLES: List[KeyVariable] = [
    _build_hyperscaler_capex(),
    _build_gpu_delivery_lead_time(),
    _build_hbm_price_trend(),
    _build_cowos_capacity(),
    _build_inference_token_growth(),
    _build_api_pricing_trend(),
    _build_data_center_power_capacity(),
    _build_export_control_policy(),
    _build_open_source_benchmark_gap(),
    _build_enterprise_ai_adoption(),
]


class KeyVariableManager:
    """关键变量管理器

    负责：
    - 维护变量定义和当前值
    - 自动更新可自动获取的变量
    - 加载/保存手动更新的变量
    """

    def __init__(self):
        self._variables: Dict[str, KeyVariable] = {}
        for v in _DEFAULT_VARIABLES:
            self._variables[v.name] = v
        self._load_manual_overrides()

    # ---------------------------------------------------------------
    # 查询
    # ---------------------------------------------------------------

    def get_all(self) -> List[KeyVariable]:
        return list(self._variables.values())

    def get(self, name: str) -> Optional[KeyVariable]:
        return self._variables.get(name)

    def get_by_category(self, category: str) -> List[KeyVariable]:
        return [v for v in self._variables.values() if v.category == category]

    def get_automated(self) -> List[KeyVariable]:
        return [v for v in self._variables.values() if v.is_automated]

    def get_manual(self) -> List[KeyVariable]:
        return [v for v in self._variables.values() if not v.is_automated]

    # ---------------------------------------------------------------
    # 更新
    # ---------------------------------------------------------------

    def update_manual(self, name: str, value: float, notes: str = "") -> None:
        """手动更新一个变量的值"""
        var = self._variables.get(name)
        if var is None:
            logger.warning("update_manual: unknown variable %s", name)
            return
        var.previous_value = var.current_value
        var.current_value = value
        var.previous_date = date.today()
        if var.previous_value and var.previous_value != 0:
            var.change_pct = round((value - var.previous_value) / abs(var.previous_value) * 100, 2)
        var.trend = self._infer_trend(var.change_pct)
        if notes:
            var.notes = notes
        self._save_manual_overrides()

    def update_from_capex_scan(self, financials_list: list) -> None:
        """从财务数据快照更新 hyperscaler capex"""
        hyperscaler_tickers = {"MSFT", "GOOGL", "AMZN", "META"}
        total_capex = 0.0
        count = 0
        for fin in financials_list:
            if fin.ticker in hyperscaler_tickers and fin.capex is not None:
                total_capex += fin.capex
                count += 1

        if count >= 3:  # 至少 3 家有数据才更新
            capex_var = self._variables.get("hyperscaler_capex")
            if capex_var:
                # capex 值是百万 USD，转 billion
                value_bn = round(total_capex / 1000, 2)
                capex_var.previous_value = capex_var.current_value
                capex_var.current_value = value_bn
                capex_var.previous_date = date.today()
                if capex_var.previous_value and capex_var.previous_value != 0:
                    capex_var.change_pct = round(
                        (value_bn - capex_var.previous_value) / abs(capex_var.previous_value) * 100, 2
                    )
                capex_var.trend = self._infer_trend(capex_var.change_pct)
                capex_var.signal = self._capex_signal(capex_var.change_pct)

    def snapshot(self) -> VariableSnapshot:
        """生成当前所有变量的快照"""
        return VariableSnapshot(variables=list(self._variables.values()), snapshot_date=date.today())

    # ---------------------------------------------------------------
    # 持久化手动变量
    # ---------------------------------------------------------------

    def _load_manual_overrides(self) -> None:
        path = _MANUAL_OVERRIDE_FILE
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for name, values in data.items():
                var = self._variables.get(name)
                if var is None:
                    continue
                var.current_value = values.get("value")
                var.previous_value = values.get("previous_value")
                var.change_pct = values.get("change_pct")
                var.trend = values.get("trend", "stable")
                var.signal = values.get("signal", "neutral")
                var.notes = values.get("notes", "")
                if values.get("updated_date"):
                    try:
                        var.previous_date = date.fromisoformat(values["updated_date"])
                    except ValueError:
                        pass
        except Exception as exc:
            logger.warning("load manual overrides failed: %s", exc)

    def _save_manual_overrides(self) -> None:
        _VARIABLE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        manual = {}
        for var in self._variables.values():
            if var.source == VariableSource.MANUAL and var.current_value is not None:
                manual[var.name] = {
                    "value": var.current_value,
                    "previous_value": var.previous_value,
                    "change_pct": var.change_pct,
                    "trend": var.trend,
                    "signal": var.signal,
                    "notes": var.notes,
                    "updated_date": str(var.previous_date) if var.previous_date else None,
                }
        try:
            _MANUAL_OVERRIDE_FILE.write_text(
                json.dumps(manual, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as exc:
            logger.warning("save manual overrides failed: %s", exc)

    # ---------------------------------------------------------------
    # 辅助
    # ---------------------------------------------------------------

    @staticmethod
    def _infer_trend(change_pct: Optional[float]) -> str:
        if change_pct is None:
            return "stable"
        if change_pct > 5:
            return "up"
        if change_pct < -5:
            return "down"
        return "stable"

    @staticmethod
    def _capex_signal(change_pct: Optional[float]) -> str:
        """hyperscaler capex 增长 = bullish for infrastructure"""
        if change_pct is None:
            return "neutral"
        if change_pct > 10:
            return "bullish"
        if change_pct < -10:
            return "bearish"
        return "neutral"
