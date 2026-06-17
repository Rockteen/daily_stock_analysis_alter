# -*- coding: utf-8 -*-
"""
AI 产业链财务数据采集器

从 yfinance 获取注册公司的财务数据，输出 `CompanyFinancials` 结构。
支持全量扫描和单公司刷新，缓存降级以避免 API 限流。

复用 `data_provider/yfinance_fetcher.py` 的 yfinance 使用模式。
"""

from __future__ import annotations

import json
import logging
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.industry_chain.models import ChainCompany, ChainLayer, CompanyFinancials
from src.industry_chain.registry import get_all_companies

logger = logging.getLogger(__name__)

# 缓存目录
CACHE_DIR = Path(os.path.dirname(__file__)).parent.parent.parent / "data" / "cache" / "industry_chain"

# 财务指标键名
_INCOME_REVENUE_KEYS = ("Total Revenue", "TotalRevenue", "Revenue")
_INCOME_GROSS_PROFIT_KEYS = ("Gross Profit", "GrossProfit")
_INCOME_OP_INCOME_KEYS = ("Operating Income", "OperatingIncome", "EBIT")
_INCOME_NET_INCOME_KEYS = (
    "Net Income Common Stockholders",
    "Net Income From Continuing Operation Net Minority Interest",
    "Net Income",
    "NetIncome",
)
_CASHFLOW_CAPEX_KEYS = (
    "Capital Expenditure",
    "CapitalExpenditure",
    "Purchase of Property, Plant and Equipment",
    "PurchaseOfPPE",
)
_CASHFLOW_FCF_KEYS = (
    "Free Cash Flow",
    "FreeCashFlow",
)


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    if result != result:
        return None
    return result


def _pick_row(df, keys) -> Any:
    """从 yfinance 财务报表 DataFrame 中按可能的键名取值"""
    if df is None or df.empty:
        return None
    for key in keys:
        if key in df.index:
            try:
                return df.loc[key]
            except KeyError:
                continue
    return None


def _latest_value(row) -> Optional[float]:
    """取 yfinance 报表数据的最新一期值"""
    if row is None or hasattr(row, "empty") and row.empty:
        return None
    try:
        return _safe_float(row.iloc[0])
    except (IndexError, TypeError):
        return None


def _yoy_growth(row) -> Optional[float]:
    """计算同比增速（需要至少 5 期数据：4 期前同比）"""
    if row is None or hasattr(row, "empty") and row.empty or len(row) < 5:
        return None
    latest = _safe_float(row.iloc[0])
    prev = _safe_float(row.iloc[4])
    if latest is None or prev in (None, 0):
        return None
    return round((latest - prev) / abs(prev) * 100.0, 2)


