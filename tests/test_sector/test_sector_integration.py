# -*- coding: utf-8 -*-
import pytest
from datetime import date
from unittest.mock import patch, MagicMock
import pandas as pd

from src.storage import DatabaseManager, SectorETFPool, SectorInflectionState
from src.services.sector_inflection_service import SectorInflectionService
from src.sector.sector_data import SectorSnapshot
from src.sector.market_regime import MarketRegime
from src.sector.state_machine import SectorState

@pytest.fixture
def in_memory_db():
    DatabaseManager.reset_instance()
    db = DatabaseManager(db_url="sqlite:///:memory:")
    yield db
    DatabaseManager.reset_instance()

@pytest.fixture
def mock_benchmark_df():
    # 构造一个 300 天的沪深300指数数据，最新收盘价为 3500，MA200 为 3300，大盘为 risk_on
    dates = pd.date_range(start="2025-01-01", periods=300).date
    # 模拟上涨价格
    closes = [float(3000 + i * 2) for i in range(300)]
    df = pd.DataFrame({
        "date": dates,
        "close": closes
    })
    df['ma200'] = df['close'].rolling(window=200, min_periods=1).mean()
    return df

@pytest.fixture
def mock_benchmark_df_risk_off():
    # 构造一个 300 天的沪深300指数数据，最新收盘价为 2500，MA200 为 3300，大盘为 risk_off
    dates = pd.date_range(start="2025-01-01", periods=300).date
    # 模拟下跌价格
    closes = [float(3500 - i * 3) for i in range(300)]
    df = pd.DataFrame({
        "date": dates,
        "close": closes
    })
    df['ma200'] = df['close'].rolling(window=200, min_periods=1).mean()
    return df

def test_sector_scan_bootstrap_and_integration(in_memory_db, mock_benchmark_df):
    # Mock SectorDataCollector.get_benchmark_data and collect_snapshot
    with patch("src.services.sector_inflection_service.get_db", return_value=in_memory_db), \
         patch("src.services.sector_inflection_service.NotificationService") as MockNotifier, \
         patch("src.sector.sector_data.SectorDataCollector.get_benchmark_data", return_value=mock_benchmark_df) as mock_get_bench, \
         patch("src.sector.sector_data.SectorDataCollector.collect_snapshot") as mock_collect:
        
        # 1. 模拟 collect_snapshot 返回特定的 SectorSnapshot
        # 我们只模拟池子里第一个 ETF "512480" (半导体)
        mock_snapshot = SectorSnapshot(
            etf_code="512480",
            sector_name="半导体ETF",
            trade_date=date(2026, 6, 15),
            close=10.0, open=9.5, high=10.5, low=9.4,
            volume=1600.0, volume_ma60=1000.0,
            ma5=9.8, ma10=9.7, ma20=9.6, ma60=9.5, ma200=9.0,
            macd_dif=0.1, macd_dea=0.08, macd_bar=0.04, rsi_14=60.0,
            bias_ma5=2.0, bias_ma20=4.0, rs_vs_benchmark=1.2,
            rs_trend="rising",
            breadth_up_pct=70.0,
            breadth_above_ma20_pct=0.0,
            breadth_new_high_pct=0.0,
            box_high=10.0, box_low=9.0,
            is_near_box_low=False,
            smp_delta=None
        )
        # 为所有其他的返回 None，保证测试简洁
        def collect_side_effect(etf_code, sector_name, index_code, benchmark_df, trade_date=None):
            if etf_code == "512480":
                # 调整日期为评估日期
                mock_snapshot.trade_date = trade_date or date(2026, 6, 15)
                return mock_snapshot
            return None
        
        mock_collect.side_effect = collect_side_effect
        
        # 实例化服务
        service = SectorInflectionService()
        
        # 第一次调用 get_active_sector_etfs 应该触发 Bootstrap，预置 11 个 ETF 到 DB 中 (8个默认+3个避险)
        etfs = in_memory_db.get_active_sector_etfs()
        assert len(etfs) == 11
        assert any(e.etf_code == "512480" for e in etfs)
        
        # 执行扫描
        scan_date = date(2026, 6, 15)
        result = service.run_daily_scan(trade_date=scan_date, force=True)
        
        assert result["status"] == "success"
        assert result["market_regime"] == "risk_on"
        
        # 验证 512480 的状态转移
        # 初始状态为空，即 SCANNING
        # 评分 67 -> stage confirmed -> transition to HOLDING
        results_map = {r["etf_code"]: r for r in result["results"]}
        assert "512480" in results_map
        assert results_map["512480"]["state"] == SectorState.HOLDING.value
        assert results_map["512480"]["prev_state"] == SectorState.SCANNING.value
        
        # 验证数据写入 DB
        history = in_memory_db.get_sector_inflection_history("512480", limit=10)
        assert len(history) == 1
        assert history[0].state == SectorState.HOLDING.value
        assert history[0].trade_date == scan_date
        
        # 验证通知被调用
        assert MockNotifier.return_value.send_sector_inflection_report.called

