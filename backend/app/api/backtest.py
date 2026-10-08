# ══════════════════════════════════════════════════════════════
# 文件顶部：只定义一次
# ══════════════════════════════════════════════════════════════
import json
import shutil
import subprocess
import tempfile
import re
import time
import pandas as pd
from pathlib import Path
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import backtest_job
from app.services.backtest_job import create_job, run_job_async, get_job
from app.services.bot_manager import BotManager
from app.services.config_service import ConfigService
from config.settings import FREQTRADE_DIR

router = APIRouter()

# ══════════════════════════════════════════════════════════════
# 基础工具
# ══════════════════════════════════════════════════════════════
def _parse_timerange(timerange: str) -> tuple:
    if "-" not in timerange:
        return timerange, timerange
    start, end = timerange.split("-", 1)
    return start or "", end or ""


def _timerange_to_ts(timerange: str):
    start_s, end_s = _parse_timerange(timerange)
    if not start_s or not end_s:
        return None
    try:
        start_dt = datetime.strptime(start_s, "%Y%m%d")
        end_dt = datetime.strptime(end_s, "%Y%m%d").replace(hour=23, minute=59, second=59)
        return (int(start_dt.timestamp()), int(end_dt.timestamp()))
    except Exception:
        return None


def _tf_to_seconds(tf: str) -> int:
    if not tf:
        return 3600
    unit = tf[-1].lower()
    try:
        n = int(tf[:-1])
    except Exception:
        return 3600
    return {"m": 60, "h": 3600, "d": 86400, "w": 604800}.get(unit, 3600) * n


def _get_data_dir(exchange_name: str = "binance",
                  trading_mode: str = "futures") -> Path:
    return (
        FREQTRADE_DIR / "user_data" / "data" /
        exchange_name / trading_mode
    )


def _pair_to_filename(pair: str) -> str:
    return pair.replace("/", "_").replace(":", "_")


def _get_local_range(pair: str, timeframe: str,
                     data_dir: Path) -> Optional[tuple]:
    stem = _pair_to_filename(pair)
    fname = f"{stem}-{timeframe}-{data_dir.name}.feather"
    fpath = data_dir / fname

    if not fpath.exists():
        return None

    try:
        df = pd.read_feather(fpath, columns=["date"])
        if df.empty:
            return None
        start = int(df["date"].iloc[0].timestamp())
        end = int(df["date"].iloc[-1].timestamp())
        return (start, end)
    except Exception as e:
        print(f"[check] read feather failed {fpath}: {e}")
        return None


# ══════════════════════════════════════════════════════════════
# 本地数据检查 + 缓存
# ══════════════════════════════════════════════════════════════
_check_cache = {}


def _check_local_data(pairs: list,
                      timeframes: list,
                      timerange: str,
                      exchange_name: str = "binance",
                      trading_mode: str = "futures") -> dict:
    # 缓存 key
    key = (
        ",".join(sorted(pairs)),
        ",".join(sorted(timeframes)),
        timerange,
        exchange_name,
        trading_mode,
    )
    now = time.time()
    if key in _check_cache and now - _check_cache[key][0] < 5:
        return _check_cache[key][1]

    target = _timerange_to_ts(timerange)
    if target is None:
        return {"all_covered": False, "details": []}

    req_start, req_end = target
    data_dir = _get_data_dir(exchange_name, trading_mode)

    details = []
    all_covered = True

    for pair in pairs:
        for tf in timeframes:
            local = _get_local_range(pair, tf, data_dir)
            covered = False
            if local is not None:
                tol = max(_tf_to_seconds(tf), 3600)
                covered = (
                    local[0] <= req_start + tol
                    and local[1] >= req_end - tol
                )
            if not covered:
                all_covered = False
            details.append({
                "pair": pair, "tf": tf,
                "local": local, "covered": covered,
            })

    result = {"all_covered": all_covered, "details": details}
    _check_cache[key] = (now, result)
    return result


def _resolve_freqtrade_exe() -> str:
    candidates = [
        FREQTRADE_DIR / "venv" / "Scripts" / "freqtrade.exe",
        FREQTRADE_DIR / ".venv" / "Scripts" / "freqtrade.exe",
        FREQTRADE_DIR.parent / "venv" / "Scripts" / "freqtrade.exe",
        FREQTRADE_DIR.parent / ".venv" / "Scripts" / "freqtrade.exe",
    ]
    for p in candidates:
        if p.exists():
            return str(p)

    which = shutil.which("freqtrade")
    if which:
        return which

    raise FileNotFoundError(
        "找不到 freqtrade 可执行文件，尝试过：\n"
        + "\n".join(str(p) for p in candidates)
    )


