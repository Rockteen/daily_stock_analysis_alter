# 📈 股票智能分析系统 (daily_stock_analysis) 项目完整分析报告

本报告对 `daily_stock_analysis` 项目进行了全方位的结构梳理、架构解析和核心细节整理，以帮助深入理解该系统是如何将金融行情数据、实时新闻舆情与大语言模型相结合，从而实现自动化选股分析与智能问股决策的。

---

## 1. 项目概述

`daily_stock_analysis` 是一个基于 AI 大模型的 A股/港股/美股自选股智能分析系统。它能够每日自动获取数据、分析行情、进行新闻舆情检索，并通过大模型生成「决策仪表盘」与「大盘复盘」报告，最终推送至多种主流社交/办公平台（企业微信、飞书、Telegram、Discord、Slack、邮件等）。此外，它还配备了 WebUI 工作台与 Agent 策略问股模块，支持多轮交互式投资问询。

### 技术栈构成
- **核心逻辑**：Python (3.10+)
- **API 后端**：FastAPI + Uvicorn
- **大模型调用**：LiteLLM（支持 Anspire、AIHubMix、Gemini、OpenAI、DeepSeek、Claude、Ollama 等）
- **数据源获取**：AkShare、Tushare、Baostock、YFinance、Longbridge、TickFlow、EFinance 等
- **搜索服务**：Anspire AI Search、SerpAPI、Tavily、Bocha（博查）、Brave、MiniMax、SearXNG 等
- **推送通知**：Webhook 推送（飞书、企业微信、Slack、Discord）、Telegram Bot、邮件 SMTP 等
- **本地存储**：SQLite / JSON / 文件快照（Context Snapshot）

---

## 2. 目录结构与模块划分

```text
daily_stock_analysis/
├── main.py                     # 主调度程序，提供命令行入口、定时调度以及完整 analysis 流程
├── server.py                   # FastAPI 后端服务入口
├── webui.py                    # 启动本地 Web 服务的便捷脚本
├── api/                        # API 接口目录
│   ├── app.py                  # FastAPI 路由配置、中间件与核心初始化
│   ├── deps.py                 # API 依赖注入（如认证、数据库连接）
│   └── v1/                     # v1 版本 API
│       ├── router.py           # v1 路由分发器
│       └── endpoints/          # 各个功能端点（个股分析、历史报告、Agent、回测、配置等）
├── data_provider/              # 数据获取层，提供统一的金融数据抓取接口
│   ├── base.py                 # 数据抓取基类与统一的清洗规范
│   ├── akshare_fetcher.py      # AkShare 获取器（A股、ETF、资金流、换手率等）
│   ├── tushare_fetcher.py      # Tushare 获取器（高阶基本面与行情数据）
│   ├── yfinance_fetcher.py      # Yahoo Finance 获取器（主要用于港股/美股）
│   ├── longbridge_fetcher.py   # 长桥证券数据获取器
│   └── ...                     # 其他特定平台的 fetcher
├── src/                        # 系统核心逻辑源码
│   ├── core/                   # 核心计算与流程控制
│   │   ├── pipeline.py         # 核心分析流水线（调度个股数据抓取、分析、推送）
│   │   ├── market_review.py    # 大盘复盘逻辑
│   │   ├── backtest_engine.py  # 历史分析报告回测评估引擎
│   │   └── trading_calendar.py # 交易日历检查与交易时段状态判断
│   ├── agent/                  # Agent 策略问股与多轮对话系统
│   │   ├── executor.py         # 策略执行器
│   │   ├── orchestrator.py     # Agent 编排器
│   │   ├── tools/              # Agent 工具包（获取行情、搜索、回测工具）
│   │   └── strategies/         # 内置的 15 种分析策略（缠论、波浪、均线等）
│   ├── analyzer.py             # AI 分析层，负责 LLM 调用、Prompt 构建和 JSON 解析
│   ├── config.py               # 环境变量加载与系统配置中心
│   ├── notification.py         # 推送通知服务，多渠道格式化与分发
│   ├── storage.py              # 本地数据库访问（SQLite）与报告快照存储
│   └── feishu_doc.py           # 飞书云文档自动生成与更新管理
├── strategies/                 # 配置化的策略 YAML 文件
│   ├── ma_golden_cross.yaml    # 均线金叉策略
│   ├── chan_theory.yaml        # 缠论策略
│   └── ...                     # 其它各种经典策略配置
└── templates/ & static/        # WebUI 界面渲染所需的 HTML/CSS/JS 静态资源
```

