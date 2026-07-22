# 盯盘侠 PanWatchDIY

**自托管 AI 盯盘助手** — A 股 / 港股 / 美股 / ETF 实时监控、多账户持仓管理、策略信号模拟盘、AI 智能分析与通知推送。

集成 [TradingAgents](https://github.com/TauricResearch/TradingAgents) 多 Agent 投资决策框架，支持 MCP 协议供 AI 客户端调用。

---

## ✨ 核心能力

### 📊 多市场实时行情
- **A 股** / **港股** / **美股** 三市场全覆盖
- **场内 ETF** 实时行情、IOPV 净值、折溢价率、成分股穿透
- **场外基金** 净值走势、重仓股分析、持仓重叠度
- 自选股管理，支持按市场分组

### 🤖 AI Agent 分析体系
| Agent | 功能 | 调度 |
|-------|------|------|
| **盘前展望** | 隔夜信息 + 昨日复盘 → 今日走势预判 | 每个交易日 9:00 |
| **盘中监测** | 实时异动监控，AI 智能判断信号 | 交易时段每 5 分钟 |
| **收盘复盘** | 市场回顾、个股复盘、次日关注 | 每个交易日 15:30 |
| **基金分析** | 基金重仓股、持仓重叠度、业绩跟踪 | 每周五 20:00 |
| **ETF 成分分析** | ETF 折溢价、成分股、与持仓重叠度 | 每周五 20:00 |
| **TradingAgents** | 多视角深度分析（基本面/情绪/新闻/技术 + 辩论 + 风控） | 手动触发 |

### 📈 策略信号与模拟盘
- **7 大内置策略**: 趋势延续、MACD 金叉、放量突破、回踩确认、超跌反弹、Agent 建议、市场扫描
- **缠论情绪策略** (`chan_emotion`): 均线多空排列 + 分型识别 + 综合情绪评分
- **模拟盘引擎**: 自动按策略信号建仓/平仓，支持 ETF 免印花税，移动止损 + 时间止损
- 虚拟账户盈亏跟踪，完整交易流水

### 💬 AI 聊天助手
- 历史对话续聊，多轮上下文记忆
- **Chat Actions**: AI 可返回可操作卡片 — 创建提醒 / 建议加减仓 / 设置止损止盈 / 添加关注
- **上下文注入**: 自动注入持仓盈亏、交易流水、相关新闻
- 对话重命名 / 清空历史

### 🔔 多渠道通知
- **Telegram** / **企业微信** / **钉钉** / **Bark** / **Webhook** — 通过 Apprise 统一推送
- 通知去重 & 静默时段策略
- 价格提醒：到达目标价自动推送

### 🏗️ 长线持仓计划
- **核心/卫星仓**架构：核心仓长期持有 (60-70%)，卫星仓波段操作 (30-40%)
- **分批加仓**：按价格区间自动生成等距加仓计划
- **滚仓降本**：利用波段差价降低核心仓持仓成本

### 🧰 MCP 协议 (Model Context Protocol)
- JSON-RPC 端点 `/api/mcp`，暴露 **45+ 工具**供 Claude Desktop / Cursor 等 AI 客户端直接调用
- 支持 Bearer / Basic 双重认证
- 核心工具类别：股票行情、K 线数据、基金数据、ETF 数据、新闻搜索、价格提醒、自选股管理、模拟盘交易

### 🧩 本地 Skill 广场
- **Hermes 引擎**: 扫描 `skills/` 目录，自动发现和加载本地技能
- 每个 Skill YAML 清单 + Python 执行器 + Prompt 模板
- Web UI 一键运行 / 查看报告
- 可扩展的插件式架构

---

## 🏗️ 技术架构

```
PanWatchDIY/
├── server.py                  # 统一入口: DB 初始化 → Agent 注册 → 调度器 → FastAPI
├── src/
│   ├── config.py              # 配置模型 (Settings + StockConfig + AppConfig)
│   ├── agents/                # AI Agent 层 (premarket / intraday / daily / fund / etf / tradingagents)
│   ├── collectors/            # 数据采集层 (quotes / kline / fund / etf / news)
│   ├── core/                  # 核心引擎
│   │   ├── ai_client.py       # OpenAI 兼容 AI 客户端
│   │   ├── notifier.py        # 通知管理器
│   │   ├── scheduler.py       # Agent 调度器
│   │   ├── paper_trading_*    # 模拟盘引擎 / 通知 / 调度
│   │   ├── signals/           # 策略信号生成 (trend / macd / momentum / chan_emotion / ...)
│   │   ├── backtest/          # 回测成本模型
│   │   ├── chat_actions.py    # 聊天动作解析
│   │   ├── long_term_plan.py  # 长线持仓计划引擎
│   │   ├── local_skill_*      # Skill 扫描 / 执行
│   │   └── ...
│   ├── web/                   # FastAPI Web 层
│   │   ├── app.py             # 路由注册
│   │   ├── api/               # 30+ API 模块 (stocks / agents / chat / mcp / local_skills / ...)
│   │   ├── models.py          # SQLAlchemy ORM 模型
│   │   └── database.py        # SQLite 数据库
│   └── models/                # 领域模型 (MarketCode etc.)
├── prompts/                   # Agent Prompt 模板
├── frontend/                  # React + TypeScript + Vite 前端
│   ├── src/pages/             # 页面组件 (Dashboard / Portfolio / PaperTrading / Skills / MCP / ...)
│   ├── src/components/        # 通用组件 (ChatWidget / ChatActionCard / ...)
│   └── packages/              # pnpm monorepo
│       ├── api/               # API 客户端 + 类型定义
│       ├── base-ui/           # shadcn/ui 组件库 (Radix UI + Tailwind)
│       └── biz-ui/            # 业务组件
├── config/
│   └── watchlist.yaml         # 自选股配置
├── data/                      # 运行时数据 (SQLite + 图表缓存)
└── tests/                     # 测试 (pytest)
```

### 技术栈

| 层 | 技术 |
|----|------|
| **后端框架** | Python 3.11+ / FastAPI / APScheduler |
| **数据库** | SQLite (SQLAlchemy ORM) |
| **AI 集成** | OpenAI 兼容 API (支持 GLM / DeepSeek / Claude 等) |
| **前端** | React 18 + TypeScript / Vite / Tailwind CSS / shadcn/ui (Radix UI) |
| **行情数据** | efinance / marketdata 包 (腾讯/东财 HTTP API) |
| **通知推送** | Apprise (Telegram / 企业微信 / 钉钉 / Bark / Webhook) |
| **包管理** | pip (Python) / pnpm (Frontend monorepo) |
| **部署** | Docker / docker-compose |

---

## 🚀 快速开始

### 环境要求
- Python 3.11+
- Node.js 18+ + pnpm
- Docker (可选，用于容器化部署)

### 本地开发

```bash
# 1. 克隆仓库
git clone https://github.com/panviviplus/PanWatchDIY.git
cd PanWatchDIY

# 2. 后端
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # 编辑 .env 填入 AI API Key 等配置
python server.py       # 启动后端 (端口 8000)

# 3. 前端
cd frontend && pnpm install && pnpm dev   # 启动前端 (端口 5183)

# 4. 一键启动
make dev-api    # 后端 (uvicorn --reload)
make dev-web    # 前端
```

### Docker 部署

```bash
./build.sh <version>    # 构建前端 + Docker 镜像
# 或
bash deploy.sh          # 测试 → 构建 → 部署 → 推送
```

### 配置自选股

编辑 `config/watchlist.yaml`:

```yaml
markets:
  - code: CN
    stocks:
      - symbol: "600519"
        name: "贵州茅台"
        security_type: stock
      - symbol: "510050"
        name: "上证50ETF"
        security_type: etf
  - code: HK
    stocks:
      - symbol: "00700"
        name: "腾讯控股"
  - code: US
    stocks:
      - symbol: "AAPL"
        name: "Apple Inc."
```

> `security_type` 可选值: `stock` (默认) / `etf` / `index`。ETF 在模拟盘中自动免除印花税和过户费。

---

## 🔧 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AI_API_KEY` | AI 服务 API Key | - |
| `AI_BASE_URL` | AI 服务地址 | `https://open.bigmodel.cn/api/paas/v4` |
| `AI_MODEL` | AI 模型名称 | `glm-4` |
| `AUTH_USERNAME` | Web 登录用户名 | - |
| `AUTH_PASSWORD` | Web 登录密码 | - |
| `JWT_SECRET` | JWT 签名密钥 | - |
| `DATA_DIR` | 运行时数据目录 | `./data` |
| `HTTP_PROXY` | HTTP 代理 | - |
| `TZ` | 时区 | `Asia/Shanghai` |

---

## 🧪 测试

```bash
python -m pytest tests/ -v           # 运行所有测试（默认不发通知）
python -m pytest tests/ -v --notify  # 运行所有测试（实际发送通知）
bash scripts/install-hooks.sh        # 安装 pre-push hook（推送前自动跑测试）
```

---

## 📂 开发指南

- **Agent 开发**: 继承 `src/agents/base.py` 的 `BaseAgent`，实现 `collect()` / `analyze()` 方法
- **策略开发**: 在 `src/core/signals/` 下新增策略模块，注册到 `src/core/strategy_catalog.py`
- **Skill 开发**: 在 `skills/<name>/` 下创建 `manifest.yaml` + `run.py`，Web UI 自动发现
- **新增 API**: 在 `src/web/api/` 下创建路由模块，在 `src/web/app.py` 中注册
- **Coding Conventions**: 见 `CLAUDE.md`

---

## 🙏 致谢

- 源项目 [PanWatch](https://github.com/TNT-Likely/PanWatch) by TNT-Likely
- [TradingAgents](https://github.com/TauricResearch/TradingAgents) — 多 Agent 投资决策框架
- PR #71 by [zackzhangkai](https://github.com/zackzhangkai) — ETF 增强、MCP、Skill 广场等核心功能

---

> 📍 PanWatchDIY = PanWatch + DIY 增强。盯盘上瘾，自己动手。