try:
    FREQTRADE_EXE = _resolve_freqtrade_exe()
    print(f"[backtest] FREQTRADE_EXE = {FREQTRADE_EXE}")
except Exception as e:
    FREQTRADE_EXE = None
    print(f"[backtest] freqtrade exe 解析失败: {e}")


def _get_htf_timeframes(bot: dict, side: str = "long") -> list:
    try:
        key = "shortConfig" if side == "short" else "longConfig"
        cfg_raw = bot.get(key) or {}
        if isinstance(cfg_raw, str):
            import json as _json
            cfg_raw = _json.loads(cfg_raw) if cfg_raw else {}

        htf_cfg = (cfg_raw or {}).get("htf_trend_filter") or {}

        # ★ 未启用 → 不需要下载 HTF 周期
        if not bool(htf_cfg.get("enable", False)):
            return []

        # ★ enable=true 但所有 protect_* 都关 → 也没必要下载
        any_protect = any([
            bool(htf_cfg.get("protect_entry", False)),
            bool(htf_cfg.get("protect_dca", False)),
            bool(htf_cfg.get("protect_grid", False)),
            bool(htf_cfg.get("protect_rebuy", False)),
            bool(htf_cfg.get("protect_trend", False)),
        ])
        if not any_protect:
            return []

        tf = str(htf_cfg.get("timeframe", "4h")).lower()
        if tf in ("4h", "12h", "1d"):
            return [tf]
    except Exception as e:
        print(f"[backtest] _get_htf_timeframes failed: {e}")
    return ["4h"]


def _require_config_path(bot: dict, bot_id: int, side: str) -> Path:
    """
    同 _resolve_config_path，但失败时直接 raise HTTPException。
    """
    enable_long = bool(bot.get("enableLong", True))
    enable_short = bool(bot.get("enableShort", False))

    if side == "long" and not enable_long:
        raise HTTPException(400, "当前机器人未启用做多，无法使用 long 方向")
    if side == "short" and not enable_short:
        raise HTTPException(400, "当前机器人未启用做空，无法使用 short 方向")

    p = FREQTRADE_DIR / "user_data" / "bots" / str(bot_id) / f"config_bot{bot_id}_{side}.json"
    if not p.exists():
        raise HTTPException(400, f"配置文件不存在: {p}")
    return p


class BacktestRequest(BaseModel):
    side: str = "long"
    timeframe: str = "30m"
    timerange: Optional[str] = None
    dry_run_wallet: float = 100.0
    auto_download: bool = True


def _default_timerange() -> str:
    from datetime import datetime, timedelta
    end = datetime.utcnow()
    start = end - timedelta(days=60)
    return f"{start.strftime('%Y%m%d')}-{end.strftime('%Y%m%d')}"


def _parse_timerange(timerange: str) -> tuple[str, str]:
    if "-" not in timerange:
        return timerange, timerange
    start, end = timerange.split("-", 1)
    return start or "", end or ""


def _run_freqtrade_download(config_path: Path,
                            timeframe: str,
                            timerange: Optional[str],
                            extra_timeframes: Optional[list] = None) -> dict:
    """
    下载回测所需的全部数据。
    ★ extra_timeframes: 除主周期外还需要下载的周期（由调用方从 bot 配置推断）
    """
    if not FREQTRADE_EXE:
        return {"success": False, "stdout_tail": "", "stderr_tail": "freqtrade 可执行文件未找到"}

    # 组装需要下载的周期集合
    tf_set = []
    for tf in [timeframe] + (extra_timeframes or []):
        if tf and tf not in tf_set:
            tf_set.append(tf)

    cmd = [
        FREQTRADE_EXE,
        "download-data",
        "--config", str(config_path),
        "-t", *tf_set,
        "--trading-mode", "futures",
    ]

    # ★ 只有明确给了 timerange 才加，否则默认最近 N 天（freqtrade 默认行为）
    if timerange:
        start, end = _parse_timerange(timerange)
        if start and end:
            cmd += ["--timerange", f"{start}-{end}"]

    print(f"[backtest] download cmd = {' '.join(cmd)}")

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(FREQTRADE_DIR),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
    except Exception as e:
        print(f"[backtest] download subprocess failed: {e}")
        return {
            "success": False,
            "stdout_tail": "",
            "stderr_tail": str(e),
        }

    ok = proc.returncode == 0
    if not ok:
        print(
            "[backtest] download-data failed:\n"
            f"stdout tail:\n{proc.stdout[-1500:]}\n"
            f"stderr tail:\n{proc.stderr[-1500:]}"
        )
    else:
        print("[backtest] download-data OK")

    return {
        "success": ok,
        "stdout_tail": proc.stdout[-1500:],
        "stderr_tail": proc.stderr[-1500:],
    }


