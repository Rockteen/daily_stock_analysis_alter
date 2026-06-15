# -*- coding: utf-8 -*-
"""
板块数据采集与技术指标计算
"""

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np

from data_provider import DataFetcherManager
from data_provider.base import normalize_stock_code

logger = logging.getLogger(__name__)

# 默认行业/主题 ETF 与其对应的成分股指数映射
DEFAULT_ETF_POOL = {
    "512480": {"name": "半导体ETF", "index": "399976", "category": "industry"},
    "512010": {"name": "医药ETF", "index": "000913", "category": "industry"},
    "512880": {"name": "证券ETF", "index": "399975", "category": "industry"},
    "512660": {"name": "军工ETF", "index": "399959", "category": "industry"},
    "515050": {"name": "5GETF", "index": "931079", "category": "theme"},
    "516160": {"name": "新能源ETF", "index": "399808", "category": "industry"},
    "512800": {"name": "银行ETF", "index": "399986", "category": "industry"},
    "510150": {"name": "消费ETF", "index": "000036", "category": "industry"},
}

# 避险 ETF 列表
SAFE_HAVEN_ETFS = {
    "511260": {"name": "十年国债ETF", "index": "H11002", "category": "safe_haven"},
    "511880": {"name": "银华日利ETF", "index": "000001", "category": "safe_haven"}, # 货币型，参考上证指数
    "518880": {"name": "黄金ETF", "index": "AU9999", "category": "safe_haven"},
}

@dataclass
class SectorSnapshot:
    """单个板块的完整数据快照"""
    etf_code: str                    # ETF 代码 (如 "512480")
    sector_name: str                 # 板块名称 (如 "半导体")
    trade_date: date                 # 交易日
    
    # 价格量能 K 线数据
    close: float
    open: float
    high: float
    low: float
    volume: float
    volume_ma60: float
    
    # 均线数据
    ma5: float
    ma10: float
    ma20: float
    ma60: float
    ma200: float
    
    # 技术指标
    macd_dif: float
    macd_dea: float
    macd_bar: float
    rsi_14: float
    bias_ma5: float
    bias_ma20: float
    
    # 相对强度 (相对于大盘基准，例如 000300)
    rs_vs_benchmark: float           # 板块/沪深300 收盘价比例
    rs_trend: str                    # "rising" (大于20日均值) 或 "falling"
    
    # 板块广度
    breadth_up_pct: float            # 成分股上涨家数占比 (0-100)
    breadth_above_ma20_pct: float    # 成分股站上 MA20 占比 (预留，默认 0.0)
    breadth_new_high_pct: float      # 成分股创 20 日新高占比 (预留，默认 0.0)
    
    # 估值 (预留，Phase 2)
    pe_percentile: Optional[float] = None
    
    # 60日箱体结构
    box_high: float = 0.0            # 60日最高收盘价
    box_low: float = 0.0             # 60日最低收盘价
    is_near_box_low: bool = False    # 是否接近箱体下沿 (收盘价 <= box_low * 1.05)
    
    # 聪明钱 (预留，Phase 3 接入)
    smp_delta: Optional[float] = None


