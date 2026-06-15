# ETF 板块拐点策略验证与手动验证报告 (Walkthrough)

## 概述

为了确保 **A股 ETF 板块拐点捕捉策略** 的稳定性和正确性，我们为其设计并运行了完整的测试套件与离线手动验证流程。
所有测试和手动验证均成功通过，状态机的强平避险逻辑以及 FastAPI 各个板块相关 API 均表现符合预期。

---

## 1. 自动化测试结果

我们共开发并执行了 21 个自动化测试用例，覆盖了大盘开关过滤、信号评分、状态机转移以及服务/DB集成等所有关键逻辑。

运行测试命令：
```bash
python -m pytest tests/test_sector/ -v
```

测试结果概要（共 21 项通过）：

| 测试文件 | 测试项 | 描述 | 状态 |
| :--- | :--- | :--- | :--- |
| `test_market_regime.py` | `test_evaluate_risk_on` / `test_evaluate_risk_off` 等 | 验证 200 日均线大盘趋势开关 | PASSED |
| `test_ignition_scorer.py` | `test_ignition_score_confirmed` / `test_ignition_score_watch` 等 | 验证 6 维启动评分与阶段判定 | PASSED |
| `test_distribution_scorer.py`| `test_detect_top_divergence_macd` / `test_distribution_score_exit` | 验证顶背离判定及离场/预警评分 | PASSED |
| `test_state_machine.py` | `test_risk_off_clears_holdings` / `test_scanning_transitions` 等 | 验证五状态机状态转移规则 | PASSED |
| `test_sector_integration.py` | `test_sector_scan_bootstrap_and_integration` / `test_sector_scan_risk_off` / `test_get_dashboard` | 验证扫描服务与 SQLite 数据库持久化交互流程 | PASSED |

---

## 2. 离线手动验证 (Manual Verification)

考虑到本地开发环境的网络不稳定性（第三方 API 如 Eastmoney/Akshare 可能连接超时），我们特别编写了 `scripts/verify_sector_offline.py` 验证脚本。该脚本通过 mock 大盘与行情数据来对主逻辑、大盘风险开关以及 FastAPI 接口可用性进行完整的端到端仿真。

执行验证命令：
```bash
python scripts/verify_sector_offline.py
```

### 验证步骤与结果：

1. **[Step 1] 运行 `--sector-scan-only` (Risk ON, 确认买入)**
   - 模拟沪深300大盘在 200日均线以上（RISK_ON），半导体ETF `512480` 启动评分 > 80。
   - 验证：成功执行仅板块扫描流程，板块状态由空仓扫描 `scanning` 成功流转至持有 `holding`，并将记录落盘。

2. **[Step 2] 运行 `--sector-scan-only` (Risk OFF, 强平避险)**
   - 模拟沪深300大盘转为下跌通道（最新收盘价低于 200日均线，大盘为 RISK_OFF）。
   - 验证：状态机强制将持有 `holding` 板块清仓，转换为 `exited` 中间态，并最终自动流转回 `scanning` 等待下一次机会。

3. **[Step 3] 验证 FastAPI 接口**
   - 使用 FastAPI TestClient 对路由进行接口可用性请求。
   - 验证：
     - `GET /api/v1/sector/pool` 正确初始化并返回 11 个激活的板块 ETF 标的。
     - `GET /api/v1/sector/dashboard` 返回今日扫描最新状态（展示大盘为 `risk_off`，半导体状态为 `scanning`）。
     - `GET /api/v1/sector/512480/history` 返回该板块的历史状态序列（长度为 2：包含买入与避险强平记录）。
     - `POST /api/v1/sector/scan` 接口调用返回 `status = success`。

---

## 总结

- 状态机在 **大盘低于 MA200 (Risk OFF)** 时的**避险强平功能**在集成测试与离线手动验证中均表现完美。
- FastAPI 的 **/api/v1/sector/** 接口与数据契约一致，能正确回显数据库状态与历史变更，可以与前端/Web 页面无缝集成。