def _split_table_row(line: str) -> list[str]:
    """按 │ 分割，去掉首尾空字段"""
    # 兼容 │ 和 |（有些 locale 下 freqtrade 会用 |）
    for sep in ("\u2502", "|"):
        if sep in line:
            parts = [p.strip() for p in line.split(sep)]
            # 去掉首尾空
            while parts and not parts[0]:
                parts.pop(0)
            while parts and not parts[-1]:
                parts.pop()
            return parts
    return []


def _parse_stdout_report(stdout: str) -> dict:
    result = {
        "summary": {
            "total_trades": 0,
            "total_profit_pct": 0.0,
            "absolute_profit": 0.0,
            "win_rate": 0.0,
            "max_drawdown": 0.0,
            "starting_balance": 0.0,
            "final_balance": 0.0,
            "sharpe": 0.0,
            "profit_factor": 0.0,
            "cagr": 0.0,
            "sortino": 0.0,
            "backtest_start": None,
            "backtest_end": None,
        },
        "pairs": [],
        "exit_reasons": [],
        "trades": [],
    }

    # ── STRATEGY SUMMARY 一行 ──
    for line in stdout.splitlines():
        parts = _split_table_row(line)
        if len(parts) >= 7 and parts[0].startswith("DcaTp"):
            try:
                result["summary"]["total_trades"] = int(parts[1])
                result["summary"]["absolute_profit"] = float(parts[3])
                result["summary"]["total_profit_pct"] = float(parts[4])
                win_parts = parts[6].split()
                if len(win_parts) >= 4:
                    result["summary"]["win_rate"] = float(win_parts[3])
                if len(parts) >= 8:
                    m = re.search(r"([\d.]+)%", parts[7])
                    if m:
                        result["summary"]["max_drawdown"] = float(m.group(1))
                break
            except Exception as e:
                print(f"[backtest] parse strategy row failed: {e}, parts={parts}")

    # ── BACKTESTING REPORT（按交易对）──
    in_backtest_section = False
    for line in stdout.splitlines():
        if "BACKTESTING REPORT" in line:
            in_backtest_section = True
            continue
        if in_backtest_section and "LEFT OPEN TRADES" in line:
            break
        if not in_backtest_section:
            continue

        parts = _split_table_row(line)
        # 只处理首列为交易对的行（跳过 TOTAL 和续行）
        if len(parts) >= 6 and re.match(r"^[A-Z0-9]+/[A-Z0-9]+:[A-Z0-9]+$", parts[0]):
            try:
                win_parts = parts[6].split() if len(parts) >= 7 else []
                result["pairs"].append({
                    "pair": parts[0],
                    "trades": int(parts[1]),
                    "avg_profit_pct": float(parts[2]),
                    "total_profit_usdt": float(parts[3]),
                    "total_profit_pct": float(parts[4]),
                    "avg_duration": parts[5] if len(parts) >= 6 else "",
                    "win_rate": float(win_parts[-1]) if win_parts else 0.0,
                })
            except Exception as e:
                print(f"[backtest] parse pair row failed: {e}, parts={parts}")

    # ── EXIT REASON STATS ──
    in_exit_section = False
    for line in stdout.splitlines():
        if "EXIT REASON STATS" in line:
            in_exit_section = True
            continue
        if in_exit_section and "MIXED TAG STATS" in line:
            break
        if not in_exit_section:
            continue

        parts = _split_table_row(line)
        # 跳过表头 / TOTAL / 空行，只处理第一列是退出原因的行
        if len(parts) >= 6 and parts[0] and parts[0] != "TOTAL":
            # 排除第一列是 "Exit" / "Reason" 之类的表头
            if parts[0] in ("Exit", "Reason"):
                continue
            try:
                win_parts = parts[6].split() if len(parts) >= 7 else []
                result["exit_reasons"].append({
                    "reason": parts[0],
                    "exits": int(parts[1]),
                    "avg_profit_pct": float(parts[2]),
                    "total_profit_usdt": float(parts[3]),
                    "total_profit_pct": float(parts[4]),
                    "avg_duration": parts[5] if len(parts) >= 6 else "",
                    "wins": int(win_parts[0]) if len(win_parts) >= 1 else 0,
                    "losses": int(win_parts[2]) if len(win_parts) >= 3 else 0,
                    "win_rate": float(win_parts[3]) if len(win_parts) >= 4 else 0.0,
                })
            except Exception as e:
                print(f"[backtest] parse exit row failed: {e}, parts={parts}")

    # ── SUMMARY METRICS ──
    for line in stdout.splitlines():
        parts = _split_table_row(line)
        if len(parts) >= 2:
            k, v = parts[0], parts[1]
            try:
                if "Starting balance" in k:
                    result["summary"]["starting_balance"] = float(v.split()[0])
                elif "Final balance" in k:
                    result["summary"]["final_balance"] = float(v.split()[0])
                elif "Sharpe (closed trades)" in k:
                    result["summary"]["sharpe"] = float(v)
                elif "Sortino (closed trades)" in k:
                    result["summary"]["sortino"] = float(v)
                elif "Profit factor" in k:
                    result["summary"]["profit_factor"] = float(v)
                elif k.strip() == "CAGR %":
                    result["summary"]["cagr"] = float(str(v).replace("%", "").strip())
                elif "Backtesting from" in k:
                    result["summary"]["backtest_start"] = v
                elif "Backtesting to" in k:
                    result["summary"]["backtest_end"] = v
            except Exception:
                pass

    return result


