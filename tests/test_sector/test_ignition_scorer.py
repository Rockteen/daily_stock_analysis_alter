# -*- coding: utf-8 -*-
import pytest
from datetime import date
from src.sector.sector_data import SectorSnapshot
from src.sector.ignition_scorer import IgnitionScorer, IgnitionResult

@pytest.fixture
def scorer():
    return IgnitionScorer(threshold_watch=40, threshold_confirm=65)

def test_ignition_score_confirmed(scorer):
    # 构建能够触发 confirmed 的快照
    # 要求：
    # 1. 最终评分 >= 65
    # 2. volume_breakout >= 60 (阳线且成交量是ma60的1.2倍以上)
    # 3. rs_trend == 100 ("rising")
    snapshot = SectorSnapshot(
        etf_code="512480",
        sector_name="半导体",
        trade_date=date(2026, 6, 15),
        close=10.0, open=9.5, high=10.5, low=9.4,
        volume=1600.0, volume_ma60=1000.0, # 1.6 倍，放量突破 (volume_breakout = 100)
        ma5=9.8, ma10=9.7, ma20=9.6, ma60=9.5, ma200=9.0,
        macd_dif=0.1, macd_dea=0.08, macd_bar=0.04, rsi_14=60.0,
        bias_ma5=2.04, bias_ma20=4.17, rs_vs_benchmark=1.2,
        rs_trend="rising", # rs_trend = 100
        breadth_up_pct=70.0, # breadth = 70
        breadth_above_ma20_pct=0.0, breadth_new_high_pct=0.0,
        box_high=10.0, box_low=9.0,
        is_near_box_low=False, # bottom_structure = 0
        smp_delta=None
    )
    
    # 权重和：0 * 0.20 + 100 * 0.25 + 100 * 0.15 + 70 * 0.10 = 25 + 15 + 7 = 47
    # 最终评分：int(47 / 0.7) = 67 >= 65
    result = scorer.score(snapshot, [])
    assert result.score == 67
    assert result.stage == "confirmed"
    assert any("相对强度趋势转强" in cond for cond in result.triggered_conditions)
    assert any("放量突破" in cond for cond in result.triggered_conditions)
    assert any("板块广度改善" in cond for cond in result.triggered_conditions)

def test_ignition_score_watch(scorer):
    # 构建触发 watch 的快照
    # 靠近箱体下沿 (bottom_structure = 100)
    snapshot = SectorSnapshot(
        etf_code="512480",
        sector_name="半导体",
        trade_date=date(2026, 6, 15),
        close=9.1, open=9.0, high=9.2, low=8.9,
        volume=1000.0, volume_ma60=1000.0, # volume_ratio = 1.0, 阳线 (volume_breakout = 30)
        ma5=9.3, ma10=9.4, ma20=9.5, ma60=9.6, ma200=9.8,
        macd_dif=-0.1, macd_dea=-0.08, macd_bar=-0.04, rsi_14=40.0,
        bias_ma5=-2.15, bias_ma20=-4.21, rs_vs_benchmark=0.8,
        rs_trend="falling", # rs_trend = 0
        breadth_up_pct=40.0, # breadth = 40
        breadth_above_ma20_pct=0.0, breadth_new_high_pct=0.0,
        box_high=10.0, box_low=9.0,
        is_near_box_low=True, # bottom_structure = 100
        smp_delta=None
    )
    
    # 权重和：100 * 0.20 + 30 * 0.25 + 0 * 0.15 + 40 * 0.10 = 20 + 7.5 + 4 = 31.5
    # 最终评分：int(31.5 / 0.7) = 45
    result = scorer.score(snapshot, [])
    assert result.score == 45
    assert result.stage == "watch"
    assert any("价格处于60日箱体下沿支撑区" in cond for cond in result.triggered_conditions)

def test_ignition_score_none(scorer):
    # 构建完全没有信号的快照
    # close = 10.5, box_low = 9.0 -> close <= box_low * 1.10 (10.5 <= 9.9) is False -> bottom_structure = 0
    snapshot = SectorSnapshot(
        etf_code="512480",
        sector_name="半导体",
        trade_date=date(2026, 6, 15),
        close=10.5, open=10.4, high=10.6, low=10.3,
        volume=800.0, volume_ma60=1000.0, # volume_ratio = 0.8, 阳线 (volume_breakout = 30)
        ma5=9.5, ma10=9.5, ma20=9.6, ma60=9.7, ma200=9.9,
        macd_dif=-0.05, macd_dea=-0.04, macd_bar=-0.02, rsi_14=45.0,
        bias_ma5=0.0, bias_ma20=-1.04, rs_vs_benchmark=0.9,
        rs_trend="falling", # rs_trend = 0
        breadth_up_pct=30.0, # breadth = 30
        breadth_above_ma20_pct=0.0, breadth_new_high_pct=0.0,
        box_high=10.0, box_low=9.0,
        is_near_box_low=False, # bottom_structure = 0
        smp_delta=None
    )
    
    # 权重和：0 * 0.20 + 30 * 0.25 + 0 * 0.15 + 30 * 0.10 = 7.5 + 3 = 10.5
    # 最终评分：int(10.5 / 0.7) = 15
    result = scorer.score(snapshot, [])
    assert result.score == 15
    assert result.stage == "none"