class SectorDataCollector:
    """
    板块数据采集器，负责获取 ETF 行情、计算各项量价指标、计算成分股广度
    """
    def __init__(self, fetcher_manager: Optional[DataFetcherManager] = None):
        self.fetcher_manager = fetcher_manager or DataFetcherManager()

    def get_benchmark_data(self, benchmark_code: str = "000300", days: int = 300) -> pd.DataFrame:
        """
        获取大盘基准的 K 线历史数据
        """
        code = normalize_stock_code(benchmark_code)
        try:
            df, _ = self.fetcher_manager.get_daily_data(code, days=days)
            if df is not None and not df.empty:
                df['date'] = pd.to_datetime(df['date']).dt.date
                df = df.sort_values('date').reset_index(drop=True)
                return df
        except Exception as e:
            logger.error(f"获取大盘基准 {benchmark_code} 数据失败: {e}")
        return pd.DataFrame()

    def calculate_technical_indicators(self, df: pd.DataFrame, benchmark_df: pd.DataFrame) -> pd.DataFrame:
        """
        计算板块 ETF 拐点所需的全部技术指标与相对强度
        """
        df = df.copy()
        
        # 1. 均线计算
        df['ma5'] = df['close'].rolling(window=5, min_periods=1).mean()
        df['ma10'] = df['close'].rolling(window=10, min_periods=1).mean()
        df['ma20'] = df['close'].rolling(window=20, min_periods=1).mean()
        df['ma60'] = df['close'].rolling(window=60, min_periods=1).mean()
        df['ma200'] = df['close'].rolling(window=200, min_periods=1).mean()
        
        # 2. 成交量均线
        df['volume_ma60'] = df['volume'].rolling(window=60, min_periods=1).mean()
        
        # 3. MACD 计算 (12, 26, 9)
        exp12 = df['close'].ewm(span=12, adjust=False).mean()
        exp26 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd_dif'] = exp12 - exp26
        df['macd_dea'] = df['macd_dif'].ewm(span=9, adjust=False).mean()
        df['macd_bar'] = 2 * (df['macd_dif'] - df['macd_dea'])
        
        # 4. RSI-14 计算
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs = avg_gain / avg_loss
        df['rsi_14'] = 100 - (100 / (1 + rs))
        df['rsi_14'] = df['rsi_14'].fillna(50.0) # 填充初始未计算部分
        
        # 5. 乖离率 (BIAS)
        df['bias_ma5'] = (df['close'] - df['ma5']) / df['ma5'] * 100
        df['bias_ma20'] = (df['close'] - df['ma20']) / df['ma20'] * 100
        
        # 6. 60日箱体边界
        df['box_high'] = df['close'].rolling(window=60, min_periods=1).max()
        df['box_low'] = df['close'].rolling(window=60, min_periods=1).min()
        df['is_near_box_low'] = df['close'] <= (df['box_low'] * 1.05)
        
        # 7. 相对强度 RS (相对于大盘基准)
        # 将 benchmark 的 close 数据合并进来
        bench_close = benchmark_df.set_index('date')['close']
        df['bench_close'] = df['date'].map(bench_close)
        df['bench_close'] = df['bench_close'].ffill() # 填充缺失值
        
        df['rs_vs_benchmark'] = df['close'] / df['bench_close']
        df['rs_vs_benchmark'] = df['rs_vs_benchmark'].fillna(1.0)
        
        # 计算 RS 的 20 日均值作为趋势过滤器
        df['rs_ma20'] = df['rs_vs_benchmark'].rolling(window=20, min_periods=1).mean()
        df['rs_trend'] = np.where(df['rs_vs_benchmark'] > df['rs_ma20'], 'rising', 'falling')
        
        return df

    def get_sector_breadth(self, index_code: str) -> float:
        """
        获取板块对应指数的上涨家数占比 (breadth_up_pct)
        使用 ak.stock_zh_a_spot_em() 获取全市场涨跌幅，并筛选指数成分股
        """
        import akshare as ak
        try:
            # 1. 获取最新指数成分股
            cons_df = ak.index_stock_cons(symbol=index_code)
            if cons_df is None or cons_df.empty:
                logger.warning(f"未能获取到指数 {index_code} 的成分股")
                return 50.0 # 默认中值
            
            # 成分股代码集合
            cons_codes = set(cons_df['品种代码'].astype(str).str.zfill(6))
            if not cons_codes:
                return 50.0
                
            # 2. 获取全市场实时行情
            spot_df = ak.stock_zh_a_spot_em()
            if spot_df is None or spot_df.empty:
                logger.warning("未能获取到全市场 A 股实时行情，将使用默认广度值")
                return 50.0
                
            # 3. 过滤出成分股并统计
            spot_df['代码'] = spot_df['代码'].astype(str).str.zfill(6)
            cons_spot = spot_df[spot_df['代码'].isin(cons_codes)]
            
            if cons_spot.empty:
                return 50.0
                
            total_active = len(cons_spot)
            # 涨跌幅大于 0 的视为上涨
            rising_count = len(cons_spot[cons_spot['涨跌幅'] > 0])
            
            breadth_up_pct = (rising_count / total_active) * 100
            logger.info(f"指数 {index_code} 广度计算成功: 成分股总数 {len(cons_codes)}, 匹配数 {total_active}, 上涨数 {rising_count}, 广度 {breadth_up_pct:.2f}%")
            return round(breadth_up_pct, 2)
            
        except Exception as e:
            logger.error(f"计算指数 {index_code} 广度时出错: {e}")
            return 50.0

    def collect_snapshot(
        self, 
        etf_code: str, 
        sector_name: str, 
        index_code: str,
        benchmark_df: pd.DataFrame,
        trade_date: Optional[date] = None
    ) -> Optional[SectorSnapshot]:
        """
        获取指定板块的最新行情快照并生成 SectorSnapshot
        """
        code = normalize_stock_code(etf_code)
        try:
            # 获取 ETF 行情，多取一些以便计算 MA200
            df, _ = self.fetcher_manager.get_daily_data(code, days=300)
            if df is None or df.empty:
                logger.error(f"获取 ETF {etf_code} 历史行情为空")
                return None
                
            df['date'] = pd.to_datetime(df['date']).dt.date
            df = df.sort_values('date').reset_index(drop=True)
            
            # 计算技术指标
            df_with_inds = self.calculate_technical_indicators(df, benchmark_df)
            
            # 选择指定交易日或最新一日的数据
            if trade_date is not None:
                row_df = df_with_inds[df_with_inds['date'] == trade_date]
                if row_df.empty:
                    # 如果找不到，使用最接近且小于指定日期的数据
                    past_df = df_with_inds[df_with_inds['date'] < trade_date]
                    if past_df.empty:
                        logger.error(f"在历史行情中未找到交易日 {trade_date} 之前的数据")
                        return None
                    row = past_df.iloc[-1]
                else:
                    row = row_df.iloc[0]
            else:
                row = df_with_inds.iloc[-1]
            
            # 获取成分股广度（使用最新当日广度）
            breadth_up_pct = self.get_sector_breadth(index_code)
            
            # 组装快照对象
            snapshot = SectorSnapshot(
                etf_code=etf_code,
                sector_name=sector_name,
                trade_date=row['date'],
                close=float(row['close']),
                open=float(row['open']),
                high=float(row['high']),
                low=float(row['low']),
                volume=float(row['volume']),
                volume_ma60=float(row.get('volume_ma60', row['volume'])),
                ma5=float(row['ma5']),
                ma10=float(row['ma10']),
                ma20=float(row['ma20']),
                ma60=float(row.get('ma60', row['close'])),
                ma200=float(row.get('ma200', row['close'])),
                macd_dif=float(row.get('macd_dif', 0.0)),
                macd_dea=float(row.get('macd_dea', 0.0)),
                macd_bar=float(row.get('macd_bar', 0.0)),
                rsi_14=float(row.get('rsi_14', 50.0)),
                bias_ma5=float(row.get('bias_ma5', 0.0)),
                bias_ma20=float(row.get('bias_ma20', 0.0)),
                rs_vs_benchmark=float(row.get('rs_vs_benchmark', 1.0)),
                rs_trend=str(row.get('rs_trend', 'falling')),
                breadth_up_pct=breadth_up_pct,
                breadth_above_ma20_pct=0.0,
                breadth_new_high_pct=0.0,
                box_high=float(row.get('box_high', row['close'])),
                box_low=float(row.get('box_low', row['close'])),
                is_near_box_low=bool(row.get('is_near_box_low', False)),
                smp_delta=None
            )
            return snapshot
            
        except Exception as e:
            logger.error(f"收集板块 {sector_name}({etf_code}) 数据快照失败: {e}", exc_info=True)
            return None