def _run_freqtrade_backtest(config_path: Path, strategy: str,
                            timeframe: str, timerange: str,
                            export_dir: Path) -> dict:
    if not FREQTRADE_EXE:
        raise RuntimeError("freqtrade 可执行文件未找到")

    cmd = [
        FREQTRADE_EXE,
        "backtesting",
        "--config", str(config_path),
        "--strategy", strategy,
        "-i", timeframe,
        "--timerange", timerange,
        "--cache", "none",
        "--export", "trades",
    ]

    print(f"[backtest] cmd = {' '.join(cmd)}")

    proc = subprocess.run(
        cmd,
        cwd=str(FREQTRADE_DIR),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
    )

    if proc.returncode != 0:
        raise RuntimeError(
            "freqtrade backtesting failed:\n"
            f"stdout tail:\n{proc.stdout[-2000:]}\n"
            f"stderr tail:\n{proc.stderr[-2000:]}"
        )

    # ★ 尝试从 JSON 读
    result_file = None
    for cand in [
        FREQTRADE_DIR / "user_data" / "backtest_results" / "last_backtest_result.json",
        FREQTRADE_DIR / "last_backtest_result.json",
        FREQTRADE_DIR.parent / "last_backtest_result.json",
    ]:
        if cand.exists():
            result_file = cand
            break

    if result_file:
        print(f"[backtest] result file = {result_file}")
        with open(result_file, "r", encoding="utf-8") as f:
            raw_json = json.load(f)
        # ★ 从原始 JSON 解析成最终结构
        return _parse_summary(raw_json)

    # ★ 找不到 JSON：从 stdout 解析（已经是最终结构，直接返回）
    print("[backtest] JSON 未找到，改用 stdout 解析")
    return _parse_stdout_report(proc.stdout)


def _cleanup_old_results(results_dir: Path, keep: int = 10):
    """
    清理旧的回测结果文件（保留最近 keep 次回测的所有文件）。

    freqtrade 每次回测可能生成：
      backtest-result-<ts>.zip
      backtest-result-<ts>.meta.json
      backtest-result-<ts>.json          （旧版/未压缩时）
      backtest-result-<ts>_config.json   （某些版本）

    以「主结果」（.zip 或 .json）为分组依据，保留最近 keep 组，
    其余连 meta / config 一起删。
    """
    if not results_dir.exists():
        return

    # ---------- 1. 找出所有主结果文件（.zip 优先，兼容 .json） ----------
    # 排除 .meta.json 和 _config.json
    main_files = []
    for f in results_dir.glob("backtest-result-*"):
        name = f.name
        if name.endswith(".meta.json"):
            continue
        if name.endswith("_config.json"):
            continue
        # 只接受 .zip 或 .json
        if name.endswith(".zip") or name.endswith(".json"):
            main_files.append(f)

    if len(main_files) <= keep:
        return

    # ---------- 2. 按 mtime 降序 ----------
    main_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    to_delete = main_files[keep:]

    # ---------- 3. 逐个删除三件套 ----------
    deleted = 0
    freed = 0
    for main_file in to_delete:
        # main_file.stem:
        #   .zip → "backtest-result-2026-10-04_19-19-44"
        #   .json → "backtest-result-2026-10-04_19-19-44"
        stem = main_file.stem

        siblings = [
            results_dir / f"{stem}.zip",
            results_dir / f"{stem}.json",
            results_dir / f"{stem}.meta.json",
            results_dir / f"{stem}_config.json",
        ]

        for f in siblings:
            if f.exists():
                try:
                    freed += f.stat().st_size
                    f.unlink()
                    deleted += 1
                except Exception as e:
                    print(f"[cleanup] 删除失败 {f}: {e}")

    if deleted:
        print(
            f"[cleanup] 清理 {deleted} 个文件，"
            f"释放 {freed / 1024 / 1024:.2f} MB"
        )


