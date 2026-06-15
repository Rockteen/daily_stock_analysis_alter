# -*- coding: utf-8 -*-
import pytest
from src.sector.state_machine import SectorStateMachine, SectorState
from src.sector.market_regime import MarketRegime
from src.sector.ignition_scorer import IgnitionResult
from src.sector.distribution_scorer import DistributionResult

@pytest.fixture
def state_machine():
    return SectorStateMachine(lurk_timeout_days=30)

@pytest.fixture
def risk_on_regime():
    return MarketRegime(status="risk_on", benchmark_code="000300", benchmark_close=3000.0, benchmark_ma200=2800.0, margin_pct=7.14)

@pytest.fixture
def risk_off_regime():
    return MarketRegime(status="risk_off", benchmark_code="000300", benchmark_close=2600.0, benchmark_ma200=2800.0, margin_pct=-7.14)

@pytest.fixture
def default_ignition():
    return IgnitionResult(score=0, dimension_scores={}, triggered_conditions=[], stage="none")

@pytest.fixture
def default_distribution():
    return DistributionResult(score=0, dimension_scores={}, triggered_conditions=[], stage="none")

def test_risk_off_clears_holdings(state_machine, risk_off_regime, default_ignition, default_distribution):
    # 如果大盘风险 OFF，HOLDING -> EXITED
    state, reason = state_machine.transition(
        current_state=SectorState.HOLDING,
        ignition=default_ignition,
        distribution=default_distribution,
        regime=risk_off_regime,
        days_in_state=5
    )
    assert state == SectorState.EXITED
    assert "大盘总开关风险 OFF" in reason

    # 如果大盘风险 OFF，ALERT -> EXITED
    state, reason = state_machine.transition(
        current_state=SectorState.ALERT,
        ignition=default_ignition,
        distribution=default_distribution,
        regime=risk_off_regime,
        days_in_state=5
    )
    assert state == SectorState.EXITED
    assert "大盘总开关风险 OFF" in reason

    # 如果大盘风险 OFF，LURKING -> SCANNING
    state, reason = state_machine.transition(
        current_state=SectorState.LURKING,
        ignition=default_ignition,
        distribution=default_distribution,
        regime=risk_off_regime,
        days_in_state=5
    )
    assert state == SectorState.SCANNING
    assert "取消潜伏观察" in reason

def test_scanning_transitions(state_machine, risk_on_regime, default_distribution):
    # SCANNING -> LURKING on watch stage
    ignition = IgnitionResult(score=45, dimension_scores={}, triggered_conditions=[], stage="watch")
    state, reason = state_machine.transition(
        current_state=SectorState.SCANNING,
        ignition=ignition,
        distribution=default_distribution,
        regime=risk_on_regime,
        days_in_state=1
    )
    assert state == SectorState.LURKING
    assert "进入潜伏期" in reason

    # SCANNING -> HOLDING on confirmed stage
    ignition = IgnitionResult(score=70, dimension_scores={}, triggered_conditions=[], stage="confirmed")
    state, reason = state_machine.transition(
        current_state=SectorState.SCANNING,
        ignition=ignition,
        distribution=default_distribution,
        regime=risk_on_regime,
        days_in_state=1
    )
    assert state == SectorState.HOLDING
    assert "直接进入持有期" in reason

def test_lurking_transitions(state_machine, risk_on_regime, default_distribution):
    # LURKING -> HOLDING on confirmed
    ignition = IgnitionResult(score=70, dimension_scores={}, triggered_conditions=[], stage="confirmed")
    state, reason = state_machine.transition(
        current_state=SectorState.LURKING,
        ignition=ignition,
        distribution=default_distribution,
        regime=risk_on_regime,
        days_in_state=5
    )
    assert state == SectorState.HOLDING
    assert "买入信号确认" in reason

    # LURKING -> SCANNING on timeout
    ignition = IgnitionResult(score=45, dimension_scores={}, triggered_conditions=[], stage="watch")
    state, reason = state_machine.transition(
        current_state=SectorState.LURKING,
        ignition=ignition,
        distribution=default_distribution,
        regime=risk_on_regime,
        days_in_state=30 # 达到超时天数
    )
    assert state == SectorState.SCANNING
    assert "潜伏期超时" in reason

    # LURKING -> SCANNING on structure broken
    ignition = IgnitionResult(score=25, dimension_scores={}, triggered_conditions=[], stage="none")
    state, reason = state_machine.transition(
        current_state=SectorState.LURKING,
        ignition=ignition,
        distribution=default_distribution,
        regime=risk_on_regime,
        days_in_state=5
    )
    assert state == SectorState.SCANNING
    assert "底部结构遭到破坏" in reason

def test_holding_transitions(state_machine, risk_on_regime, default_ignition):
    # HOLDING -> ALERT on alert stage
    distribution = DistributionResult(score=60, dimension_scores={}, triggered_conditions=[], stage="alert")
    state, reason = state_machine.transition(
        current_state=SectorState.HOLDING,
        ignition=default_ignition,
        distribution=distribution,
        regime=risk_on_regime,
        days_in_state=10
    )
    assert state == SectorState.ALERT
    assert "见顶评分预警" in reason

    # HOLDING -> EXITED on exit stage
    distribution = DistributionResult(score=80, dimension_scores={}, triggered_conditions=[], stage="exit")
    state, reason = state_machine.transition(
        current_state=SectorState.HOLDING,
        ignition=default_ignition,
        distribution=distribution,
        regime=risk_on_regime,
        days_in_state=10
    )
    assert state == SectorState.EXITED
    assert "价格发生破位" in reason

def test_alert_transitions(state_machine, risk_on_regime, default_ignition):
    # ALERT -> EXITED on exit stage
    distribution = DistributionResult(score=80, dimension_scores={}, triggered_conditions=[], stage="exit")
    state, reason = state_machine.transition(
        current_state=SectorState.ALERT,
        ignition=default_ignition,
        distribution=distribution,
        regime=risk_on_regime,
        days_in_state=2
    )
    assert state == SectorState.EXITED
    assert "关键支撑位跌破" in reason

    # ALERT -> HOLDING on none stage (alert cleared)
    distribution = DistributionResult(score=20, dimension_scores={}, triggered_conditions=[], stage="none")
    state, reason = state_machine.transition(
        current_state=SectorState.ALERT,
        ignition=default_ignition,
        distribution=distribution,
        regime=risk_on_regime,
        days_in_state=2
    )
    assert state == SectorState.HOLDING
    assert "警报解除" in reason

def test_exited_transitions(state_machine, risk_on_regime, default_ignition, default_distribution):
    # EXITED always transitions to SCANNING
    state, reason = state_machine.transition(
        current_state=SectorState.EXITED,
        ignition=default_ignition,
        distribution=default_distribution,
        regime=risk_on_regime,
        days_in_state=1
    )
    assert state == SectorState.SCANNING
    assert "自动退回扫描状态" in reason
