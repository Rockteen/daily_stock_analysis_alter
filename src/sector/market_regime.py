# -*- coding: utf-8 -*-
"""
大盘总开关 (Market Regime Switch)
"""

import logging
from dataclasses import dataclass
from datetime import date
from typing import Optional, Literal
import pandas as pd

logger = logging.getLogger(__name__)

@dataclass
class MarketRegime:
    status: Literal["risk_on", "risk_off"]
    benchmark_code: str
    benchmark_close: float
    benchmark_ma200: float
    margin_pct: float              # 距离 MA200 的偏离百分比

class MarketRegimeSwitch:
    """
    市场大盘环境过滤器（系统级开关）
    基准: 沪深300指数 (000300)
    规则:
      - 价格 > 200日均线: 🟢 风险 ON  (允许进场做多)
      - 价格 < 200日均线: 🔴 风险 OFF (强制退场观望，禁止开新仓)
    """
    def __init__(self, benchmark_code: str = "000300"):
        self.benchmark_code = benchmark_code

    def evaluate(self, benchmark_df: pd.DataFrame, trade_date: Optional[date] = None) -> MarketRegime:
        """
        评估大盘环境
        """
        if benchmark_df is None or benchmark_df.empty:
            logger.warning("大盘基准数据为空，默认设置为 🟢 risk_on")
            return MarketRegime(
                status="risk_on",
                benchmark_code=self.benchmark_code,
                benchmark_close=0.0,
                benchmark_ma200=0.0,
                margin_pct=0.0
            )

        # 确保计算了 MA200
        if 'ma200' not in benchmark_df.columns:
            benchmark_df['ma200'] = benchmark_df['close'].rolling(window=200, min_periods=1).mean()

        # 获取目标日期行
        if trade_date is not None:
            row_df = benchmark_df[benchmark_df['date'] == trade_date]
            if row_df.empty:
                # 寻找最接近的历史交易日
                past_df = benchmark_df[benchmark_df['date'] < trade_date]
                if past_df.empty:
                    row = benchmark_df.iloc[-1]
                else:
                    row = past_df.iloc[-1]
            else:
                row = row_df.iloc[0]
        else:
            row = benchmark_df.iloc[-1]

        close = float(row['close'])
        ma200 = float(row['ma200'])
        
        # 计算偏离度百分比
        margin_pct = 0.0
        if ma200 > 0:
            margin_pct = ((close - ma200) / ma200) * 100

        # 判断风险状态
        status: Literal["risk_on", "risk_off"] = "risk_on" if close >= ma200 else "risk_off"

        logger.info(
            f"大盘总开关评估 [{row['date']}]: 基准={self.benchmark_code}, 收盘={close:.2f}, "
            f"MA200={ma200:.2f}, 偏离度={margin_pct:.2f}%, 状态={status.upper()}"
        )

        return MarketRegime(
            status=status,
            benchmark_code=self.benchmark_code,
            benchmark_close=close,
            benchmark_ma200=ma200,
            margin_pct=round(margin_pct, 2)
        )
