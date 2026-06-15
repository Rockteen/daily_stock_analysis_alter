# -*- coding: utf-8 -*-
import pytest
from datetime import date, timedelta
from src.sector.sector_data import SectorSnapshot
from src.sector.distribution_scorer import DistributionScorer, DistributionResult

@pytest.fixture
def scorer():
    return DistributionScorer(threshold_alert=50)

def test_detect_top_divergence_macd(scorer):
    # 构建 25 天的历史快照以触发顶背离检测
    history = []
    base_date = date(2026, 5, 1)
    
    # 模拟过去的价格和指标
    for i in range(25):
        # 设第15天 (index 14) 是峰值：收盘价 10.0，macd_dif = 0.5，rsi = 70.0
        if i == 14:
            close = 10.0
            macd_dif = 0.5
            rsi = 70.0
        else:
            close = 9.0
            macd_dif = 0.1
            rsi = 50.0
            
        snap = SectorSnapshot(
            etf_code="512480", sector_name="半导体",
            trade_date=base_date + timedelta(days=i),
            close=close, open=close, high=close, low=close, volume=1000.0, volume_ma60=1000.0,
            ma5=9.0, ma10=9.0, ma20=9.0, ma60=9.0, ma200=9.0,
            macd_dif=macd_dif, macd_dea=0.0, macd_bar=0.0, rsi_14=rsi,
            bias_ma5=0.0, bias_ma20=0.0, rs_vs_benchmark=1.0, rs_trend="falling",
            breadth_up_pct=50.0, breadth_above_ma20_pct=0.0, breadth_new_high_pct=0.0,
            box_high=10.0, box_low=8.0, is_near_box_low=False, smp_delta=None
        )
        history.append(snap)
        
    # 当前快照：收盘价 10.5 (创新高)，但 macd_dif 降低为 0.3 (< 0.5 * 0.9)
    current_snapshot = SectorSnapshot(
        etf_code="512480", sector_name="半导体",
        trade_date=base_date + timedelta(days=25),
        close=10.5, open=10.4, high=10.6, low=10.3, volume=1000.0, volume_ma60=1000.0,
        ma5=10.0, ma10=9.8, ma20=9.6, ma60=9.2, ma200=9.0,
        macd_dif=0.3, macd_dea=0.0, macd_bar=0.0, rsi_14=65.0, # RSI 也稍低于峰值但没有 MACD 明显，任一背离都行
        bias_ma5=5.0, bias_ma20=9.38, rs_vs_benchmark=1.0, rs_trend="rising",
        breadth_up_pct=50.0, breadth_above_ma20_pct=0.0, breadth_new_high_pct=0.0,
        box_high=10.5, box_low=8.0, is_near_box_low=False, smp_delta=None
    )
    
    assert scorer._detect_top_divergence(current_snapshot, history) is True

def test_distribution_score_exit(scorer):
    # 破位退出：价格同时跌破 MA20 和 MA60 (break_support = 100)
    snapshot = SectorSnapshot(
        etf_code="512480", sector_name="半导体",
        trade_date=date(2026, 6, 15),
        close=8.5, open=8.9, high=9.0, low=8.4, volume=1000.0, volume_ma60=1000.0,
        ma5=9.0, ma10=9.2, ma20=9.3, ma60=9.1, ma200=8.8, # close < ma20 且 close < ma60
        macd_dif=-0.2, macd_dea=-0.15, macd_bar=-0.1, rsi_14=35.0,
        bias_ma5=-5.56, bias_ma20=-8.6, rs_vs_benchmark=0.9, rs_trend="falling",
        breadth_up_pct=20.0, breadth_above_ma20_pct=0.0, breadth_new_high_pct=0.0,
        box_high=10.0, box_low=8.0, is_near_box_low=False, smp_delta=None
    )
    
    result = scorer.score(snapshot, [])
    assert result.stage == "exit"
    assert result.dimension_scores["break_support"] == 100

def test_distribution_score_alert(scorer):
    # 触发警报：
    # 1. 最终评分 >= 50
    # 2. volume_divergence 或 divergence 触发
    # 3. 价格未触发 exit
    snapshot = SectorSnapshot(
        etf_code="512480", sector_name="半导体",
        trade_date=date(2026, 6, 15),
        close=9.8, open=9.7, high=9.9, low=9.6,
        volume=600.0, volume_ma60=1000.0, # volume_ratio = 0.6 (< 0.8, 缩量上涨)
        ma5=9.7, ma10=9.6, ma20=9.5, ma60=9.0, ma200=8.5, # close >= ma20 且 close >= ma60
        macd_dif=0.2, macd_dea=0.18, macd_bar=0.04, rsi_14=65.0,
        bias_ma5=1.03, bias_ma20=3.16, rs_vs_benchmark=1.1, rs_trend="rising",
        breadth_up_pct=35.0, # 广度恶化 (breadth_deterioration = 100)
        breadth_above_ma20_pct=0.0, breadth_new_high_pct=0.0,
        box_high=10.0, box_low=8.0,
        is_near_box_low=False, smp_delta=None
    )
    
    # 此时价格 9.8 >= box_high * 0.95 = 9.5，故处于高位区间。
    # volume_ratio = 0.6 < 0.8，触发缩量上涨量能背离 (volume_divergence = 100)
    # breadth_up_pct = 35 < 40，触发广度恶化 (breadth_deterioration = 100)
    # break_support = 0
    # weighted_sum = 0 * 0.25 + 100 * 0.20 + 100 * 0.15 + 0 * 0.10 = 35
    # final_score = int(35 / 0.70) = 50
    result = scorer.score(snapshot, [])
    assert result.score == 50
    assert result.stage == "alert"
    assert any("缩量上涨量能背离" in cond for cond in result.triggered_conditions)
    assert any("广度严重恶化" in cond for cond in result.triggered_conditions)

def test_distribution_score_none(scorer):
    # 正常平稳行情
    snapshot = SectorSnapshot(
        etf_code="512480", sector_name="半导体",
        trade_date=date(2026, 6, 15),
        close=9.4, open=9.4, high=9.5, low=9.3,
        volume=950.0, volume_ma60=1000.0,
        ma5=9.4, ma10=9.4, ma20=9.4, ma60=9.2, ma200=9.0,
        macd_dif=0.05, macd_dea=0.04, macd_bar=0.02, rsi_14=52.0,
        bias_ma5=0.0, bias_ma20=0.0, rs_vs_benchmark=1.0, rs_trend="rising",
        breadth_up_pct=52.0, breadth_above_ma20_pct=0.0, breadth_new_high_pct=0.0,
        box_high=10.0, box_low=8.0, is_near_box_low=False, smp_delta=None
    )
    
    result = scorer.score(snapshot, [])
    assert result.score == 0
    assert result.stage == "none"

