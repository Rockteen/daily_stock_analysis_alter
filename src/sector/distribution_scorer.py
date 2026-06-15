# -*- coding: utf-8 -*-
"""
见顶评分器 (Distribution Scorer)
"""

import logging
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from .sector_data import SectorSnapshot

logger = logging.getLogger(__name__)

@dataclass
class DistributionResult:
    score: int                        # 0-100 综合评分
    dimension_scores: Dict[str, int]  # 各维度分项得分
    triggered_conditions: List[str]    # 触发的条件说明
    stage: str                        # "none" / "alert" / "exit"

class DistributionScorer:
    """
    见顶评分器：合成六个维度的见顶信号并输出 0-100 的综合评分。
    
    权重分配:
      ① 聪明钱撤离 (SMP)         - 25% (Phase 1 默认为 0)
      ② 顶背离 (MACD/RSI)        - 25%
      ③ 量能背离/滞涨 (量能背离)   - 20%
      ④ 广度恶化 (成分股滞涨)     - 15%
      ⑤ 估值/拥挤极端            - 5%  (Phase 1 默认为 0)
      ⑥ 破位 (跌破关键均线)      - 10%
    """
    def __init__(self, threshold_alert: int = 50):
        self.threshold_alert = threshold_alert

    def _detect_top_divergence(self, snapshot: SectorSnapshot, history: List[SectorSnapshot]) -> bool:
        """
        顶背离检测：价格创新高或处于高位，但 MACD DIF 或 RSI 出现更低的峰值
        """
        if not history or len(history) < 10:
            return False
            
        # 必须处于 60日高位区间
        if snapshot.close < snapshot.box_high * 0.93:
            return False

        # 寻找过去 20 个交易日中，价格最高的那一天 (排除最近 2 天以防噪声)
        lookback = history[-22:-2]
        if not lookback:
            return False
            
        peak_idx = -1
        max_close = -1.0
        for i, hist_snap in enumerate(lookback):
            if hist_snap.close > max_close:
                max_close = hist_snap.close
                peak_idx = i
                
        if peak_idx == -1:
            return False
            
        peak_snap = lookback[peak_idx]
        
        # 顶背离判定条件：
        # 当前价格高于或等于历史高点价格，但是当前的指标低于当时的值
        if snapshot.close >= peak_snap.close:
            # MACD DIF 顶背离
            if snapshot.macd_dif < peak_snap.macd_dif * 0.9:
                return True
            # RSI 顶背离
            if snapshot.rsi_14 < peak_snap.rsi_14 * 0.9:
                return True
                
        return False

    def score(self, snapshot: SectorSnapshot, history: List[SectorSnapshot]) -> DistributionResult:
        """
        计算板块 ETF 的见顶评分并返回诊断结果
        """
        dimension_scores = {
            "smp": 0,
            "divergence": 0,
            "volume_divergence": 0,
            "breadth_deterioration": 0,
            "valuation": 0,
            "break_support": 0
        }
        triggered_conditions = []

        # 1. 聪明钱撤离 (SMP) - 默认 0
        if snapshot.smp_delta is not None:
            if snapshot.smp_delta < 0:
                dimension_scores["smp"] = 100
                triggered_conditions.append("聪明钱持续减仓 (SMP增量 < 0)")

        # 2. 顶背离 (MACD/RSI)
        if self._detect_top_divergence(snapshot, history):
            dimension_scores["divergence"] = 100
            triggered_conditions.append("发现技术顶背离 (价格创高但MACD/RSI走低)")

        # 3. 量能背离/滞涨
        volume_ratio = 1.0
        if snapshot.volume_ma60 > 0:
            volume_ratio = snapshot.volume / snapshot.volume_ma60
            
        # 情况 A: 缩量上涨 (价格在高位但成交量低于均线 80%)
        is_at_high = snapshot.close >= snapshot.box_high * 0.95
        if is_at_high and volume_ratio < 0.8:
            dimension_scores["volume_divergence"] = 100
            triggered_conditions.append(f"缩量上涨量能背离 (高位成交量仅为均线 {volume_ratio:.2f} 倍)")
        # 情况 B: 放量滞涨 (成交量超过均线 1.6 倍，但收盘价变动极小且实体小)
        elif volume_ratio >= 1.6:
            price_change_abs = abs(snapshot.close - snapshot.open) / snapshot.open * 100
            if price_change_abs < 1.0:
                dimension_scores["volume_divergence"] = 100
                triggered_conditions.append(f"放量滞涨 (成交量达均线 {volume_ratio:.2f} 倍，但当日价格波动仅 {price_change_abs:.2f}%)")

        # 4. 广度恶化
        # 板块指数高位，但上涨家数占比小于 40% (分化严重)
        if is_at_high and snapshot.breadth_up_pct < 40.0:
            dimension_scores["breadth_deterioration"] = 100
            triggered_conditions.append(f"广度严重恶化 (高位普跌，仅有 {snapshot.breadth_up_pct:.1f}% 个股上涨)")
        elif is_at_high and snapshot.breadth_up_pct < 50.0:
            dimension_scores["breadth_deterioration"] = 50
            triggered_conditions.append(f"广度有所转差 (上涨个股占比下降至 {snapshot.breadth_up_pct:.1f}%)")

        # 5. 估值/拥挤度 - 默认 0

        # 6. 破位 (跌破 MA20 / MA60)
        if snapshot.close < snapshot.ma20 and snapshot.close < snapshot.ma60:
            dimension_scores["break_support"] = 100
            triggered_conditions.append("关键支撑位跌破 (价格同时跌破 MA20 和 MA60)")
        elif snapshot.close < snapshot.ma20:
            dimension_scores["break_support"] = 50
            triggered_conditions.append("跌破短线关键支撑 (价格收于 MA20 下方)")

        # 评分合成逻辑
        # Phase 1 动态调整权重：剔除 SMP 和 valuation 后的有效权重
        # divergence(25%), volume_divergence(20%), breadth_deterioration(15%), break_support(10%) -> 总共 70%
        active_weight = 0.70
        weighted_sum = (
            dimension_scores["divergence"] * 0.25 +
            dimension_scores["volume_divergence"] * 0.20 +
            dimension_scores["breadth_deterioration"] * 0.15 +
            dimension_scores["break_support"] * 0.10
        )
        
        # 计算 0-100 的最终得分
        final_score = int(weighted_sum / active_weight)

        # 状态机分级判定
        # 1. 见顶预警 (Alert): 评分超高，且出现背离
        # 2. 见顶确认 (Exit): 跌破关键支撑
        stage = "none"
        if dimension_scores["break_support"] >= 100:
            stage = "exit"
        elif final_score >= self.threshold_alert and (dimension_scores["divergence"] >= 100 or dimension_scores["volume_divergence"] >= 100):
            stage = "alert"

        return DistributionResult(
            score=final_score,
            dimension_scores=dimension_scores,
            triggered_conditions=triggered_conditions,
            stage=stage
        )