def _parse_summary(data: dict) -> dict:
    strategy = data.get("strategy", {})

    total_trades = (
            strategy.get("total_trades")
            or data.get("total_trades")
            or 0
    )

    pair_stats = []
    trades = data.get("trades", [])
    pair_map = {}

    for t in trades:
        pair = t.get("pair", "UNKNOWN")
        profit_ratio = t.get("profit_ratio", 0.0)
        profit_abs = t.get("profit_abs", 0.0)
        duration = t.get("trade_duration", 0)

        if pair not in pair_map:
            pair_map[pair] = {
                "pair": pair,
                "trades": 0,
                "total_profit_pct": 0.0,
                "total_profit_usdt": 0.0,
                "total_duration_min": 0,
                "wins": 0,
                "losses": 0,
            }

        s = pair_map[pair]
        s["trades"] += 1
        s["total_profit_pct"] += profit_ratio * 100
        s["total_profit_usdt"] += profit_abs
        s["total_duration_min"] += duration
        if profit_abs > 0:
            s["wins"] += 1
        elif profit_abs < 0:
            s["losses"] += 1

    for s in pair_map.values():
        s["avg_profit_pct"] = round(
            s["total_profit_pct"] / s["trades"], 2
        ) if s["trades"] else 0
        s["avg_duration_min"] = round(
            s["total_duration_min"] / s["trades"], 1
        ) if s["trades"] else 0
        s["win_rate"] = round(
            s["wins"] / s["trades"] * 100, 1
        ) if s["trades"] else 0
        s["total_profit_pct"] = round(s["total_profit_pct"], 2)
        s["total_profit_usdt"] = round(s["total_profit_usdt"], 2)
        pair_stats.append(s)

    winrate_raw = strategy.get("winrate", 0)
    win_rate = winrate_raw * 100 if winrate_raw <= 1 else winrate_raw

    summary = {
        "backtest_start": data.get("backtest_start"),
        "backtest_end": data.get("backtest_end"),
        "starting_balance": data.get("starting_balance", 0),
        "final_balance": data.get("final_balance", 0),
        "absolute_profit": data.get("absolute_profit", 0),
        "total_profit_pct": data.get("total_profit_pct", 0),
        "total_trades": total_trades,
        "max_open_trades": data.get("max_open_trades", 0),
        "win_rate": win_rate,
        "profit_factor": strategy.get("profit_factor", 0),
        "sharpe": strategy.get("sharpe", 0),
        "sortino": strategy.get("sortino", 0) or data.get("sortino", 0) or 0,
        "cagr": (data.get("cagr", 0) or 0) * 100 if (data.get("cagr", 0) or 0) <= 1 else (data.get("cagr", 0) or 0),
        "max_drawdown": (data.get("max_drawdown_account", 0) or 0) * 100,
        "best_pair": data.get("best_pair"),
        "worst_pair": data.get("worst_pair"),
        "best_trade_pct": data.get("best_trade", 0),
        "worst_trade_pct": data.get("worst_trade", 0),
    }

    return {
        "summary": summary,
        "pairs": pair_stats,
        "exit_reasons": [],  # ★ 新增，JSON 路径暂不解析，给空数组
        "trades": trades,
    }


