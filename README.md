<div align="center">

# 📈 股票智能分析系统（DSA）

[![CI](https://github.com/ZhuLinsen/daily_stock_analysis/actions/workflows/ci.yml/badge.svg)](https://github.com/ZhuLinsen/daily_stock_analysis/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> 基于 AI 大模型的股票分析系统，覆盖 A 股 / 港股 / 美股（含 ETF），支持 Web 工作台与 FastAPI 服务。

[**快速开始**](#-快速开始本地开发) · [**数据存储**](#-数据存储sqlite) · [**关键入口**](#-关键入口) · [**文档中心**](docs/INDEX.md)

简体中文 | [English](docs/README_EN.md) | [繁體中文](docs/README_CHT.md)

</div>

## 快速开始（本地开发）

### 1) 后端（FastAPI）

```bash
py -m pip install -r requirements.txt
py -m uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

- API 基址：`http://127.0.0.1:8000`
- ETF 板块决策 API：
  - `GET /api/v1/board-diagnosis/boards`
  - `GET /api/v1/board-diagnosis/{board_key}`

### 2) 前端（Web 工作台）

```bash
cd apps/dsa-web
pnpm install
pnpm dev
```

- Web 地址：`http://127.0.0.1:5173`
- ETF 板块决策页面：`/board-diagnosis`
- 开发环境已配置 `/api` 代理到 `http://127.0.0.1:8000`（见 `apps/dsa-web/vite.config.ts`）。

> Docker / GitHub Actions / 桌面端打包与部署请参考 [docs/full-guide.md](docs/full-guide.md) 与 [docs/DEPLOY.md](docs/DEPLOY.md)。

## ✨ 功能特性

| 能力             | 覆盖内容                                                                                          |
| ---------------- | ------------------------------------------------------------------------------------------------- |
| AI 决策报告      | 核心结论、评分、趋势、买卖点位、风险警报、催化因素、操作检查清单                                  |
| 多市场数据聚合   | A股、港股、美股、ETF；行情、K 线、技术指标、资金流、筹码、新闻、公告和基本面                      |
| Web / 桌面工作台 | 手动分析、任务进度、历史报告、完整 Markdown、回测、持仓、配置管理、浅色 / 深色主题                |
| Agent 策略问股   | 多轮追问，支持均线、缠论、波浪、趋势、热点、事件、成长、预期等 15 种内置策略，覆盖 Web/Bot/API    |
| 智能导入与补全   | 图片、CSV/Excel、剪贴板导入；股票代码/名称/拼音/别名补全                                          |
| 自动化与推送     | GitHub Actions、Docker、本地定时任务、FastAPI 服务和企业微信/飞书/Telegram/Discord/Slack/邮件推送 |

> 功能细节、字段契约、基本面 P0 超时语义、交易纪律、数据源优先级、Web/API 行为请看 [完整配置与部署指南](docs/full-guide.md)。

### 技术栈与数据来源

| 类型     | 支持                                                                                                                                                                                                                                                                                                        |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AI 模型  | [Anspire](https://open.anspire.cn/?share_code=QFBC0FYC)、[AIHubMix](https://aihubmix.com/?aff=CfMq)、Gemini、OpenAI 兼容、DeepSeek、通义千问、Claude、Ollama 本地模型等                                                                                                                                     |
| 行情数据 | [TickFlow](https://tickflow.org/auth/register?ref=WDSGSPS5XC)、AkShare、Tushare、Pytdx、Baostock、YFinance、Longbridge                                                                                                                                                                                      |
| 新闻搜索 | [Anspire](https://open.anspire.cn/?share_code=QFBC0FYC)、[SerpAPI](https://serpapi.com/baidu-search-api?utm_source=github_daily_stock_analysis)、[Tavily](https://tavily.com/)、[Bocha](https://open.bocha.cn/)、[Brave](https://brave.com/search/api/)、[MiniMax](https://platform.minimaxi.com/)、SearXNG |
| 社交舆情 | [Stock Sentiment API](https://api.adanos.org/docs)（Reddit / X / Polymarket，仅美股，可选）                                                                                                                                                                                                                 |

> 完整规则见 [数据源配置](docs/full-guide.md#数据源配置)。

## 数据存储（SQLite）

本项目默认使用 **SQLite** 作为持久化存储（SQLAlchemy 管理，见 `src/storage.py`），用于保存历史、缓存与运行态记录。

- 数据库路径：环境变量 `DATABASE_PATH` 控制，默认 `./data/stock_analysis.db`
- 常见持久化表：
  - `analysis_history`：分析历史 / 报告快照
  - `stock_daily`：日线缓存（用于加速与断点续传）
  - `alert_rules` / `alert_triggers` / `alert_notifications` / `alert_cooldowns`：告警中心规则与记录
  - 组合 / 回测 / LLM 用量审计等表（详见 `src/storage.py`）
- ETF 板块决策：当前主要是**实时按需拉取**数据源信号并返回结果，并非默认把每次诊断结果落库成独立表。

## 🧭 关键入口

- `main.py`：分析任务主入口（批量分析 / schedule 等）
- `server.py`：FastAPI 服务入口（API/Web/桌面端共用）
- `apps/dsa-web/`：Web 前端
- `apps/dsa-desktop/`：桌面端
- `docs/`：文档与字段契约说明

## 📄 License

[MIT License](LICENSE)

## ⚠️ 免责声明

本项目仅供学习和研究使用，不构成任何投资建议。股市有风险，投资需谨慎。作者不对使用本项目产生的任何损失负责。
