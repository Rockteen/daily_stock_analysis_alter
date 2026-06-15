# -*- coding: utf-8 -*-
import pytest
import pandas as pd
from datetime import date
from src.sector.market_regime import MarketRegimeSwitch, MarketRegime

def test_evaluate_empty_dataframe():
    switch = MarketRegimeSwitch(benchmark_code="000300")
    regime = switch.evaluate(pd.DataFrame())
    assert regime.status == "risk_on"
    assert regime.benchmark_close == 0.0
    assert regime.benchmark_ma200 == 0.0
    assert regime.margin_pct == 0.0

def test_evaluate_risk_on():
    switch = MarketRegimeSwitch(benchmark_code="000300")
    # 创建一个有201行的数据框，使 ma200 能正常计算且收盘价大于 ma200
    dates = pd.date_range(start="2026-01-01", periods=210).date
    # 模拟递增的价格，收盘价会一直大于均价
    closes = [float(i) for i in range(100, 310)]
    df = pd.DataFrame({
        "date": dates,
        "close": closes
    })
    
    # 此时最新的收盘价是 309，MA200 应该在 209 左右，close >= ma200
    regime = switch.evaluate(df)
    assert regime.status == "risk_on"
    assert regime.benchmark_close == 309.0
    assert regime.benchmark_ma200 > 0
    assert regime.benchmark_close >= regime.benchmark_ma200
    assert regime.margin_pct > 0

def test_evaluate_risk_off():
    switch = MarketRegimeSwitch(benchmark_code="000300")
    dates = pd.date_range(start="2026-01-01", periods=210).date
    # 模拟递减的价格，收盘价会低于均价
    closes = [float(310 - i) for i in range(210)]
    df = pd.DataFrame({
        "date": dates,
        "close": closes
    })
    
    regime = switch.evaluate(df)
    assert regime.status == "risk_off"
    assert regime.benchmark_close == 101.0
    assert regime.benchmark_ma200 > 101.0
    assert regime.margin_pct < 0

def test_evaluate_exact_date():
    switch = MarketRegimeSwitch(benchmark_code="000300")
    dates = pd.date_range(start="2026-01-01", periods=10).date
    closes = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0]
    df = pd.DataFrame({
        "date": dates,
        "close": closes
    })
    
    # 获取中间某天的数据，例如 2026-01-05 (第5个，索引4，价格14.0)
    target_date = dates[4]
    regime = switch.evaluate(df, trade_date=target_date)
    assert regime.benchmark_close == 14.0
    # 由于 min_periods=1，均值计算是前5天的均值：(10+11+12+13+14)/5 = 12.0
    assert regime.benchmark_ma200 == 12.0
    assert regime.status == "risk_on"

def test_evaluate_closest_past_date():
    switch = MarketRegimeSwitch(benchmark_code="000300")
    # 间隔一天的日期
    dates = [
        date(2026, 1, 1),
        date(2026, 1, 3),
        date(2026, 1, 5)
    ]
    closes = [10.0, 12.0, 14.0]
    df = pd.DataFrame({
        "date": dates,
        "close": closes
    })
    
    # 评估 2026-01-04 (介于 1-03 和 1-05 之间)
    # 应找到 2026-01-03 的记录，价格为 12.0
    target_date = date(2026, 1, 4)
    regime = switch.evaluate(df, trade_date=target_date)
    assert regime.benchmark_close == 12.0
    # 2026-01-03 时的 MA200 应为 (10+12)/2 = 11.0
    assert regime.benchmark_ma200 == 11.0
    assert regime.status == "risk_on"