def test_sector_scan_risk_off(in_memory_db, mock_benchmark_df_risk_off):
    # 测试大盘风险关掉 (Risk OFF) 时的避险清仓逻辑
    with patch("src.services.sector_inflection_service.get_db", return_value=in_memory_db), \
         patch("src.services.sector_inflection_service.NotificationService") as MockNotifier, \
         patch("src.sector.sector_data.SectorDataCollector.get_benchmark_data", return_value=mock_benchmark_df_risk_off) as mock_get_bench, \
         patch("src.sector.sector_data.SectorDataCollector.collect_snapshot") as mock_collect:
        
        # 预先向数据库写入前一天的 HOLDING 状态
        prev_date = date(2026, 6, 14)
        in_memory_db.get_active_sector_etfs() # Bootstrap
        
        in_memory_db.save_sector_inflection_state(
            etf_code="512480",
            sector_name="半导体ETF",
            trade_date=prev_date,
            ignition_score=70,
            distribution_score=0,
            ignition_details={},
            distribution_details={},
            state=SectorState.HOLDING.value,
            prev_state=SectorState.SCANNING.value,
            state_reason="买入确认",
            state_entered_date=prev_date,
            market_regime="risk_on"
        )
        
        # 模拟当日快照 (2026-06-15)
        mock_snapshot = SectorSnapshot(
            etf_code="512480", sector_name="半导体ETF",
            trade_date=date(2026, 6, 15),
            close=9.8, open=9.8, high=9.9, low=9.7, volume=1000.0, volume_ma60=1000.0,
            ma5=9.8, ma10=9.8, ma20=9.8, ma60=9.8, ma200=9.8,
            macd_dif=0.0, macd_dea=0.0, macd_bar=0.0, rsi_14=50.0,
            bias_ma5=0.0, bias_ma20=0.0, rs_vs_benchmark=1.0, rs_trend="falling",
            breadth_up_pct=50.0, breadth_above_ma20_pct=0.0, breadth_new_high_pct=0.0,
            box_high=10.0, box_low=9.0, is_near_box_low=False, smp_delta=None
        )
        
        mock_collect.return_value = mock_snapshot
        
        # 执行扫描
        service = SectorInflectionService()
        result = service.run_daily_scan(trade_date=date(2026, 6, 15), force=True)
        
        assert result["market_regime"] == "risk_off"
        
        # 验证状态从 HOLDING 强制流转为 EXITED
        results_map = {r["etf_code"]: r for r in result["results"]}
        assert results_map["512480"]["state"] == SectorState.EXITED.value
        assert results_map["512480"]["prev_state"] == SectorState.HOLDING.value
        
        # 运行后先保存为 EXITED，然后自动归零重置保存为 SCANNING
        # 由于 unique_constraint，在同一天 (6-15) 两次写入最终覆盖，状态为 SCANNING
        # 所以最终数据库里应该有两条记录：6-14 HOLDING, 6-15 SCANNING (自动重置)
        history = in_memory_db.get_sector_inflection_history("512480", limit=10)
        assert len(history) == 2 # 6-14 HOLDING, 6-15 SCANNING
        assert history[0].state == SectorState.SCANNING.value
        assert history[1].state == SectorState.HOLDING.value


def test_get_dashboard(in_memory_db):
    # 测试 get_dashboard 数据获取
    with patch("src.services.sector_inflection_service.get_db", return_value=in_memory_db):
        service = SectorInflectionService()
        
        # 写入几条状态
        scan_date = date(2026, 6, 15)
        in_memory_db.save_sector_inflection_state(
            etf_code="512480", sector_name="半导体ETF", trade_date=scan_date,
            ignition_score=60, distribution_score=10, ignition_details={}, distribution_details={},
            state=SectorState.HOLDING.value, prev_state=SectorState.SCANNING.value,
            state_reason="test", state_entered_date=scan_date, market_regime="risk_on"
        )
        
        dashboard = service.get_dashboard(trade_date=scan_date)
        assert len(dashboard) == 1
        assert dashboard[0]["etf_code"] == "512480"
        assert dashboard[0]["state"] == SectorState.HOLDING.value
        assert dashboard[0]["ignition_score"] == 60
