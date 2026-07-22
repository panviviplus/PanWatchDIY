# PR #71 分批迁移方案

> **来源**: [PanWatch PR #71](https://github.com/TNT-Likely/PanWatch/pull/71) by zackzhangkai
> **目标仓库**: [PanWatchDIY](https://github.com/panviviplus/PanWatchDIY)
> **状态**: 施工中 🚧

---

## 概述

[PanWatch PR #71](https://github.com/TNT-Likely/PanWatch/pull/71) 是一个大型 PR（218 文件，+32,921/-1,636 行），包含 6 大功能域的变更。原作者 TNT-Likely 建议拆分为 6 个独立 PR。本方案将其调整为 **5+1 批次**，按依赖关系和风险从低到高排列，每批独立可测、可部署。

## PR #71 变更全景

### 1. MCP 接口
暴露 45+ 工具供 Cursor/Claude Desktop 等 AI 客户端调用盯盘能力。

| 类型 | 文件 |
|------|------|
| 新增 | `src/web/api/mcp.py` — JSON-RPC 端点 `/api/mcp` |
| 新增 | `frontend/src/pages/MCP.tsx` — MCP 配置/调试页 |
| 新增 | `tests/test_mcp_tools.py` |
| 修改 | `src/web/app.py` — 路由注册 + 中间件放行原生 JSON-RPC 格式 |
| 修改 | `server.py` — 注册端点 |

### 2. ETF 盯盘
场内 ETF 搜索/详情/成分股分析、净值图表、ETF 持仓 AI 分析。

| 类型 | 文件 |
|------|------|
| 新增 | `src/collectors/etf_collector.py` |
| 新增 | `src/agents/etf_holding_analyst.py` |
| 新增 | `prompts/etf_holding_analyst.md` |
| 新增 | `frontend/.../etf-overview-modal.tsx` |
| 新增 | `frontend/.../etf-nav-chart.tsx` |
| 新增 | `src/core/backtest/cost_model.py` |
| 修改 | `src/web/models.py` — `security_type` 字段 |
| 修改 | `src/core/paper_trading_engine.py` — ETF 免印花税/过户费 |

> ⚠️ **合并策略**: 本项目已有 `fund_collector`、`fund_holding_analyst`、`FundOverviewModal`、`InteractiveFundChart`。PR 的 ETF 特性与现有场外基金系统**合并共存**，而非替换。

### 3. AI 助手增强
对话续聊历史、清会话、Chat Actions（建提醒/加减仓确认）。

| 类型 | 文件 |
|------|------|
| 新增 | `src/core/chat_actions.py` |
| 新增 | `src/core/position_daily_pnl.py` |
| 新增 | `src/core/position_trades_context.py` |
| 新增 | `src/core/stock_news_context.py` |
| 新增 | `frontend/src/components/ChatActionCard.tsx` |
| 修改 | `frontend/src/components/ChatWidget.tsx` |
| 修改 | `frontend/packages/api/src/chat.ts` |
| 修改 | `src/web/api/chat.py` |
| 修改 | `src/collectors/news_collector.py` — Playwright 新闻采集 |

### 4. 本地 Skill 广场
Hermes Skill 扫描/运行/报告，老马视角（LMD）产业周期分析。

| 类型 | 文件 |
|------|------|
| 新增 | `src/core/local_skill_scanner.py`, `hermes_runner.py`, `hermes_config.py` |
| 新增 | `src/core/local_skill_report.py`, `lmd_auto_bootstrap.py`, `lmd_report_snapshot.py` |
| 新增 | `src/agents/lmd_outlook.py` + `prompts/lmd_outlook.txt` |
| 新增 | `src/web/api/local_skills.py` |
| 新增 | `frontend/src/pages/Skills.tsx` + `report-markdown.tsx` |
| 新增 | `config/lmd_industry_chains.yaml` |

### 5. 长线持仓计划
核心/卫星仓架构、分批加仓、滚仓降本、缠论情绪策略、产业链分类。

| 类型 | 文件 |
|------|------|
| 新增 | `src/core/long_term_plan.py` |
| 新增 | `src/core/signals/chan_emotion_strategy.py` |
| 新增 | `src/core/stock_industry_chain.py`, `stock_concept_tags.py` |
| 新增 | `src/core/regulatory_red_flags.py` |
| 新增 | `src/collectors/concept_collector.py` |
| 新增 | 10+ 前端组件（long-term-plan-panel, rolling-cost-plan, chan-emotion-*, industry-chain-*, etc.） |
| 新增 | `docs/long-term-position-architecture.md` |

### 6. 行情与 UI（⚠️ 低优先级）
分时图、分钟K线、深度分析模式、首页指数扩展。

| 类型 | 文件 |
|------|------|
| 新增 | `frontend/.../IntradayChart.tsx` |
| 修改 | `frontend/.../InteractiveKline.tsx`（重大改写 ~700行） |
| 新增 | `frontend/.../deep-analysis-modal.tsx`, `deep-analysis-mode-picker.tsx` |
| 新增 | `src/core/providers/kline/tencent.py` |
| 修改 | `src/collectors/kline_collector.py` |

---

## 与现有代码的重叠分析

| PR 功能 | PanWatchDIY 现状 | 迁移策略 |
|---------|-----------------|---------|
| ETF 盯盘 | 已有 fund_collector, fund_holding_analyst, FundOverviewModal, InteractiveFundChart | **合并增强** |
| AI 聊天 | 已有 ChatConversation/ChatMessage 表、ChatWidget | **增强** |
| 分时图/分钟K线 | 已有 InteractiveKline.tsx（较完善） | **放最后/跳过** |
| MCP | 无 | **全新引入** |
| Skill 广场 | 无 | **全新引入** |
| 长线持仓/产业链/缠论 | 无 | **全新引入** |

---

## 分批施工方案

### 第 0 批：基础设施准备（基建）

**目标**: 为后续批次铺路，变更最小、风险最低。

- [x] 新增 `security_type` 字段到 Stock 模型 + DB 迁移脚本 (m119)
- [x] 新增 `PositionTrade` 表 + 迁移 (m121)
- [x] Position 模型新增 `status/closed_at/realized_pnl` 字段
- [x] Account 模型新增 `other_funds/other_fund_items/initial_funds/base_currency`
- [x] `requirements.txt` Python 依赖已就绪（playwright, weasyprint, xhtml2pdf, tradingagents）
- [x] `frontend/package.json` 新增 `lightweight-charts` npm 包 + `vitest`
- [x] `frontend/index.html` 移除 CDN lightweight-charts 脚本
- [x] 新增 `src/core/app_shutdown.py` 优雅关闭
- [ ] 前端新增通用类型/工具函数（后续批次按需添加）

**验证**: ✅ Python 编译通过 ✅ TypeScript 类型检查通过 ✅ 前端 build 成功 (3.87s)

---

### 第 1 批：MCP 接口

**目标**: 独立性强，不依赖其他批次，可独立上线。

- [x] 新增 `src/web/api/mcp.py` — JSON-RPC 端点 (3863行，已适配 PanWatchDIY)
- [x] 新增 `frontend/src/pages/MCP.tsx` — MCP 配置页 (472行，已适配)
- [x] 修改 `src/web/response.py` — 中间件放行 `/api/mcp` 原生 JSON-RPC 格式
- [x] 修改 `src/web/app.py` — 注册 MCP 路由（公开，自带 Bearer/Basic 鉴权）
- [x] 修改 `frontend/src/App.tsx` — 新增 `/mcp` 路由和导航
- [ ] 新增 `tests/test_mcp_tools.py`（待后续添加）

**验证**: ✅ Python 编译通过 ✅ TypeScript 类型检查 ✅ 前端 build 成功 (4.25s) ✅ deploy.sh 就绪
**注意**: ETF 工具目前为桩实现，第 2 批施工后替换为真实实现

## 部署脚本

`deploy.sh` 放置在项目根目录（已被 `.gitignore` 忽略），用于每批施工后的本地部署：

```bash
bash deploy.sh              # 完整流程：测试 → 构建 → 部署 → 推送
bash deploy.sh --skip-tests # 跳过测试
bash deploy.sh --skip-push  # 跳过代码推送
```

流程：Python 测试 → 前端构建检查 → Docker 镜像构建 (panwatch-etf:latest) → docker-compose 重启 → git push

---

### 第 2 批：ETF 盯盘增强

**目标**: 在现有场外基金系统基础上，增加场内 ETF 支持。

- [ ] 新增 `src/collectors/etf_collector.py`
- [ ] 新增 `src/agents/etf_holding_analyst.py`
- [ ] 新增 `prompts/etf_holding_analyst.md`
- [ ] 新增 `frontend/.../etf-nav-chart.tsx`
- [ ] 增强 `FundOverviewModal.tsx` — 融入 ETF 概览
- [ ] 新增 `src/core/backtest/cost_model.py`
- [ ] 修改 `src/core/paper_trading_engine.py` — ETF 免印花税

**验证**: ETF 搜索/详情/净值图表/AI 分析正常

---

### 第 3 批：AI 助手增强

**目标**: Chat Actions + 对话历史 + 上下文注入。

- [ ] 新增 `src/core/chat_actions.py`
- [ ] 新增 `src/core/position_daily_pnl.py`
- [ ] 新增 `src/core/position_trades_context.py`
- [ ] 新增 `src/core/stock_news_context.py`
- [ ] 新增 `frontend/src/components/ChatActionCard.tsx`
- [ ] 修改 `ChatWidget.tsx`、`chat.py`（前后端）
- [ ] 修改 `src/collectors/news_collector.py` — Playwright 新闻

**验证**: 续聊/清会话/Chat Actions 正常

---

### 第 4 批：长线持仓 + 产业链 + Skill 广场

#### 4a：长线持仓计划
- [ ] `src/core/long_term_plan.py` + 前端面板
- [ ] `frontend/.../rolling-cost-plan.tsx` + `src/lib/rolling-cost-plan.ts`
- [ ] `frontend/.../add-position-calculator.tsx`
- [ ] `src/core/signals/chan_emotion_strategy.py` + 前端面板

#### 4b：产业链 + 概念标签
- [ ] `src/core/stock_industry_chain.py` + `config/lmd_industry_chains.yaml`
- [ ] `src/core/stock_concept_tags.py` + `src/core/regulatory_red_flags.py`
- [ ] `src/collectors/concept_collector.py`
- [ ] 前端: industry-chain-*, stock-concept-tags, watchlist-valuation-brief

#### 4c：本地 Skill 广场
- [ ] `src/core/local_skill_scanner.py` + `hermes_runner.py` + `hermes_config.py`
- [ ] `src/core/local_skill_report.py` + `lmd_auto_bootstrap.py` + `lmd_report_snapshot.py`
- [ ] `src/agents/lmd_outlook.py` + `prompts/lmd_outlook.txt`
- [ ] `src/web/api/local_skills.py`
- [ ] `frontend/src/pages/Skills.tsx` + `report-markdown.tsx`

---

### 第 5 批：行情与 UI 增强（⚠️ 可跳过）

**目标**: 分时图、分钟K线、深度分析模式。

- [ ] `frontend/.../IntradayChart.tsx`
- [ ] 谨慎合并 `InteractiveKline.tsx`（分钟K线支持）
- [ ] `src/core/providers/kline/tencent.py`
- [ ] `src/collectors/kline_collector.py` 增强
- [ ] `frontend/.../deep-analysis-modal.tsx` + `deep-analysis-mode-picker.tsx`
- [ ] 首页指数扩展

---

## 验证策略（每批次）

1. `python -m pytest tests/ -v` — 全量测试通过
2. 新增本批次相关测试用例
3. `cd frontend && pnpm build` — 前端构建无报错
4. Docker 部署: `docker-compose up -d --build` (路径: `C:\Program Files\PanWatch\`)
5. 手动回归: 首页 → 持仓 → Agent → 聊天 → 通知

## 关键决策

| 决策项 | 结论 |
|--------|------|
| 品牌名 | **保持 PanWatchDIY**，跳过 PR 中 AlphaMind 改名 |
| ETF vs 基金 | **合并共存**：场外基金（现有）+ 场内 ETF（PR 增强） |
| 分时图/分钟K线 | **放最后 / 可跳过** |
| 第4批拆分 | **4a/4b/4c** 三个子批次 |
| 施工粒度 | 逐文件搬运，先读 PR diff 再合并 |

---

> 📅 创建日期: 2026-07-22
> 📝 基于 PR #71 分析 + PanWatchDIY 代码库探索