@router.post("/{bot_id}/backtest")
async def run_backtest(bot_id: int, req: BacktestRequest):
    bot = BotManager.get(bot_id)
    if not bot:
        raise HTTPException(404, "bot not found")

    # 1. 保证配置文件最新
    ConfigService.generate_configs(bot_id, {
        "base": {
            "name": bot["name"],
            "pair": bot["pair"],
            "capital": bot["capital"],
            "stakeAmount": bot.get("stakeAmount", 10),
            "leverage": bot.get("leverage", 10),
            "maxOpenTrades": bot.get("maxOpenTrades", 3),
            "dryRun": bot.get("dryRun", True),
            "enableLong": bot.get("enableLong", True),
            "enableShort": bot.get("enableShort", False),
        },
        "risk": {
            "tp_enabled": bot.get("tp_enabled", False),
            "tp_mode": bot.get("tp_mode", "amount"),
            "tp_amount": bot.get("tp_amount", 0),
            "tp_ratio": bot.get("tp_ratio", 0),
            "sl_enabled": bot.get("sl_enabled", False),
            "sl_mode": bot.get("sl_mode", "amount"),
            "sl_amount": bot.get("sl_amount", 0),
            "sl_ratio": bot.get("sl_ratio", 0),
            "trail_enabled": bot.get("trail_enabled", False),
            "trail_mode": bot.get("trail_mode", "ratio"),
            "trail_activate_amount": bot.get("trail_activate_amount", 0),
            "trail_activate_ratio": bot.get("trail_activate_ratio", 0),
            "trail_drawdown_amount": bot.get("trail_drawdown_amount", 0),
            "trail_drawdown_ratio": bot.get("trail_drawdown_ratio", 0),
            "auto_stop_on_tp": bot.get("auto_stop_on_tp", True),
            "auto_stop_on_sl": bot.get("auto_stop_on_sl", True),
            "auto_stop_on_trail": bot.get("auto_stop_on_trail", True),
        },
        "longConfig": bot.get("longConfig"),
        "shortConfig": bot.get("shortConfig"),
    })

    config_path = _require_config_path(bot, bot_id, req.side)
    print(f"[backtest] config_path = {config_path}, exists = {config_path.exists()}")

    strategy = "DcaTpLong" if req.side == "long" else "DcaTpShort"
    timerange = req.timerange or _default_timerange()

    # ★ 回测前自动下载数据（含 informative 周期）
    print(f"[backtest] auto_download flag = {req.auto_download} (ignored, use /download-data)")

    with tempfile.TemporaryDirectory() as tmp:
        export_dir = Path(tmp)
        # ★ 打印当前 config 的关键策略字段（临时排查用）
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            print("=" * 60)
            print(f"[debug] config = {config_path}")
            print(f"[debug] timeframe = {cfg.get('timeframe')}")
            print(f"[debug] max_open_trades = {cfg.get('max_open_trades')}")
            # 你的策略配置会以自定义字段的方式写进 config（如果你的 config_service 是这样做的）
            for key in ("longConfig", "shortConfig", "htf_trend_filter",
                        "entry", "htf_trend_filter_enable", "protect_entry"):
                if key in cfg:
                    print(f"[debug] {key} = {cfg[key]}")
            print("=" * 60)
        except Exception as _e:
            print(f"[debug] dump config failed: {_e}")

        try:
            raw = _run_freqtrade_backtest(
                config_path=config_path,
                strategy=strategy,
                timeframe=req.timeframe,
                timerange=timerange,
                export_dir=export_dir,
            )
        except Exception as e:
            raise HTTPException(500, str(e))

    result = raw
    result["config"] = {
        "side": req.side,
        "timeframe": req.timeframe,
        "timerange": timerange,
        "strategy": strategy,
    }
    return result


class DownloadDataRequest(BaseModel):
    side: str = "long"
    timeframe: str = "30m"
    timerange: Optional[str] = None


@router.post("/{bot_id}/download-data")
async def download_data(bot_id: int, req: DownloadDataRequest):
    bot = BotManager.get(bot_id)
    if not bot:
        raise HTTPException(404, "bot not found")

    ConfigService.generate_configs(bot_id, _build_config_for_backtest(bot))
    config_path = _require_config_path(bot, bot_id, req.side)

    # ★ 从 config 读 exchange / trading_mode，避免硬编码
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    exchange_name = (cfg.get("exchange") or {}).get("name", "binance")
    trading_mode = cfg.get("trading_mode", "futures")

    timerange = req.timerange or _default_timerange()

    pairs = bot.get("pair") or []
    tf_list = [req.timeframe]
    for tf in _get_htf_timeframes(bot, side=req.side):
        if tf not in tf_list:
            tf_list.append(tf)

    local_check = _check_local_data(
        pairs, tf_list, timerange,
        exchange_name=exchange_name,
        trading_mode=trading_mode,
    )
    print(f"[download-data] 本地数据检查: all_covered={local_check['all_covered']}")
    for d in local_check["details"]:
        print(f"  {d['pair']:20s} {d['tf']:5s} local={d['local']} covered={d['covered']}")

    if local_check["all_covered"]:
        print("[download-data] ✅ 本地数据已覆盖，跳过下载")
        return {
            "success": True,
            "skipped": True,
            "message": "数据已下载",
            "bot_id": bot_id,
            "timeframe": req.timeframe,
            "timerange": timerange,
        }

    # 下载
    res = _run_freqtrade_download(
        config_path=config_path,
        timeframe=req.timeframe,
        timerange=timerange,
        extra_timeframes=_get_htf_timeframes(bot, side=req.side),
    )
    if not res["success"]:
        raise HTTPException(
            500,
            "数据下载失败：\n"
            + (res.get("stderr_tail") or res.get("stdout_tail") or "未知错误")
        )

    # ★ 下载成功后清缓存
    _check_cache.clear()

    return {
        "success": True,
        "skipped": False,
        "bot_id": bot_id,
        "timeframe": req.timeframe,
        "timerange": timerange,
    }


