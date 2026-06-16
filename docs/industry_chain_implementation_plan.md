# AI 产业链研究框架 — 量化验证子系统实施计划

## 目标

将 **AI 产业链研究框架（8 层分层法）** 实现为 `src/industry_chain/` 独立子系统，将定性分析转化为可量化、可验证的代码模块，支持产业链利润分布追踪、假说验证与投资信号生成。

**版本**: v1.0
**分支**: `supply_train_replace`
**基分支**: `main`

---

## 背景与动机

AI 产业链研究框架的核心观点：

1. AI 产业链有 **8 个分层**：半导体设备→代工封装→AI 芯片→HBM/存储→服务器网络→云平台→基础模型→应用层
2. **利润分布不均**：最高在 AI 加速器层（Nvidia 毛利率 >71%），最低在应用层和服务器 ODM
3. **关键变量**驱动投资决策：hyperscaler capex、GPU 交付、HBM 价格、CoWoS 产能等
4. 部分论断可**量化验证**："应用层最容易被卷"、"ASIC 可能拿走部分 Nvidia 增量"、"Hyperscaler capex 仍在增长"

目标是将上述框架编码为可每日运行的量化验证系统，输出链层评分排名、假说验证结果和投资信号。

---

## 总体架构

```
src/industry_chain/
├── __init__.py                      # 包定义
├── models.py                        # 核心数据模型
├── registry.py                      # 公司注册表（8 层 50+ 公司）
│
├── data/
│   ├── __init__.py
│   ├── financial.py                 # 财务数据采集器
│   └── key_variables.py             # 关键变量追踪
│
├── analysis/
│   ├── __init__.py
│   ├── layer_scorer.py              # 链层评分引擎
│   ├── thesis_validator.py          # 框架假说验证引擎
│   └── signal_generator.py          # 信号生成器
│
├── reporting/
│   ├── __init__.py
│   ├── chain_report.py              # 报告生成
│   └── visualizer.py                # 可视化辅助
│
├── tools/
│   ├── __init__.py
│   └── industry_tools.py            # Agent 工具注册
│
└── cli.py                           # 命令行入口
```

---

## 阶段计划

### Phase 1: 数据模型与公司注册表

**关键文件**:
- `src/industry_chain/__init__.py`
- `src/industry_chain/models.py`
- `src/industry_chain/registry.py`

**内容**:

1. **`models.py`** — 定义以下数据模型：
   - `ChainLayer` 枚举：8 层，带中文名称和排序
   - `ChainCompany` 数据类：股票代码、中英文名、所属层、区域、yfinance ticker、核心角色
   - `CompanyFinancials` 数据类：收入、增速、毛利率、运营利润率、净利率、capex、市值、PE
   - `LayerFinancialSnapshot` 数据类：层的聚合财务指标
   - `LayerScore` 数据类：各评分维度的结果
   - `KeyVariable` 数据类：关键监控变量
   - `ThesisVerdict` 数据类：假说验证结果
   - `ChainScanResult` 数据类：全量扫描输出

2. **`registry.py`** — 公司注册表：
   - 8 层共约 50+ 公司（美股 + 中国相关），覆盖框架所有核心玩家
   - 每层列出全球核心玩家和中国相关玩家
   - 按层分组提供查询方法

**参考现有代码**:
- `src/sector/sector_data.py` 的 dataclass 模式
- `src/sector/__init__.py` 的包结构

### Phase 2: 财务数据采集层

**关键文件**:
- `src/industry_chain/data/__init__.py`
- `src/industry_chain/data/financial.py`
- `src/industry_chain/data/key_variables.py`

**内容**:

1. **`financial.py`** — `ChainFinancialFetcher` 类：
   - 核心方法：`full_snapshot()` 全量扫描所有注册公司
   - 支持 `company_update(ticker)` 单公司更新
   - 复用 `data_provider/yfinance_fundamental_adapter.py` 获取财务数据
   - 采集指标：收入、收入增速、毛利率、运营利润率、净利率、capex、市值、PE
   - 缓存：日频写入 `data/cache/industry_chain/` 避免重复请求
   - 错误处理：单公司失败不影响整体扫描

2. **`key_variables.py`** — 关键变量追踪：
   - 定义框架中的 10 个关键变量及其获取方式
   - 自动可获取：hyperscaler capex（通过 yfinance 财报数据）
   - 手动更新：CoWoS 产能、推理 token 增速、HBM 价格等
   - 预留手动更新接口

### Phase 3: 链层评分与假说验证引擎

**关键文件**:
- `src/industry_chain/analysis/__init__.py`
- `src/industry_chain/analysis/layer_scorer.py`
- `src/industry_chain/analysis/thesis_validator.py`
- `src/industry_chain/analysis/signal_generator.py`

