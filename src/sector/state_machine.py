# -*- coding: utf-8 -*-
"""
板块状态机 (Sector State Machine)
"""

import logging
from enum import Enum
from typing import Tuple
from .market_regime import MarketRegime
from .ignition_scorer import IgnitionResult
from .distribution_scorer import DistributionResult

logger = logging.getLogger(__name__)

class SectorState(str, Enum):
    SCANNING = "scanning"       # 空仓·扫描
    LURKING = "lurking"         # 潜伏观察
    HOLDING = "holding"         # 持有
    ALERT = "alert"             # 警戒持有
    EXITED = "exited"           # 离场中间态

class SectorStateMachine:
    """
    五状态机实现，管理单个板块的生命周期状态转换。
    
    转换逻辑:
      - SCANNING -> LURKING:   启动评分出现潜伏信号 (watch)
      - LURKING -> HOLDING:    启动评分出现确认买入信号 (confirmed)
      - LURKING -> SCANNING:   潜伏超时（默认30天）或信号消失
      - HOLDING -> ALERT:      见顶评分出现预警信号 (alert)
      - HOLDING -> EXITED:     大盘总开关转为风险 OFF (risk_off)
      - ALERT -> EXITED:       跌破关键均线确认离场 (exit) 或大盘转风险 OFF
      - ALERT -> HOLDING:      警报解除 (none)
      - EXITED -> SCANNING:    自动回滚
    """
    def __init__(self, lurk_timeout_days: int = 30):
        self.lurk_timeout_days = lurk_timeout_days

    def transition(
        self,
        current_state: SectorState,
        ignition: IgnitionResult,
        distribution: DistributionResult,
        regime: MarketRegime,
        days_in_state: int
    ) -> Tuple[SectorState, str]:
        """
        根据最新指标评估状态转换，返回 (新状态, 转移原因)
        """
        # 1. 大盘总闸门判断：风险 OFF 时，所有持仓状态 (HOLDING, ALERT) 强制清仓离场
        if regime.status == "risk_off":
            if current_state in (SectorState.HOLDING, SectorState.ALERT):
                return SectorState.EXITED, "大盘总开关风险 OFF，强制避险离场"
            elif current_state == SectorState.LURKING:
                return SectorState.SCANNING, "大盘总开关风险 OFF，取消潜伏观察"

        # 2. 状态机常规流转
        if current_state == SectorState.SCANNING:
            if ignition.stage == "watch":
                return SectorState.LURKING, "启动评分进入潜伏期（主力资金建仓+底部结构）"
            elif ignition.stage == "confirmed":
                # 若直接强力突起，也可直接进入持有
                return SectorState.HOLDING, "发现强力放量突破，直接进入持有期"

        elif current_state == SectorState.LURKING:
            if ignition.stage == "confirmed":
                return SectorState.HOLDING, "放量突破 + RS反转，买入信号确认"
            elif days_in_state >= self.lurk_timeout_days:
                return SectorState.SCANNING, f"潜伏期超时（已达 {days_in_state} 天未启动），退回扫描状态"
            elif ignition.stage == "none" and ignition.score < 30:
                return SectorState.SCANNING, f"底部结构遭到破坏，取消潜伏观察"

        elif current_state == SectorState.HOLDING:
            if distribution.stage == "alert":
                return SectorState.ALERT, "见顶评分预警（聪明钱撤离/顶背离），减半仓并收紧止损"
            elif distribution.stage == "exit":
                return SectorState.EXITED, "价格发生破位，见顶信号确认，全仓离场"

        elif current_state == SectorState.ALERT:
            if distribution.stage == "exit":
                return SectorState.EXITED, "关键支撑位跌破，最终离场信号触发"
            elif distribution.stage == "none":
                return SectorState.HOLDING, "警报解除（主力重回流入或技术形态修复）"

        elif current_state == SectorState.EXITED:
            # EXITED 是一个短暂的中间状态，用于触发卖出通知，随后自动归零为 SCANNING
            return SectorState.SCANNING, "卖出清仓完成，自动退回扫描状态"

        # 默认保持原状态
        return current_state, "状态保持"
