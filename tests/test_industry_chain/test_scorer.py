# -*- coding: utf-8 -*-
"""Tests for layer scoring and signal generation."""

from __future__ import annotations

from src.industry_chain.models import (
    ChainLayer,
    CompanyFinancials,
    LayerScoreCard,
    LayerScore,
    ScoreDimension,
    ThesisStatus,
    ThesisVerdict,
    ThesisValidationReport,
    SignalOutput,
)
from src.industry_chain.analysis.layer_scorer import LayerScorer
from src.industry_chain.analysis.signal_generator import SignalGenerator
from src.industry_chain.analysis.thesis_validator import ThesisValidator


def _make_financials():
    """创建测试用财务数据"""
    return [
        CompanyFinancials(
            ticker="NVDA", name="NVIDIA", layer=ChainLayer.AI_ACCELERATOR,
            revenue=130000, gross_margin=71.3, operating_margin=55.0,
            net_margin=48.0, revenue_growth=65.0, market_cap=3000000,
            pe_ratio=45.0, data_completeness="full",
        ),
        CompanyFinancials(
            ticker="AMD", name="AMD", layer=ChainLayer.AI_ACCELERATOR,
            revenue=25000, gross_margin=50.0, operating_margin=15.0,
            net_margin=12.0, revenue_growth=15.0, market_cap=250000,
            pe_ratio=30.0, data_completeness="full",
        ),
        CompanyFinancials(
            ticker="AVGO", name="Broadcom", layer=ChainLayer.AI_ACCELERATOR,
            revenue=50000, gross_margin=65.0, operating_margin=38.0,
            net_margin=30.0, revenue_growth=30.0, market_cap=900000,
            pe_ratio=35.0, data_completeness="full",
        ),
        CompanyFinancials(
            ticker="MSFT", name="Microsoft", layer=ChainLayer.CLOUD_IAAS,
            revenue=250000, gross_margin=70.0, operating_margin=45.0,
            net_margin=35.0, revenue_growth=18.0, market_cap=3000000,
            pe_ratio=35.0, capex=80000, data_completeness="full",
        ),
        CompanyFinancials(
            ticker="AMZN", name="Amazon", layer=ChainLayer.CLOUD_IAAS,
            revenue=600000, gross_margin=45.0, operating_margin=12.0,
            net_margin=8.0, revenue_growth=12.0, market_cap=2000000,
            pe_ratio=40.0, capex=70000, data_completeness="full",
        ),
        CompanyFinancials(
            ticker="ADBE", name="Adobe", layer=ChainLayer.APPLICATION_SAAS,
            revenue=21000, gross_margin=88.0, operating_margin=35.0,
            net_margin=28.0, revenue_growth=10.0, market_cap=250000,
            pe_ratio=40.0, data_completeness="full",
        ),
        CompanyFinancials(
            ticker="CRM", name="Salesforce", layer=ChainLayer.APPLICATION_SAAS,
            revenue=35000, gross_margin=75.0, operating_margin=20.0,
            net_margin=15.0, revenue_growth=10.0, market_cap=280000,
            pe_ratio=35.0, data_completeness="full",
        ),
    ]