def _make_download_parse_fn():
    """下载完成时的解析函数"""
    def _parse(stdout: str) -> dict:
        # 清检查缓存（下次再点"下载"会重新判断）
        _check_cache.clear()
        return {
            "success": True,
            "skipped": False,
            "message": "数据下载完成",
        }
    return _parse


@router.post("/{bot_id}/download-data/start")
async def download_data_start(bot_id: int, req: DownloadDataRequest):
    """
    启动异步下载，立即返回 job_id。
    前端通过 /download-data/progress/{job_id} 轮询。
    """
    if not FREQTRADE_EXE:
        raise HTTPException(500, "freqtrade 可执行文件未找到")

    bot = BotManager.get(bot_id)
    if not bot:
        raise HTTPException(404, "bot not found")

    # 1. 生成 config
    ConfigService.generate_configs(bot_id, _build_config_for_backtest(bot))
    config_path = _require_config_path(bot, bot_id, req.side)

    # 2. 从 config 读 exchange / trading_mode
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    exchange_name = (cfg.get("exchange") or {}).get("name", "binance")
    trading_mode = cfg.get("trading_mode", "futures")

    timerange = req.timerange or _default_timerange()
    pairs = bot.get("pair") or []
    tf_list = [req.timeframe]
    for tf in _get_htf_timeframes(bot, side=req.side):
        if tf not in tf_list:
            tf_list.append(tf)

    # 3. 本地检查
    local_check = _check_local_data(
        pairs, tf_list, timerange,
        exchange_name=exchange_name,
        trading_mode=trading_mode,
    )
    print(f"[download:start] 本地数据检查: all_covered={local_check['all_covered']}")

    if local_check["all_covered"]:
        # ★ 直接创建一个已完成的 job，前端看到 success 就提示"已下载"
        job = create_job(bot_id, kind="download")
        job.status = "success"
        job.stage = "已下载"
        job.percent = 100
        job.finished_at = time.time()
        job.elapsed = 0
        job.result = {
            "skipped": True,
            "message": "数据已下载",
            "timerange": timerange,
        }
        return {
            "job_id": job.job_id,
            "status": job.status,
            "skipped": True,
        }

    # 4. 组装命令
    tf_set = tf_list
    cmd = [
        FREQTRADE_EXE,
        "download-data",
        "--config", str(config_path),
        "-t", *tf_set,
        "--trading-mode", trading_mode,
    ]
    if timerange:
        start, end = _parse_timerange(timerange)
        if start and end:
            cmd += ["--timerange", f"{start}-{end}"]

    print(f"[download:start] bot={bot_id} cmd={' '.join(cmd)}")

    # 5. 创建异步 job
    job = create_job(bot_id, kind="download")
    run_job_async(
        job=job,
        cmd=cmd,
        cwd=str(FREQTRADE_DIR),
        parse_result_fn=_make_download_parse_fn(),
    )

    return {
        "job_id": job.job_id,
        "status": job.status,
        "skipped": False,
    }