---

## 3. 核心流程与运行机制

系统的主要工作流可以分为 **命令行执行/定时任务工作流** 以及 **WebUI 与 API 服务工作流**。

### 3.1 完整分析工作流（命令行/定时任务）

当执行 `python main.py` 或由定时任务触发 `run_full_analysis` 时，系统将执行以下核心步骤：

```mermaid
graph TD
    A[启动分析] --> B{交易日检查}
    B -- 闭市且未强制运行 --> C[跳过执行]
    B -- 交易日或强制运行 --> D[刷新股票索引与自选股列表]
    D --> E[初始化 StockAnalysisPipeline]
    E --> F[加载大盘复盘上下文 (DailyMarketContext)]
    F --> G[多线程并发执行个股分析]
    G --> H[获取个股行情与指标数据]
    H --> I[获取社交舆情与新闻/公告]
    I --> J[构建 Prompt 并调用大模型分析]
    J --> K[将分析结果存入本地 SQLite 并生成报告快照]
    K --> L[运行大盘复盘分析]
    L --> M{合并推送?}
    M -- 是 --> N[生成合并报告并通过 Webhook/邮件等推送]
    M -- 否 --> O[逐个推送个股分析并单独推送大盘复盘]
    N --> P[创建/更新飞书云文档]
    O --> P
    P --> Q[触发自动回测]
    Q --> R[结束任务]
```

#### 关键机制解析：
1. **交易日日历检查 (`trading_calendar.py`)**：默认检查 A股、港股、美股开闭市状态。如果某市场休市，对应的自选股数据采集将被跳过，降低无效的 API 损耗。
2. **并发控制与错误隔离 (`pipeline.py`)**：在 `StockAnalysisPipeline.run` 中，使用 `ThreadPoolExecutor` 并发获取和分析个股，最大并发数可配置。若单个股票因网络、API 配额或大模型报错失败，不会影响其余股票的正常分析与推送。
3. **断点续传设计 (`pipeline.py`)**：系统在获取数据前会校验本地数据库 `SQLite` 中今日的 K 线和分析快照。如果数据已准备完毕且未显式指定强制刷新，会直接复用缓存，有效节约网络请求与大模型 Tokens。
4. **延迟保护机制 (`analysis_delay`)**：为防止在分析多只股票时因密集调用搜索引擎或 LLM API 而触发限流（Rate Limit），可以在配置中设定延迟时间，保证并发流程平稳运行。

---

## 4. 核心功能模块详解

### 4.1 数据获取层 (`data_provider/`)
这是系统的“物质基础”。系统并非只抓取简单股价，而是聚合了多维度数据：
- **行情 K 线**：包含 30 天以来的日 K 线及均线状态。
- **技术指标**：计算 MA5、MA10、MA20，以及乖离率（Bias）、成交量变化等。
- **资金流向与筹码分布**：如果启用 `enable_chip_distribution`，会通过 AkShare 或 TickFlow 获取当前的筹码集中度（90% 筹码区间、筹码单峰/双峰形态），这直接影响大模型对个股强弱的研判。
- **实时估算数据**：在盘中或非交易时段，通过 realtime API（Tencent/YFinance）拉取最新价格，支持“实时估算价”和“上一交易日收盘价”的平滑切换。

