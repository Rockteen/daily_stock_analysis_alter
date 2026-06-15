# A股 ETF 板块拐点捕捉策略集成开发总结报告

本报告总结了将「A股 ETF 板块拐点捕捉策略」完整集成至 `daily_stock_analysis` 系统的全部工作、核心设计与技术实现。

---

## 1. 策略核心架构设计

板块拐点捕捉系统作为与个股分析平行的独立子系统，遵循系统的分层规范。

### 核心流向与状态机转换
1. **大盘总开关（Market Regime Switch）**：以沪深 300 指数 (000300) 的 200 日移动平均线 (MA200) 作为大盘趋势过滤器。如果指数高于 MA200，则大盘为 `Risk ON`，允许买入和启动；如果低于 MA200，则大盘为 `Risk OFF`，一票否决所有板块的买入与启动，持有板块强制转入警戒或全清。
2. **启动评分器 (IgnitionScorer)** 与 **见顶评分器 (DistributionScorer)**：多维度量价、RS 趋势和成分股上涨广度加权合成评分 (0-100)。
3. **状态机 (State Machine)**：管理各板块 ETF 状态转移：
   `SCANNING` (空仓扫描) ➔ `LURKING` (潜伏观察) ➔ `HOLDING` (持有) ➔ `ALERT` (警戒持有) ➔ `EXITED` (卖出离场) ➔ `SCANNING` (自动循环)。

---

## 2. 完成的具体开发阶段