@router.get("/{bot_id}/download-data/progress/{job_id}")
async def download_data_progress(bot_id: int, job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if job.bot_id != bot_id:
        raise HTTPException(400, "job / bot 不匹配")
    if job.kind != "download":
        raise HTTPException(400, "job 不是下载任务")

    finished = job.status in ("success", "failed", "cancelled")
    return job.to_public(include_result=finished)


@router.post("/{bot_id}/download-data/cancel/{job_id}")
async def download_data_cancel(bot_id: int, job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if job.bot_id != bot_id:
        raise HTTPException(400, "job / bot 不匹配")
    job.cancel()
    return {"success": True, "job_id": job_id, "status": job.status}


# ============================================================================
# ★ 异步回测：start / progress / cancel
# ============================================================================

def _build_config_for_backtest(bot: dict):
    """把 bot 记录组装成 ConfigService 需要的 payload"""
    return {
        "base": {
            "name": bot["name"],
            "pair": bot["pair"],
            "capital": bot["capital"],
            "stakeAmount": bot.get("stakeAmount", 10),
            "leverage": bot.get("leverage", 10),
            "maxOpenTrades": bot.get("maxOpenTrades", 3),
            "dryRun": bot.get("dryRun", True),
            "enableLong": bot.get("enableLong", True),
            "enableShort": bot.get("enableShort", False),
        },
        "risk": {
            "tp_enabled": bot.get("tp_enabled", False),
            "tp_mode": bot.get("tp_mode", "amount"),
            "tp_amount": bot.get("tp_amount", 0),
            "tp_ratio": bot.get("tp_ratio", 0),
            "sl_enabled": bot.get("sl_enabled", False),
            "sl_mode": bot.get("sl_mode", "amount"),
            "sl_amount": bot.get("sl_amount", 0),
            "sl_ratio": bot.get("sl_ratio", 0),
            "trail_enabled": bot.get("trail_enabled", False),
            "trail_mode": bot.get("trail_mode", "ratio"),
            "trail_activate_amount": bot.get("trail_activate_amount", 0),
            "trail_activate_ratio": bot.get("trail_activate_ratio", 0),
            "trail_drawdown_amount": bot.get("trail_drawdown_amount", 0),
            "trail_drawdown_ratio": bot.get("trail_drawdown_ratio", 0),
            "auto_stop_on_tp": bot.get("auto_stop_on_tp", True),
            "auto_stop_on_sl": bot.get("auto_stop_on_sl", True),
            "auto_stop_on_trail": bot.get("auto_stop_on_trail", True),
        },
        "longConfig": bot.get("longConfig"),
        "shortConfig": bot.get("shortConfig"),
    }


def _make_parse_fn():
    """返回一个纯函数：stdout -> dict"""

    def _parse_from_stdout(stdout: str) -> dict:
        result_file = None
        for cand in [
            FREQTRADE_DIR / "user_data" / "backtest_results" / "last_backtest_result.json",
            FREQTRADE_DIR / "last_backtest_result.json",
            FREQTRADE_DIR.parent / "last_backtest_result.json",
        ]:
            if cand.exists():
                result_file = cand
                break

        result = None
        if result_file:
            try:
                with open(result_file, "r", encoding="utf-8") as f:
                    raw_json = json.load(f)
                result = _parse_summary(raw_json)
            except Exception as e:
                print(f"[backtest] json parse failed: {e}")

        if result is None:
            result = _parse_stdout_report(stdout)

        # ★ 回测完成后清理旧结果
        try:
            _cleanup_old_results(
                FREQTRADE_DIR / "user_data" / "backtest_results",
                keep=10,
            )
        except Exception as e:
            print(f"[cleanup] 失败（不影响回测结果）: {e}")

        return result

    return _parse_from_stdout


@router.post("/{bot_id}/backtest/start")
async def start_backtest(bot_id: int, req: BacktestRequest):
    """
    启动异步回测，立即返回 job_id。前端通过 /progress/{job_id} 轮询。
    ★ 关键：ConfigService.generate_configs 在此刻冻结参数到 config 文件，
      之后 DB 里 bot 参数怎么改都不会影响正在跑的子进程。
    """
    if not FREQTRADE_EXE:
        raise HTTPException(500, "freqtrade 可执行文件未找到")

    bot = BotManager.get(bot_id)
    if not bot:
        raise HTTPException(404, "bot not found")

    # ★ 先检查请求的 side 是否合法（用 DB 状态判断）
    enable_long = bool(bot.get("enableLong", True))
    enable_short = bool(bot.get("enableShort", False))
    if req.side == "long" and not enable_long:
        raise HTTPException(400, "当前机器人未启用做多，无法回测 long 方向")
    if req.side == "short" and not enable_short:
        raise HTTPException(400, "当前机器人未启用做空，无法回测 short 方向")

    # 1. 生成 config（参数快照）
    ConfigService.generate_configs(bot_id, _build_config_for_backtest(bot))
    config_path = _require_config_path(bot, bot_id, req.side)

    strategy = "DcaTpLong" if req.side == "long" else "DcaTpShort"
    timerange = req.timerange or _default_timerange()

    cmd = [
        FREQTRADE_EXE,
        "backtesting",
        "--config", str(config_path),
        "--strategy", strategy,
        "-i", req.timeframe,
        "--timerange", timerange,
        "--cache", "none",
        "--export", "trades",
    ]

    print(f"[backtest:start] bot={bot_id} job cmd = {' '.join(cmd)}")

    job = create_job(bot_id)
    run_job_async(
        job=job,
        cmd=cmd,
        cwd=str(FREQTRADE_DIR),
        parse_result_fn=_make_parse_fn(),
    )

    return {
        "job_id": job.job_id,
        "status": job.status,
        "bot_id": bot_id,
    }


@router.get("/{bot_id}/backtest/progress/{job_id}")
async def backtest_progress(bot_id: int, job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    if job.bot_id != bot_id:
        raise HTTPException(400, "job / bot 不匹配")

    # 完成时把 result 也带上
    finished = job.status in ("success", "failed", "cancelled")
    return job.to_public(include_result=finished)


@router.post("/{bot_id}/backtest/cancel/{job_id}")
async def backtest_cancel(bot_id: int, job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "job not found")
    job.cancel()
    return {"success": True, "job_id": job_id, "status": job.status}