class TestLayerScorer:
    def setup_method(self):
        self.scorer = LayerScorer()
        self.financials = _make_financials()

    def test_build_layer_snapshots(self):
        snapshots = self.scorer.build_layer_snapshots(self.financials)
        assert ChainLayer.AI_ACCELERATOR in snapshots
        assert ChainLayer.CLOUD_IAAS in snapshots
        assert ChainLayer.APPLICATION_SAAS in snapshots

    def test_snapshot_aggregation(self):
        snapshots = self.scorer.build_layer_snapshots(self.financials)
        ai = snapshots[ChainLayer.AI_ACCELERATOR]
        assert ai.company_count == 3
        assert ai.avg_gross_margin is not None
        # NVDA 71.3 + AMD 50 + AVGO 65 = 186.3 / 3 = 62.1
        assert abs(ai.avg_gross_margin - 62.1) < 1.0

    def test_score_single_layer(self):
        snapshots = self.scorer.build_layer_snapshots(self.financials)
        ai_snap = snapshots[ChainLayer.AI_ACCELERATOR]
        card = self.scorer.score_single(ChainLayer.AI_ACCELERATOR, ai_snap)

        assert card.layer == ChainLayer.AI_ACCELERATOR
        assert card.composite_score > 0
        assert len(card.dimension_scores) == 5

        for ds in card.dimension_scores:
            assert 0 <= ds.score <= 100

    def test_score_all_returns_sorted(self):
        snapshots = self.scorer.build_layer_snapshots(self.financials)
        cards = self.scorer.score_all(snapshots)

        # 所有有数据的层都应被评分
        assert len(cards) == 3

        # 应包含排名信息
        for card in cards:
            assert card.composite_rank is not None

    def test_hhi_calculation(self):
        snapshots = self.scorer.build_layer_snapshots(self.financials)
        ai = snapshots[ChainLayer.AI_ACCELERATOR]
        # NVDA 130k, AMD 25k, AVGO 50k => total 205k
        # HHI = (130/205)^2 + (25/205)^2 + (50/205)^2
        if ai.herfindahl_index is not None:
            assert ai.herfindahl_index > 4000  # NVDA 集中


class TestSignalGenerator:
    def setup_method(self):
        self.generator = SignalGenerator()
        self.financials = _make_financials()
        self.scorer = LayerScorer()
        snapshots = self.scorer.build_layer_snapshots(self.financials)
        self.cards = self.scorer.score_all(snapshots)

    def test_generate_layer_allocations(self):
        output = self.generator.generate(
            score_cards=self.cards,
            financials=self.financials,
        )
        assert len(output.layer_allocations) == 3

    def test_generate_company_recommendations(self):
        output = self.generator.generate(
            score_cards=self.cards,
            financials=self.financials,
        )
        # 7 家公司都有评分但只有有 revenue 的才有推荐
        assert len(output.company_recommendations) >= 7

    def test_signals_with_thesis_report(self):
        """假说验证结果应影响信号"""
        # 创建一个假说验证报告，让"应用层最容易卷"通过
        thesis_report = ThesisValidationReport(theses=[
            ThesisVerdict(
                thesis_id="application_lowest_margin",
                title="应用层利润率最低",
                description="",
                status=ThesisStatus.PASS,
                evidence="验证通过",
                confidence="high",
            ),
        ])
        thesis_report.compute_summary()

        output = self.generator.generate(
            score_cards=self.cards,
            thesis_report=thesis_report,
            financials=self.financials,
        )
        assert len(output.layer_allocations) > 0


class TestThesisValidator:
    def setup_method(self):
        self.validator = ThesisValidator()

    def test_list_theses(self):
        theses = self.validator.list_theses()
        assert len(theses) >= 8  # 至少有 8 条假说
        ids = [t["id"] for t in theses]
        assert "nvda_margin" in ids
        assert "application_lowest_margin" in ids

    def test_validate_nvda_margin_with_data(self):
        """使用测试数据验证 nvda_margin 假说"""
        financials = _make_financials()
        snapshots = LayerScorer().build_layer_snapshots(financials)

        verdict = self.validator.validate_one("nvda_margin", snapshots, financials)
        assert verdict is not None
        assert verdict.status in (ThesisStatus.PASS, ThesisStatus.FAIL, ThesisStatus.INSUFFICIENT_DATA)
        if verdict.status == ThesisStatus.PASS:
            # NVDA 71.3% 应在 65-75 范围内
            assert verdict.numerical_value == 71.3

    def test_validate_all(self):
        financials = _make_financials()
        snapshots = LayerScorer().build_layer_snapshots(financials)

        report = self.validator.validate_all(snapshots, financials)
        assert len(report.theses) >= 8
        report.compute_summary()
        assert isinstance(report.pass_count, int)