**内容**:

1. **`layer_scorer.py`** — `LayerScorer` 类：
   - 按层聚合财务数据（均值、中位数、HHI）
   - 5 维评分：
     - 利润率得分（毛利率 60% + 运营利润率 40%）
     - 竞争壁垒得分（HHI + 玩家数量 + 技术门槛系数）
     - 瓶颈度得分（供给稀缺性 + 产能约束）
     - 增长动能得分（收入增速 + capex 趋势）
     - 估值压力得分（PE 历史分位数）
   - 输出：每层综合评分 + 排名

2. **`thesis_validator.py`** — `ThesisValidator` 类：
   - 实现 8-10 条框架论断的验证逻辑
   - 每条论断包含：名称、条件函数、数据依赖、pass/fail 阈值
   - 示例验证：
     - "NVDA 毛利率约 71%" → `abs(NVDA.gross_margin - 0.71) < 0.05`
     - "应用层最容易卷" → `avg_margin(应用层) < avg_margin(其他各层)`
     - "Hyperscaler capex 持续增长" → `Δ∑capex > 0`
   - 输出状态：pass / fail / insufficient_data

3. **`signal_generator.py`** — `SignalGenerator` 类：
   - 根据评分和假说验证生成投资信号
   - 层级别：overweight / neutral / underweight
   - 公司级别：基于层评分 + 公司相对表现

### Phase 4: 报告生成与 Agent 工具集成

**关键文件**:
- `src/industry_chain/reporting/__init__.py`
- `src/industry_chain/reporting/chain_report.py`
- `src/industry_chain/reporting/visualizer.py`
- `src/industry_chain/tools/__init__.py`
- `src/industry_chain/tools/industry_tools.py`

**内容**:

1. **`chain_report.py`** — Markdown 报告生成：
   ```
   # AI 产业链全景扫描 [日期]
   ## 一、链层评分排名
   ## 二、关键假说验证结果
   ## 三、重点公司监控
   ## 四、关键变量追踪
   ## 五、投资信号
   ```

2. **`visualizer.py`** — Markdown 表格和 ASCII 图表

3. **`industry_tools.py`** — Agent 工具：
   - `get_industry_chain_overview` — 产业链全景
   - `get_layer_analysis` — 指定链层分析
   - `validate_chain_thesis` — 假说验证
   - 注册方式参考 `src/agent/tools/analysis_tools.py`

### Phase 5: CLI 入口与验证

**关键文件**:
- `src/industry_chain/cli.py`

**内容**:

1. **CLI 命令**：
   - `python -m src.industry_chain.cli scan` — 全量扫描
   - `python -m src.industry_chain.cli layer --name AI_ACCELERATOR` — 单层分析
   - `python -m src.industry_chain.cli thesis` — 假说验证
   - `python -m src.industry_chain.cli track` — 关键变量追踪

2. **测试**：
   - `tests/test_industry_chain/test_models.py`
   - `tests/test_industry_chain/test_scorer.py`
   - 网络相关测试标记 `@pytest.mark.network`

---

## 复用现有基础设施

| 现有模块 | 复用方式 |
|----------|---------|
| `data_provider/yfinance_fetcher.py` | 获取美股行情和财务数据 |
| `data_provider/yfinance_fundamental_adapter.py` | 基本面数据提取模式参考 |
| `data_provider/DataFetcherManager` | 数据源管理（如果需要更多数据源） |
| `src/agent/tools/registry.py` | 工具注册系统 |
| `src/sector/` (整个包) | 子系统架构模式参考 |
| `src/formatters.py` | 报告格式输出辅助 |

## 设计约束

1. **数据源优先 yfinance**：美股核心公司首选 yfinance；中国相关公司视可用性选用 akshare 或 yfinance
2. **纯 Python 数据类，不引入新的 ORM**：Phase 1-4 仅用 dataclass，无需数据库
3. **部分变量手动更新**：CoWoS 产能、推理 token 增速等标记为 `manual_only`
4. **独立子系统**：不影响现有个股分析流程；扫描结果可作为参考信号注入
5. **缓存友好**：日频缓存财务数据，避免 API 限流

## 验证计划

1. **单元测试**：`pytest tests/test_industry_chain/ -m "not network"`
2. **模式验证**：运行 CLI `scan` 和 `thesis`，验证产出格式和框架论断
3. **交叉验证**：将层排名与框架原文利润率排名对比
4. **代码质量**：`py_compile` + `flake8`

---

## 预期交付物

1. `src/industry_chain/` 完整包，约 15 个文件
2. 8 层 50+ 公司的注册表
3. 10 条框架论断的量化验证引擎
4. 3 个 Agent 工具
5. CLI 入口
6. 单元测试覆盖核心逻辑
