# -*- coding: utf-8 -*-
"""Tests for industry_chain data models and registry."""

from __future__ import annotations

from src.industry_chain.models import ChainLayer, Region, ChainCompany, CompanyFinancials
from src.industry_chain.registry import (
    get_all_companies,
    get_companies_by_layer,
    get_company,
    get_layers,
    count_companies,
    get_core_players,
    get_tickers,
)


class TestChainLayer:
    def test_sort_order(self):
        """链层应按上下游顺序正确排序"""
        layers = list(ChainLayer)
        orders = [l.sort_order for l in layers]
        assert orders == sorted(orders), "sort_order should be sequential 1-8"

    def test_display_name_not_empty(self):
        """所有链层应有中文名"""
        for layer in ChainLayer:
            assert len(layer.display_name) > 0, f"{layer} missing display_name"

    def test_eight_layers(self):
        """应有且仅有 8 层"""
        assert len(list(ChainLayer)) == 8


class TestRegion:
    def test_display(self):
        from src.industry_chain.models import region_display
        assert region_display(Region.US) == "美国"
        assert region_display(Region.CN) == "中国"
        assert region_display(Region.NL) == "荷兰"


class TestRegistry:
    def test_count(self):
        """注册表应有 50 家以上公司"""
        assert count_companies() >= 50, f"Got {count_companies()}, expected >= 50"

    def test_get_all_companies(self):
        companies = get_all_companies()
        assert len(companies) == count_companies()

    def test_get_company(self):
        nvda = get_company("NVDA")
        assert nvda is not None
        assert nvda.name == "英伟达"
        assert nvda.layer == ChainLayer.AI_ACCELERATOR
        assert nvda.region == Region.US

    def test_get_company_not_found(self):
        assert get_company("INVALID_TICKER") is None

    def test_get_layers_in_order(self):
        layers = get_layers()
        assert len(layers) == 8
        # 第一层是半导体设备，最后一层是应用
        assert layers[0] == ChainLayer.SEMI_EQUIPMENT
        assert layers[-1] == ChainLayer.APPLICATION_SAAS

    def test_each_layer_has_companies(self):
        """每层至少有一家公司"""
        for layer in ChainLayer:
            companies = get_companies_by_layer(layer)
            assert len(companies) >= 1, f"{layer.display_name} has no companies"

    def test_core_players(self):
        """AI 加速器层应有核心玩家"""
        cores = get_core_players(ChainLayer.AI_ACCELERATOR)
        assert any(c.ticker_yf == "NVDA" for c in cores)
        assert any(c.ticker_yf == "AMD" for c in cores)
        assert any(c.ticker_yf == "AVGO" for c in cores)

    def test_tickers(self):
        """ticker 列表不应为空，NVDA 应在其中"""
        tickers = get_tickers()
        assert "NVDA" in tickers
        assert "TSM" in tickers
        assert "AVGO" in tickers


class TestCompanyFinancials:
    def test_defaults(self):
        fin = CompanyFinancials(ticker="NVDA", name="NVIDIA", layer=ChainLayer.AI_ACCELERATOR)
        assert fin.ticker == "NVDA"
        assert fin.revenue is None
        assert fin.data_completeness == "partial"
        assert fin.errors == []

    def test_with_values(self):
        fin = CompanyFinancials(
            ticker="NVDA", name="NVIDIA", layer=ChainLayer.AI_ACCELERATOR,
            revenue=100000, gross_margin=71.3, operating_margin=55.0,
        )
        assert fin.gross_margin == 71.3
        assert fin.revenue == 100000