class ChainFinancialFetcher:
    """AI 产业链财务数据采集器

    用法:
        fetcher = ChainFinancialFetcher()
        snapshot = fetcher.full_snapshot()     # 全量扫描
        fin = fetcher.company_update("NVDA")   # 单公司更新
    """

    def __init__(self, use_cache: bool = True, cache_ttl_days: int = 1):
        self.use_cache = use_cache
        self.cache_ttl_days = cache_ttl_days
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ---------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------

    def full_snapshot(self, companies: Optional[List[ChainCompany]] = None) -> List[CompanyFinancials]:
        """全量扫描所有注册公司，返回财务数据列表"""
        if companies is None:
            companies = get_all_companies()

        results: List[CompanyFinancials] = []
        errors: List[str] = []

        for company in companies:
            ticker = company.ticker_yf
            if not ticker:
                continue
            try:
                fin = self.company_update(ticker)
                if fin is not None:
                    results.append(fin)
                else:
                    errors.append(f"{company.code}: returned None")
            except Exception as exc:
                logger.warning("full_snapshot: %s (%s) failed: %s", company.code, ticker, exc)
                errors.append(f"{company.code}: {exc}")

        if errors:
            logger.info("full_snapshot completed with %d errors: %s", len(errors), errors[:3])

        return results

    def company_update(self, ticker: str) -> Optional[CompanyFinancials]:
        """获取单个公司的最新财务数据

        优先读取缓存，缓存过期则从 yfinance 拉取。
        """
        # 尝试读缓存
        cached = self._read_cache(ticker)
        if cached is not None:
            return cached

        # 从 yfinance 获取
        fin = self._fetch_yfinance(ticker)

        # 写入缓存
        if fin is not None:
            self._write_cache(ticker, fin)

        return fin

    def batch_update(self, tickers: List[str]) -> Dict[str, Optional[CompanyFinancials]]:
        """批量更新，返回 {ticker: CompanyFinancials} 字典"""
        result: Dict[str, Optional[CompanyFinancials]] = {}
        for t in tickers:
            result[t] = self.company_update(t)
        return result

    # ---------------------------------------------------------------
    # yfinance 数据获取
    # ---------------------------------------------------------------

    def _fetch_yfinance(self, ticker: str) -> Optional[CompanyFinancials]:
        """从 yfinance 拉取一个 ticker 的财务数据"""
        import yfinance as yf

        try:
            t = yf.Ticker(ticker)
            info = t.info or {}

            # 基础识别
            company = None
            from src.industry_chain.registry import get_company
            company = get_company(ticker)

            name = info.get("longName") or info.get("shortName") or ticker
            layer = company.layer if company else ChainLayer.APPLICATION_SAAS

            fin = CompanyFinancials(ticker=ticker, name=str(name), layer=layer)
            fin.trade_date = date.today()

            # --- 从 info 获取 ---
            fin.market_cap = _safe_float(info.get("marketCap"))
            fin.enterprise_value = _safe_float(info.get("enterpriseValue"))
            fin.pe_ratio = _safe_float(info.get("trailingPE"))
            fin.ps_ratio = _safe_float(info.get("priceToSalesTrailing12Months"))
            fin.pb_ratio = _safe_float(info.get("priceToBook"))

            # yfinance 返回的 margin 是小数，转百分比
            gm = _safe_float(info.get("grossMargins"))
            fin.gross_margin = round(gm * 100, 2) if gm is not None else None

            om = _safe_float(info.get("operatingMargins"))
            fin.operating_margin = round(om * 100, 2) if om is not None else None

            rev_growth = _safe_float(info.get("revenueGrowth"))
            fin.revenue_growth = round(rev_growth * 100, 2) if rev_growth is not None else None

            # --- 从年度财务报表获取 ---
            try:
                income_stmt = t.financials
                if income_stmt is not None and not income_stmt.empty:
                    rev_row = _pick_row(income_stmt, _INCOME_REVENUE_KEYS)
                    fin.revenue = _latest_value(rev_row)
                    # YoY 增长
                    yoy = _yoy_growth(rev_row)
                    if yoy is not None:
                        fin.revenue_growth = yoy

                    gp_row = _pick_row(income_stmt, _INCOME_GROSS_PROFIT_KEYS)
                    gross_profit = _latest_value(gp_row)
                    if fin.revenue and gross_profit is not None and gross_profit != 0 and fin.revenue != 0:
                        fin.gross_margin = round(gross_profit / fin.revenue * 100, 2)

                    oi_row = _pick_row(income_stmt, _INCOME_OP_INCOME_KEYS)
                    op_income = _latest_value(oi_row)
                    if fin.revenue and op_income is not None and op_income != 0:
                        fin.operating_margin = round(op_income / fin.revenue * 100, 2)

                    ni_row = _pick_row(income_stmt, _INCOME_NET_INCOME_KEYS)
                    net_income = _latest_value(ni_row)
                    if fin.revenue and net_income is not None and net_income != 0:
                        fin.net_margin = round(net_income / fin.revenue * 100, 2)
            except Exception as exc:
                logger.debug("fetch %s financials failed: %s", ticker, exc)
                fin.errors.append(f"income_stmt: {exc}")

            # --- 从现金流量表获取 ---
            try:
                cf_stmt = t.cashflow
                if cf_stmt is not None and not cf_stmt.empty:
                    capex_row = _pick_row(cf_stmt, _CASHFLOW_CAPEX_KEYS)
                    raw_capex = _latest_value(capex_row)
                    # yfinance 的 capex 通常为负值，取绝对值
                    if raw_capex is not None:
                        fin.capex = abs(raw_capex)

                    fcf_row = _pick_row(cf_stmt, _CASHFLOW_FCF_KEYS)
                    fin.free_cash_flow = _latest_value(fcf_row)
            except Exception as exc:
                logger.debug("fetch %s cashflow failed: %s", ticker, exc)
                fin.errors.append(f"cashflow: {exc}")

            # 数据完整度评估
            fin.data_completeness = self._assess_completeness(fin)
            return fin

        except Exception as exc:
            logger.warning("_fetch_yfinance(%s) failed: %s", ticker, exc)
            return None

    # ---------------------------------------------------------------
    # 缓存
    # ---------------------------------------------------------------

    def _cache_path(self, ticker: str) -> Path:
        return CACHE_DIR / f"{ticker}.json"

    def _read_cache(self, ticker: str) -> Optional[CompanyFinancials]:
        if not self.use_cache:
            return None
        path = self._cache_path(ticker)
        if not path.exists():
            return None
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            age_days = (datetime.now() - mtime).total_seconds() / 86400
            if age_days > self.cache_ttl_days:
                return None
            data = json.loads(path.read_text(encoding="utf-8"))
            return self._dict_to_financials(data)
        except Exception:
            return None

    def _write_cache(self, ticker: str, fin: CompanyFinancials) -> None:
        if not self.use_cache:
            return
        try:
            data = self._financials_to_dict(fin)
            path = self._cache_path(ticker)
            path.write_text(json.dumps(data, ensure_ascii=False, default=str), encoding="utf-8")
        except Exception as exc:
            logger.debug("write_cache(%s) failed: %s", ticker, exc)

    def flush_cache(self, ticker: Optional[str] = None) -> None:
        """清空缓存（单个或全部）"""
        if ticker:
            self._cache_path(ticker).unlink(missing_ok=True)
        else:
            for p in CACHE_DIR.glob("*.json"):
                p.unlink(missing_ok=True)

    # ---------------------------------------------------------------
    # 序列化辅助
    # ---------------------------------------------------------------

    @staticmethod
    def _assess_completeness(fin: CompanyFinancials) -> str:
        """根据已有字段判断数据完整度"""
        core = [fin.revenue, fin.gross_margin, fin.operating_margin, fin.market_cap]
        present = sum(1 for v in core if v is not None)
        if present >= 4:
            return "full"
        if present >= 2:
            return "partial"
        return "minimal"

    @staticmethod
    def _financials_to_dict(fin: CompanyFinancials) -> Dict[str, Any]:
        return {
            "ticker": fin.ticker,
            "name": fin.name,
            "layer": fin.layer.value,
            "trade_date": str(fin.trade_date) if fin.trade_date else None,
            "revenue": fin.revenue,
            "revenue_growth": fin.revenue_growth,
            "gross_margin": fin.gross_margin,
            "operating_margin": fin.operating_margin,
            "net_margin": fin.net_margin,
            "capex": fin.capex,
            "free_cash_flow": fin.free_cash_flow,
            "market_cap": fin.market_cap,
            "enterprise_value": fin.enterprise_value,
            "pe_ratio": fin.pe_ratio,
            "ps_ratio": fin.ps_ratio,
            "pb_ratio": fin.pb_ratio,
            "data_completeness": fin.data_completeness,
            "errors": fin.errors,
        }

    @staticmethod
    def _dict_to_financials(data: Dict[str, Any]) -> CompanyFinancials:
        return CompanyFinancials(
            ticker=data.get("ticker", ""),
            name=data.get("name", ""),
            layer=ChainLayer(data.get("layer", "application_agent_and_saas")),
            trade_date=date.fromisoformat(data["trade_date"]) if data.get("trade_date") else None,
            revenue=_safe_float(data.get("revenue")),
            revenue_growth=_safe_float(data.get("revenue_growth")),
            gross_margin=_safe_float(data.get("gross_margin")),
            operating_margin=_safe_float(data.get("operating_margin")),
            net_margin=_safe_float(data.get("net_margin")),
            capex=_safe_float(data.get("capex")),
            free_cash_flow=_safe_float(data.get("free_cash_flow")),
            market_cap=_safe_float(data.get("market_cap")),
            enterprise_value=_safe_float(data.get("enterprise_value")),
            pe_ratio=_safe_float(data.get("pe_ratio")),
            ps_ratio=_safe_float(data.get("ps_ratio")),
            pb_ratio=_safe_float(data.get("pb_ratio")),
            data_completeness=data.get("data_completeness", "partial"),
            errors=data.get("errors", []),
        )