### 4.2 AI 分析层 (`src/analyzer.py`)
主要职责是将所有结构化行情、指标、筹码、新闻舆情转换为精简的 Prompt，然后通过 LLM 进行推理。
- **多模型降级链 (Fallback Routing)**：大模型不可用是常见故障。`GeminiAnalyzer` 实现了自动容错降级。如果主模型（如 Gemini 2.5 Pro）请求超时或超出限制，系统会自动切换到降级列表（如 DeepSeek 或通义千问）继续重试。
- **JSON 强约束与自动修复 (`json_repair`)**：Prompt 要求模型输出必须符合预设的结构化 JSON。当模型返回非标准 JSON 字符（如多了逗号或包含 Markdown 标记）时，系统会先使用 `json_repair` 进行修复；如果解析依然失败，会退回到非结构化文本输出，确保报告始终可读。
- **交易策略护栏 (Guardrails)**：为了规避 AI “胡说八道”，引入了 `daily_market_context_guardrail` 和 `phase_decision_guardrail`。如果 AI 给出了买入建议，但当前股票乖离率过大（如短线涨幅过高）或均线呈空头排列，系统会启动拦截和修正。

### 4.3 智能 Agent 与策略问股 (`src/agent/`)
除了常规的每日自动复盘，系统还提供了一个自主性更强的 Agent 问股对话框架：
- **Orchestrator（编排器）**：负责维护会话状态、管理用户上下文与多轮追问的路由。
- **内置策略（yaml 驱动）**：系统在 `strategies/` 中定义了 15 种常见的投资分析流派（如缠论、波浪理论、事件驱动、情绪周期）。Agent 在接收到问题后，会加载对应的 YAML 规则，按照策略指南引导大模型重点评估。
- **Agent 工具箱 (`agent/tools/`)**：Agent 在思考过程中可以主动调用系统内的工具，例如：
  - `data_tools`：获取最新的财报、行情、K 线。
  - `search_tools`：实时联网搜索目标公司的最新传闻和催化事件。
  - `backtest_tools`：拉取该股票的历史 AI 评分和后续走势。

### 4.4 通知与云文档生成 (`src/notification.py` & `src/feishu_doc.py`)
- **多渠道推送**：不同渠道支持不同的格式。例如，对于微信/飞书机器人推送，主要生成精炼的 Markdown 卡片；而对于邮件，会把个股与大盘信息聚合成一封设计优雅的 HTML 格式邮件，且支持 Markdown 转图片。
- **飞书云文档**：系统内置 `FeishuDocManager`。在任务运行完毕后，除了发送推送，还会在指定的飞书云文件夹中自动新建一篇以日期时间命名的“大盘复盘与个股仪表盘”文档，方便后续留档查阅。

### 4.5 回测引擎 (`src/core/backtest_engine.py`)
系统每天输出的“买入/观望/卖出”决策准不准？回测引擎可以给出答案：
- 读取历史的分析报告，抓取当时的“评分（sentiment_score）”和“决策（operation_advice）”。
- 对比该决策发出后 1天、3天、5天、10天 和 20天 的个股真实股价走势。
- 计算超额收益率（Alpha）、胜率（Win Rate）以及最大回撤，并在 WebUI 回测看板中以可视化的图表形式展示给用户。

---

## 5. 项目设计亮点

1. **极致的鲁棒性（Robustness）**：数据抓取和 LLM 接口都具备健全的多源降级设计。任何一个节点出现故障，都有低配或备用方案进行兜底，非常适合长期无人值守运行。
2. **关注细节与边界**：在 `analyzer.py` 中，我们可以看到诸如盘中、盘前、非交易日的时段感知。技术指标的展示能够根据不同市场的具体时间和平缓交易日逻辑动态调整词条（例如，“今日行情” vs “上一完整交易日行情”）。
3. **低敏度与安全性**：在 Web 接口及公开 API 的设计中，对于高敏的环境变量（如各种 API Key、Webhooks）有严格的模糊和权限管理限制。在公共接口暴露时会自动检查管理员认证权限。
4. **易于扩展与二次开发**：数据抓取层（`DataFetcher`）和策略层均通过统一基类与接口约束，若想引入新的数据源（如某收费终端 API）或自定义新的交易策略，仅需继承并重写对应的方法或编写 YAML 策略配置即可。

---

> [!NOTE]
> 该项目已成功创建了从「行情抓取 ➔ 多维搜索 ➔ AI 策略提炼 ➔ 风险决策护栏 ➔ 闭环回测 ➔ 多渠道推送」的完整闭环。如果需要深入了解特定代码文件的实现，可以直接点击本报告中的链接进行查看。
