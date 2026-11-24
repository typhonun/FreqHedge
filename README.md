<div align="center">

# FreqHedge

Manage multiple trading bots from a single web UI: configure dynamic grid or DCA strategies, run backtests, monitor positions, track trade events, and enforce unified risk control with cross-bot take-profit.

[Overview](#what-is-freqhedge) · [Preview](#-features) · [Core Capabilities](#core-capabilities) · [Get Started](#quick-start)

</div>

---

### What is FreqHedge

Freqtrade executes the trading strategies; FreqHedge orchestrates multiple Freqtrade instances into a complete, easy-to-use workflow:

```text
Configure strategy → Prepare data → Backtest → Start bot → Monitor live → Review & adjust
```

It is designed for individual users and small teams who want to manage quant trading through a web interface — especially when running multiple strategies, trading pairs, or directions at the same time. Independent bots across coins, directions, and strategies spread capital and strategy exposure across different markets, while global risk controls manage portfolio-level risk.


### Problems FreqHedge solves


- No more manually maintaining config files, ports, and launch commands for every bot;

- No more switching between terminals and log files to check positions;

- No more looking only at final returns — replay every add, reduce, and exit on the K-line chart;

- No more separating backtest parameters from runtime parameters — saved configs can be used directly for backtests and live runs;

- No more relying only on per-trade stop loss — take profit, stop loss, and trailing stop can be enforced on overall bot returns;
- No more managing each bot in isolation — joint take-profit, stop loss, and trailing stop can be applied to the combined returns of all bots.


> FreqHedge is a trading management tool. It does not promise returns and is not investment advice. Before connecting a real account, run in `dry_run` first and verify your strategy, fees, slippage, and exchange settings yourself.

## Features


[//]: # (### 📹 Demo Video)


[//]: # ([![Demo Video]&#40;https://img.shields.io/badge/▶_Watch_Demo-3min-red?style=for-the-badge&#41;]&#40;https://www.bilibili.com/video/xxxxx&#41;)


[//]: # (> Demo flow: Login → Select strategy → View live K-line → Replay trade events → Adjust parameters → Start backtest.)


[//]: # (### 📸 Screenshots)


#### Live K-line & trade events


[//]: # (![Chart]&#40;./screenshots/chart.png&#41;)


The K-line chart consolidates signal entries, DCA adds, grid buys/sells, take-profit, stop-loss, and global close events. Each bot type uses its own event types, so you can see exactly why the strategy adjusted a position at a given moment — no need to reconstruct the process from long logs.


#### Strategy configuration panel


[//]: # (![Strategy Config]&#40;./screenshots/strategy-config.png&#41;)


Depending on the bot type, configure DCA parameters or grid ranges, launch mode, stop loss, indicators, ROI rules, and candle timeframe through forms. FreqHedge then generates the corresponding Freqtrade configs automatically — no manual editing of complex JSON.


#### Real-time position monitoring


[//]: # (![Dashboard]&#40;./screenshots/dashboard.png&#41;)


View positions, direction, PnL, leverage, margin, and "target take-profit %" for multiple bots on a single dashboard, with filtering by bot, direction, or trading pair. For DCA bots the target take-profit shows the current ROI tier; for grid bots it shows the return rate at the expected next reduce price.


#### Backtest results


[//]: # (![Backtest]&#40;./screenshots/backtest.png&#41;)


Run backtests with the current strategy config and review returns, drawdown, win rate, profit factor, and exit reasons before deciding whether to start a dry-run or live instance.

## Core Capabilities

### Multi-instance management

Every bot is an independent runtime unit that can be configured, started, stopped, restarted, and monitored separately. A bot can enable Long and/or Short on demand, and each direction runs as an independent Freqtrade process:

```text
Bot #N
├── Long  → dedicated port → dedicated config → dedicated DB & logs
└── Short → dedicated port → dedicated config → dedicated DB & logs
```

- Instances do not interfere with each other — ideal for running multiple strategies and parameter sets;
- Configs, logs, and trade records are isolated per bot;
- The Freqtrade RPC endpoint is checked automatically after startup;
- Supports background start, status queries, per-direction restarts, and health monitoring;
- Bots can be created per exchange account, trading pair, capital, and leverage;
- The strategy type (DCA / grid) acts as a unified identifier across the stack: frontend forms, backend storage, Freqtrade config generation, and position reporting all stay consistent.

Independent bot combinations can span multiple coins, strategies, and directions: when one coin trends one way, other coins or directions keep running independently, reducing reliance on any single market at the portfolio level. Global take-profit, stop-loss, trailing-stop, and long/short exposure-difference risk controls constrain the whole bot portfolio so a single bot's risk cannot grow unbounded.

> **Exchange position mode**: when a futures bot enables both Long and Short, the config enables Hedge Mode, and the exchange account must already be in dual-side position mode.

### Configurable parameters

Strategy parameters are managed through web forms and saved as reusable bot configs:

| Scope | Configurable content |
| --- |----------------------|
| Trading basics | Pairs, capital, stake amount, leverage, max open trades, candle timeframe, trading mode (spot/futures) |
| DCA bot | Entry indicators, layered adds, per-layer add amount, amount/percent mode, cooldown |
| Exit rules | ROI ladder, stop loss, DCA take-profit, TP/KDJ partial exits, time stop |
| Market protection | Higher-timeframe trend filter, pump protection, per-pair position cap |
| Grid bot | Price bounds, grid count, arithmetic/geometric spacing, per-grid buy/reduce amount, launch mode, dynamic grid bounds |
| Pair selection | Manual pair selection, or multi-factor scanning for automatic pair selection (supported by both grid and DCA) |
| Instance risk | Per-bot take-profit, stop-loss, trailing stop, and auto-stop after trigger |
| Portfolio risk | Bot-level take/stop/trailing, joint take-profit, and long/short exposure difference limits |

Configuration flow:

```text
Web form → Save params → Generate bot/direction configs → Backtest → Start instance
```

### DCA bot

The DCA bot suits scenarios where you want to add in layers on price drawdowns and exit on a rebound:

- **Layered adds**: each next layer triggers on a price offset; supports automatic or manual levels;
- **Per-layer sizing**: every add layer can independently use a fixed amount or a percentage of the account, with different scales per level;
- **Flexible exits**: on take-profit, KDJ exit, or risk triggers, positions can be partially reduced by fixed amount, ratio, or target size — or fully closed;
- **Position control**: supports fixed amount or account percentage, with base amount, multiplier, max count, and cooldown;
- **Entry filters**: RSI, KDJ, MACD, EMA, and Bollinger Bands combinations;
- **Multi-level take-profit**: ROI ladder, floating-loss rebound take-profit, staged partial exits, and time stop;
- **Higher-timeframe protection**: 4h, 12h, 1d trend filters reduce counter-trend entries and adds;
- **Multi-factor pair selection**: can switch to scanner mode, where a multi-factor selector picks pairs automatically and dynamically replaces the whitelist on position rotation.

DCA uses limit-order logic; dry-run and backtests assume maker fees, while live trading follows actual exchange fills. The Long and Short directions share a single strategy config and run in separate Freqtrade processes.

### Grid bot

The grid bot supports two modes — manual single-pair and multi-factor multi-pair. Manual mode automatically buys low and sells high within a configured absolute price range, suited to ranges you are confident about; multi-factor mode lets the selector pick pairs dynamically, compute grid ranges automatically, and split capital across a max concurrency count.

- **Price range**: manual mode sets lower/upper bounds; multi-factor mode derives the range from scan results;
- **Grid spacing**: arithmetic and geometric spacing algorithms, configurable grid count, and selectable candle timeframe (1m / 3m / 5m / 15m / 30m);
- **Dynamic grid**: anchored on current positions and executed grids rather than pre-placing all orders; as price runs toward the range edge, adjacent grids keep being generated and grid state updates on fills;
- **Grid trading**: longs add when price drops and reduce at the next grid level on the way up; shorts work in reverse;
- **Launch modes**: grid-triggered, trigger-price, and immediate start;
- **Position limits**: caps the number of simultaneously held grids and sizes each grid from capital and grid count; multi-factor mode splits capital by concurrency;
- **Range stop-loss**: can clear positions when price breaks below the lower bound, as protection against range failure;
- **Dynamic whitelist**: in multi-factor mode, supports scan locks, prefetched configs, and hot reloads at runtime; the pair whitelist updates automatically after a position closes;
- **Grid preview**: the config page shows grid lines, spacing, expected per-grid profit, and estimated investment for pre-launch checks.

Grid bots use market-order logic; dry-run and backtests assume taker fees, while live trading follows actual exchange fills.

Typical grid workflow:

```text
Choose mode (manual / multi-factor) → Set range or scan params → Preview grid → Backtest → Start bot
```

### Backtesting & data preparation

Backtests and historical data downloads are managed centrally by FreqHedge:

- Checks whether local candles cover the pair, timeframe, and timerange;
- Triggers downloads when data is missing, with progress display;
- Runs Freqtrade in the background without blocking web requests;
- Supports querying, cancelling, and viewing task logs;
- Gives clear errors for config issues, missing data, process failures, and missing reports;
- Uses the same config as the bot, reducing divergence between backtest and live.

### Real-time monitoring & trade review

- Aggregates account, positions, realized PnL, and floating PnL across bots;
- Shows equity curve, return curve, margin, and risk exposure;
- Filter positions by bot, direction, and trading pair;
- The position table shows current return rate and target take-profit rate (ROI tier for DCA, estimated next reduce price for grid);
- Supports manual open/close and bot start/stop;
- Trade events are saved and mapped onto the K-line chart for locating each strategy action;
- Clicking a position jumps to the corresponding K-line chart with grid or DCA events rendered per strategy type.

### Unified risk control

Risk control computes "round returns" per bot, including both realized and floating PnL:

- Trigger take-profit or stop-loss by amount or return rate;
- Supports profit-drawdown and loss-direction trailing stops;
- Executes a full close on trigger and waits until positions are confirmed flat;
- Can auto-stop the bot after triggering, per config;
- Prevents the same risk condition from triggering repeatedly.

Beyond per-bot risk control, FreqHedge also supports **cross-bot joint take-profit**: realized and floating PnL of multiple independent bots are aggregated into a portfolio return, and all positions are closed uniformly once a target amount is reached.

## How it works

```text
┌────────────────────┐
│  Vue Web Console    │  Config / Dashboard / K-line / Backtest
└─────────┬──────────┘
          │ REST API
┌─────────▼──────────┐
│  FastAPI Service    │  bot / config / backtest / risk / monitoring
└────┬──────────┬────┘
     │          │
┌────▼─────┐ ┌──▼──────────────────┐
│ Local    │  │ Freqtrade Pool      │
│ data     │  │ one process per     │
│ (users/  │  │ bot × direction     │
│  events) │  │                     │
└──────────┘ └────────────────────┘
```

FreqHedge is built with Vue 3, FastAPI, SQLite, SQLAlchemy, APScheduler, and Freqtrade. It does not replace Freqtrade's trade execution — it provides the configuration, orchestration, observability, and risk-control layer. Strategy types are defined in a unified registry (`backend/app/core/strategy_registry.py`); adding a new bot type only requires registering its metadata, without touching the config generation or position reporting pipeline.

## Quick Start

Follow these steps to run FreqHedge locally.

### Prerequisites
Install the following software:
- [Python 3.12.x](https://www.python.org/downloads/) (3.11 - 3.12 supported; check `Add Python to PATH` during install)
- [Node.js 20 LTS](https://nodejs.org/) (18+ supported) and [pnpm 10](https://pnpm.io/installation)
- [Git](https://git-scm.com/)

### Install dependencies

```powershell
git clone https://github.com/typhonun/FreqHedge
cd FreqHedge

py -3.12 -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r freqtrade\requirements.txt
python -m pip install -e .\freqtrade

cd frontend
pnpm install
```

### Start the services

Run the backend and frontend in two separate terminal windows.

#### Start the backend

```powershell
# From the repository root
venv\Scripts\activate
cd backend
python -m uvicorn app.main:app --reload --port 9000
```

#### Start the frontend

```powershell
# In a new PowerShell window from the repository root
cd frontend
pnpm dev
```

Open http://localhost:5173 in your browser to enter the FreqHedge console. When creating a bot, choose the DCA or grid strategy, then configure pairs, direction, capital, and strategy parameters.

## Project Structure

```text
FreqHedge/
├── backend/
│   ├── app/api/                 # bot, backtest, chart, position, risk, log, exchange endpoints
│   ├── app/services/            # instance, process, config, backtest, RPC, risk, grid scanner services
│   ├── app/core/                # strategy registry, defaults, config management
│   ├── app/models/              # users, trade events, profit and balance snapshots
│   └── config/settings.py       # project paths and runtime config
├── frontend/src/
│   ├── features/                # dashboard, strategy config, pair selector and other feature modules
│   ├── views/                   # dashboard, positions, charts, bot and settings pages
│   ├── config/                  # frontend strategy registry and default configs
│   ├── api/                     # backend API wrappers
│   └── stores/                  # Pinia state management
└── freqtrade/user_data/
    ├── strategies/              # DCA/grid strategy bases, direction strategies, event recorder
    │   ├── DcaTpBotBase.py      # DCA bot base strategy
    │   └── GridBotBase.py       # grid bot base strategy
    ├── bots/{bot_id}/           # per-instance configs, logs and trade databases
    └── config_template.json     # Freqtrade config template
```

## Disclaimer

FreqHedge is intended for software engineering practice, quantitative research, and learning exchange. It does not guarantee any returns and is not investment advice. Cryptocurrency trading carries high risk; users bear full responsibility for their API keys, funds, strategies, and trading outcomes.

If FreqHedge helps you, a Star is appreciated.
