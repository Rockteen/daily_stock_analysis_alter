# -*- coding: utf-8 -*-
"""
启动评分器 (Ignition Scorer)
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, List
from .sector_data import SectorSnapshot

logger = logging.getLogger(__name__)

@dataclass
class IgnitionResult:
    score: int                        # 0-100 综合评分
    dimension_scores: Dict[str, int]  # 各维度分项得分
    triggered_conditions: List[str]    # 触发的条件说明
    stage: str                        # "none" / "watch" / "confirmed"

class IgnitionScorer:
    """
    启动评分器：合成六个维度的启动信号并输出 0-100 的综合评分。
    
    权重分配:
      ① 聪明钱先行 (SMP)         - 25% (Phase 1 默认为 0)
      ② 底部结构 (箱体低位/估值)   - 20%
      ③ 放量突破 (量量放大)       - 25%
      ④ 相对强度反转 (RS转强)     - 15%
      ⑤ 广度改善 (成分股普涨)     - 10%
      ⑥ 催化事件                 - 5%  (Phase 1 默认为 0)
    """
    def __init__(self, threshold_watch: int = 40, threshold_confirm: int = 65):
        self.threshold_watch = threshold_watch
        self.threshold_confirm = threshold_confirm

    def score(self, snapshot: SectorSnapshot, history: List[SectorSnapshot]) -> IgnitionResult:
        """
        计算板块 ETF 的启动评分并返回诊断结果
        """
        dimension_scores = {
            "smp": 0,                # 聪明钱 (Phase 1 预留)
            "bottom_structure": 0,   # 底部结构
            "volume_breakout": 0,    # 放量突破
            "rs_trend": 0,           # 相对强度
            "breadth": 0,            # 广度
            "catalyst": 0            # 催化事件 (Phase 1 预留)
        }
        triggered_conditions = []

        # 1. 聪明钱先行 (SMP) - 默认 0
        if snapshot.smp_delta is not None:
            # 预留实际计算逻辑
            if snapshot.smp_delta > 0:
                dimension_scores["smp"] = 100
                triggered_conditions.append("聪明钱流入 (SMP增量 > 0)")
        
        # 2. 底部结构 (箱体低位)
        # 靠近 60日收盘价箱体下沿
        if snapshot.is_near_box_low:
            dimension_scores["bottom_structure"] = 100
            triggered_conditions.append("价格处于60日箱体下沿支撑区")
        elif snapshot.close <= snapshot.box_low * 1.10:
            dimension_scores["bottom_structure"] = 60
            triggered_conditions.append("价格接近60日箱体下沿 (偏离小于10%)")
        
        # 3. 放量突破
        # 放量上涨：今日成交量 > 60日均量 * 1.5，且为阳线
        is_positive_day = snapshot.close >= snapshot.open
        volume_ratio = 1.0
        if snapshot.volume_ma60 > 0:
            volume_ratio = snapshot.volume / snapshot.volume_ma60

        if volume_ratio >= 1.5 and is_positive_day:
            dimension_scores["volume_breakout"] = 100
            triggered_conditions.append(f"放量突破 (成交量达60日均线 {volume_ratio:.2f} 倍)")
        elif volume_ratio >= 1.2 and is_positive_day:
            dimension_scores["volume_breakout"] = 60
            triggered_conditions.append(f"温和放量 (成交量达60日均线 {volume_ratio:.2f} 倍)")
        elif is_positive_day:
            dimension_scores["volume_breakout"] = 30

        # 4. 相对强度反转
        # RS 线处于上升趋势
        if snapshot.rs_trend == "rising":
            dimension_scores["rs_trend"] = 100
            triggered_conditions.append("相对强度趋势转强 (RS位于20日均线上方)")

        # 5. 广度改善
        # 上涨个股家数占比直接作为评分 (0-100)
        dimension_scores["breadth"] = int(snapshot.breadth_up_pct)
        if snapshot.breadth_up_pct >= 60:
            triggered_conditions.append(f"板块广度改善 (上涨家数占比 {snapshot.breadth_up_pct:.1f}%)")

        # 6. 催化事件 - 默认 0

        # 评分合成逻辑
        # Phase 1 动态调整权重：剔除 SMP 和 catalyst 后的有效权重
        # bottom_structure(20%), volume_breakout(25%), rs_trend(15%), breadth(10%) -> 总共 70%
        active_weight = 0.70
        weighted_sum = (
            dimension_scores["bottom_structure"] * 0.20 +
            dimension_scores["volume_breakout"] * 0.25 +
            dimension_scores["rs_trend"] * 0.15 +
            dimension_scores["breadth"] * 0.10
        )
        
        # 计算 0-100 的最终得分
        final_score = int(weighted_sum / active_weight)

        # 两段式判定阶段
        # 1. 潜伏预警 (Watch): 底部结构好 + 广度/RS开始有起色
        # 2. 启动确认 (Confirmed): 综合评分大于阈值，且有放量突破和相对强度确认
        stage = "none"
        if final_score >= self.threshold_confirm and dimension_scores["volume_breakout"] >= 60 and dimension_scores["rs_trend"] == 100:
            stage = "confirmed"
        elif dimension_scores["bottom_structure"] >= 60:
            stage = "watch"

        return IgnitionResult(
            score=final_score,
            dimension_scores=dimension_scores,
            triggered_conditions=triggered_conditions,
            stage=stage
        )