### Phase 1：数据层与核心信号计算（量价骨架）
- **数据收集器**：在 [src/sector/sector_data.py](file:///D:/tools/stock-analysis/daily_stock_analysis/src/sector/sector_data.py) 中，使用 AkShare 获取 ETF 日 K 线及大盘基准，并通过单次获取全市场行情并与指数成分股列表求交集的方法，极速计算出高精度的每日成分股上涨广度。
- **大盘总开关**：在 [src/sector/market_regime.py](file:///D:/tools/stock-analysis/daily_stock_analysis/src/sector/market_regime.py) 中实现 `MarketRegimeSwitch`，按收盘价与 MA200 关系一票否决。
- **启动评分与见顶评分**：在 [src/sector/ignition_scorer.py](file:///D:/tools/stock-analysis/daily_stock_analysis/src/sector/ignition_scorer.py) 和 [src/sector/distribution_scorer.py](file:///D:/tools/stock-analysis/daily_stock_analysis/src/sector/distribution_scorer.py) 中，剥离了缺省的「聪明钱」和「新闻催化」权重，对剩余的底部箱体形态、放量突破强度、相对强度反转 (RS) 以及上涨广度进行动态归一化加权，输出高可靠性的 0-100 分数。

### Phase 2：状态机与持久化
- **状态转移**：在 [src/sector/state_machine.py](file:///D:/tools/stock-analysis/daily_stock_analysis/src/sector/state_machine.py) 中实现了严格根据启动/见顶阈值、持续天数及大盘开关切换状态的五状态机。
- **数据表新增**：在 [src/storage.py](file:///D:/tools/stock-analysis/daily_stock_analysis/src/storage.py) 中，添加了 `SectorETFPool`（ETF池表）与 `SectorInflectionState`（每日评分状态表）模型，并在 `DatabaseManager` 中新增了 `get_active_sector_etfs`（首次调用自动 Bootstrap 预置种子池）、`save_sector_inflection_state` 和 `get_sector_inflection_history` 数据库事务存取函数。

### Phase 3：服务层、命令行参数与通知集成
- **扫描服务编排**：在 [src/services/sector_inflection_service.py](file:///D:/tools/stock-analysis/daily_stock_analysis/src/services/sector_inflection_service.py) 中实现 `SectorInflectionService`。它统一控制大盘过滤、各板块状态评估和数据库持久化，并调用系统通知。
- **Bug 修正**：修复了原服务中 `new_state == SectorState.EXITED` 自动重置时对 `distribution_score=distribution_score` 变量引用错误（修正为 `distribution.score`）以及大盘提示语中 "沪静300" 的拼写错误。
- **CLI 参数注册**：在 [main.py](file:///D:/tools/stock-analysis/daily_stock_analysis/main.py) 中注册了 `--sector-scan` 和 `--sector-scan-only` 命令行参数。前者随每日正常流运行，后者用于独立扫描并发送报告。
- **模板与通知解耦**：修改了 [src/notification.py](file:///D:/tools/stock-analysis/daily_stock_analysis/src/notification.py)，在 `NotificationBuilder` 中新增了板块拐点专用 Markdown 报告构建器，并在 `NotificationService` 中新增了 `send_sector_inflection_report` 接口，保持了通知层和业务服务层的代码解耦。

### Phase 4：API 路由与 WebUI 界面集成
- **FastAPI 接口开发**：创建了 [api/v1/endpoints/sector_inflection.py](file:///D:/tools/stock-analysis/daily_stock_analysis/api/v1/endpoints/sector_inflection.py) 端点文件，提供：
  - `GET /api/v1/sector/dashboard`：获取板块最新状态和评分。
  - `GET /api/v1/sector/{etf_code}/history`：获取单板块历史状态。
  - `POST /api/v1/sector/scan`：手动或自动运行拐点扫描。
  - `GET /api/v1/sector/pool`、`POST /api/v1/sector/pool` 和 `DELETE /api/v1/sector/pool/{etf_code}`：管理板块标的池。
- **路由注册**：在 [api/v1/router.py](file:///D:/tools/stock-analysis/daily_stock_analysis/api/v1/router.py) 中聚合注册 `/sector` 路由。
- **前端页面集成**：
  - **i18n**：在 [apps/dsa-web/src/i18n/uiText.ts](file:///D:/tools/stock-analysis/daily_stock_analysis/apps/dsa-web/src/i18n/uiText.ts) 中新增了 `layout.nav.sector` 和相关中英翻译。
  - **Sidebar 导航**：在 [apps/dsa-web/src/components/layout/SidebarNav.tsx](file:///D:/tools/stock-analysis/daily_stock_analysis/apps/dsa-web/src/components/layout/SidebarNav.tsx) 导入了 Lucide 中的 `Compass` 指针图标并添加了板块拐点导航项。
  - **API 层对接**：新增了 [apps/dsa-web/src/types/sector.ts](file:///D:/tools/stock-analysis/daily_stock_analysis/apps/dsa-web/src/types/sector.ts) 类型声明与 [apps/dsa-web/src/api/sector.ts](file:///D:/tools/stock-analysis/daily_stock_analysis/apps/dsa-web/src/api/sector.ts) API 请求封装。
  - **板块工作台页面**：新增了 [apps/dsa-web/src/pages/SectorPage.tsx](file:///D:/tools/stock-analysis/daily_stock_analysis/apps/dsa-web/src/pages/SectorPage.tsx) 页面。它包含：
    - 大盘总开关状态卡片 (Risk ON / OFF 动态配色)。
    - 分析看板：展示各板块 ETF 最新状态徽章、评分条及持续天数，卡片点击后侧滑打开历史演变日志抽屉。
    - Recharts 折线趋势图：以极具质感的渐变面积图在抽屉内展示板块近 60 日启动/见顶评分走势。
    - ETF 池配置面板：包含板块启用开关、增删板块交互对话框。
  - **页面路由注册**：在 [apps/dsa-web/src/App.tsx](file:///D:/tools/stock-analysis/daily_stock_analysis/apps/dsa-web/src/App.tsx) 注册了 `/sector` 路由，支持懒加载 `SectorPage`。

### Phase 5：预留接口 (已完成 SMP 占位)
- **聪明钱仓位计算**：创建了 [src/sector/smp_calculator.py](file:///D:/tools/stock-analysis/daily_stock_analysis/src/sector/smp_calculator.py)，预留了 `SMPCalculator` 接口。当前由于缺乏高频公募持仓数据源，接口默认返回 `0.0`，为二期接入专业数据源预留了完备的基础。

---

## 3. 后续规划与思考

1. **二期数据源接入**：
   - 当二期需要接入聪明钱仓位数据 (SMP) 或通过多渠道新闻提取政策催化评分时，可以直接在 `src/sector/smp_calculator.py` 与未创建的 `src/sector/news_catalyst.py` 中重写打分逻辑，然后在主评分器中调高对应的权重参数（当前权重为 0）。
2. **测试与回测验证**：
   - 可以在本地通过 `--sector-scan` 或在 Web 页面上手动触发 `/scan` 快速测试。在数据库中积累更多板块拐点样本后，建议结合 `BacktestEngine` 构建独立的板块拐点历史回测，以统计各板块在不同大盘周期下的信号胜率。
