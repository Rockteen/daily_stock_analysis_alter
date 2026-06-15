# -*- coding: utf-8 -*-
"""
板块拐点捕捉策略服务层
"""

import logging
from datetime import date, datetime
from typing import Dict, Any, List, Optional, Tuple
import json

from src.storage import get_db, SectorETFPool, SectorInflectionState
from src.sector.sector_data import SectorDataCollector, SectorSnapshot
from src.sector.market_regime import MarketRegimeSwitch, MarketRegime
from src.sector.ignition_scorer import IgnitionScorer, IgnitionResult
from src.sector.distribution_scorer import DistributionScorer, DistributionResult
from src.sector.state_machine import SectorStateMachine, SectorState
from src.notification import NotificationService

logger = logging.getLogger(__name__)

class SectorInflectionService:
    """
    板块拐点主服务，负责日频扫描、编排计算流程、状态机推进与通知推送
    """
    def __init__(self):
        self.db = get_db()
        self.data_collector = SectorDataCollector()
        self.regime_switch = MarketRegimeSwitch()
        self.ignition_scorer = IgnitionScorer()
        self.distribution_scorer = DistributionScorer()
        self.state_machine = SectorStateMachine()
        self.notifier = NotificationService()

    def get_state_before(self, etf_code: str, before_date: date) -> Optional[SectorInflectionState]:
        """
        获取指定日期前该板块的最新状态记录
        """
        with self.db.get_session() as session:
            from sqlalchemy import desc, and_
            return session.query(SectorInflectionState).filter(
                and_(
                    SectorInflectionState.etf_code == etf_code,
                    SectorInflectionState.trade_date < before_date
                )
            ).order_by(desc(SectorInflectionState.trade_date)).first()

    def run_daily_scan(self, trade_date: Optional[date] = None, force: bool = False) -> Dict[str, Any]:
        """
        运行日频板块拐点扫描
        """
        if trade_date is None:
            trade_date = date.today()
            
        logger.info(f"开始执行板块拐点扫描，目标交易日: {trade_date}")

        # 1. 获取所有激活的板块 ETF
        active_etfs = self.db.get_active_sector_etfs()
        if not active_etfs:
            logger.warning("激活的板块 ETF 池为空，无法执行扫描")
            return {"status": "skipped", "reason": "No active ETFs in pool"}

        # 2. 获取大盘基准日 K 线，并评估大盘总开关
        # 大盘基准代码从配置获取，默认 000300
        from src.config import get_config
        config = get_config()
        benchmark_code = getattr(config, 'sector_scan_benchmark', '000300')
        
        benchmark_df = self.data_collector.get_benchmark_data(benchmark_code, days=300)
        if benchmark_df.empty:
            logger.error("获取大盘基准 K 线数据失败，终止扫描")
            return {"status": "failed", "reason": "Failed to load benchmark data"}

        regime = self.regime_switch.evaluate(benchmark_df, trade_date=trade_date)
        
        # 实际收集到的 snapshot 和转移记录
        snapshots: List[SectorSnapshot] = []
        transitions: List[Tuple[str, str, str, str, int, int]] = [] # (ETF名称, 代码, 旧状态, 新状态, 启动分, 见顶分)
        all_results = []

        # 3. 遍历各板块，计算评分并驱动状态机
        for etf in active_etfs:
            logger.info(f"正在分析板块: {etf.sector_name}({etf.etf_code})")
            
            # 获取历史记录用于指标和背离计算
            history_records = self.db.get_sector_inflection_history(etf.etf_code, limit=60)
            # 转换为 SectorSnapshot
            history_snapshots: List[SectorSnapshot] = []
            for record in reversed(history_records):
                # 转换简单的历史对象
                try:
                    ign_details = json.loads(record.ignition_details) if record.ignition_details else {}
                    dist_details = json.loads(record.distribution_details) if record.distribution_details else {}
                except Exception:
                    ign_details, dist_details = {}, {}
                
                # 构造一个极简快照以便背离计算
                snap = SectorSnapshot(
                    etf_code=record.etf_code,
                    sector_name=record.sector_name,
                    trade_date=record.trade_date,
                    close=0.0, open=0.0, high=0.0, low=0.0, volume=0.0, volume_ma60=0.0,
                    ma5=0.0, ma10=0.0, ma20=0.0, ma60=0.0, ma200=0.0,
                    macd_dif=ign_details.get("macd_dif", 0.0) or dist_details.get("macd_dif", 0.0) or 0.0,
                    macd_dea=0.0, macd_bar=0.0,
                    rsi_14=ign_details.get("rsi_14", 50.0) or dist_details.get("rsi_14", 50.0) or 50.0,
                    bias_ma5=0.0, bias_ma20=0.0, rs_vs_benchmark=0.0, rs_trend="falling",
                    breadth_up_pct=0.0, breadth_above_ma20_pct=0.0, breadth_new_high_pct=0.0,
                    box_high=0.0, box_low=0.0, is_near_box_low=False
                )
                history_snapshots.append(snap)

            # 获取当前板块快照
            snapshot = self.data_collector.collect_snapshot(
                etf_code=etf.etf_code,
                sector_name=etf.sector_name,
                index_code=etf.benchmark_index,
                benchmark_df=benchmark_df,
                trade_date=trade_date
            )
            
            if snapshot is None:
                logger.warning(f"无法获取板块 {etf.sector_name}({etf.etf_code}) 的最新行情快照，跳过")
                continue

            # 评估评分
            ignition = self.ignition_scorer.score(snapshot, history_snapshots)
            distribution = self.distribution_scorer.score(snapshot, history_snapshots)

            # 读取前一状态
            prev_record = self.get_state_before(etf.etf_code, snapshot.trade_date)
            
            if prev_record:
                prev_state = SectorState(prev_record.state)
                state_entered_date = prev_record.state_entered_date or prev_record.trade_date
                # 状态持续天数
                days_in_state = (snapshot.trade_date - state_entered_date).days + 1
            else:
                prev_state = SectorState.SCANNING
                state_entered_date = snapshot.trade_date
                days_in_state = 1

            # 状态机转换
            new_state, transition_reason = self.state_machine.transition(
                current_state=prev_state,
                ignition=ignition,
                distribution=distribution,
                regime=regime,
                days_in_state=days_in_state
            )

            # 状态进入日期更新
            new_state_entered_date = state_entered_date
            if new_state != prev_state:
                new_state_entered_date = snapshot.trade_date
                transitions.append((etf.sector_name, etf.etf_code, prev_state.value, new_state.value, ignition.score, distribution.score))
                logger.info(f"板块 {etf.sector_name}({etf.etf_code}) 状态转移: {prev_state.value} -> {new_state.value} (原因: {transition_reason})")

            # 保存到数据库
            self.db.save_sector_inflection_state(
                etf_code=etf.etf_code,
                sector_name=etf.sector_name,
                trade_date=snapshot.trade_date,
                ignition_score=ignition.score,
                distribution_score=distribution.score,
                ignition_details=ignition.dimension_scores,
                distribution_details=distribution.dimension_scores,
                state=new_state.value,
                prev_state=prev_state.value if prev_record else None,
                state_reason=transition_reason,
                state_entered_date=new_state_entered_date,
                market_regime=regime.status
            )

            all_results.append({
                "etf_code": etf.etf_code,
                "sector_name": etf.sector_name,
                "prev_state": prev_state.value,
                "state": new_state.value,
                "reason": transition_reason,
                "ignition_score": ignition.score,
                "distribution_score": distribution.score
            })

            # 如果状态是 EXITED 且转移了，那么本轮扫描后自动流转回 SCANNING (中间态自动清除)
            if new_state == SectorState.EXITED:
                self.db.save_sector_inflection_state(
                    etf_code=etf.etf_code,
                    sector_name=etf.sector_name,
                    trade_date=snapshot.trade_date,
                    ignition_score=ignition.score,
                    distribution_score=distribution.score,
                    ignition_details=ignition.dimension_scores,
                    distribution_details=distribution.dimension_scores,
                    state=SectorState.SCANNING.value,
                    prev_state=SectorState.EXITED.value,
                    state_reason="自动重置为扫描状态",
                    state_entered_date=snapshot.trade_date,
                    market_regime=regime.status
                )

        # 4. 推送通知日报
        if getattr(config, 'sector_scan_notify', True) and (transitions or force):
            self.push_notification(regime, all_results, transitions, trade_date)

        return {
            "status": "success",
            "trade_date": str(trade_date),
            "market_regime": regime.status,
            "transitions_count": len(transitions),
            "results": all_results
        }

    def push_notification(
        self, 
        regime: MarketRegime, 
        all_results: List[Dict[str, Any]], 
        transitions: List[Tuple[str, str, str, str, int, int]],
        trade_date: date
    ) -> None:
        """
        组装板块拐点报告并推送通知
        """
        logger.info("发送板块拐点扫描通知...")
        self.notifier.send_sector_inflection_report(
            regime_status=regime.status,
            transitions=transitions,
            all_results=all_results,
            trade_date=trade_date
        )

    def get_dashboard(self, trade_date: Optional[date] = None) -> List[Dict[str, Any]]:
        """
        获取板块最新的分析看板数据
        """
        if trade_date is None:
            # 找到最新一个记录的交易日
            with self.db.get_session() as session:
                from sqlalchemy import desc
                latest_record = session.query(SectorInflectionState).order_by(
                    desc(SectorInflectionState.trade_date)
                ).first()
                if latest_record:
                    trade_date = latest_record.trade_date
                else:
                    trade_date = date.today()

        with self.db.get_session() as session:
            records = session.query(SectorInflectionState).filter(
                SectorInflectionState.trade_date == trade_date
            ).all()

            results = []
            for r in records:
                try:
                    ign_details = json.loads(r.ignition_details) if r.ignition_details else {}
                    dist_details = json.loads(r.distribution_details) if r.distribution_details else {}
                except Exception:
                    ign_details, dist_details = {}, {}

                results.append({
                    "etf_code": r.etf_code,
                    "sector_name": r.sector_name,
                    "trade_date": str(r.trade_date),
                    "ignition_score": r.ignition_score,
                    "distribution_score": r.distribution_score,
                    "state": r.state,
                    "prev_state": r.prev_state,
                    "state_reason": r.state_reason,
                    "state_entered_date": str(r.state_entered_date) if r.state_entered_date else None,
                    "market_regime": r.market_regime,
                    "ignition_details": ign_details,
                    "distribution_details": dist_details
                })
            return results
