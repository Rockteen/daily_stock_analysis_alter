# -*- coding: utf-8 -*-
"""
聪明钱仓位计算接口 (SMP Calculator Placeholder)
"""

import logging
from datetime import date
from typing import Optional

logger = logging.getLogger(__name__)


class SMPCalculator:
    """
    聪明钱仓位 (Smart Money Position) 计算器。
    当前阶段作为占位实现，默认返回 0.0 或 None。
    """
    def __init__(self):
        pass

    def calculate_smp_delta(self, etf_code: str, trade_date: date) -> Optional[float]:
        """
        计算指定板块 ETF 在交易日的聪明钱仓位变化量 (ΔSMP)。
        返回值代表仓位变化比例（如 0.05 代表流入 5%，-0.02 代表流出 2%）。
        
        当前返回 0.0 占位。
        """
        logger.debug(f"SMP 计算占位：{etf_code} 在 {trade_date}")
        return 0.0
