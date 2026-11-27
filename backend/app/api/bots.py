# backend/app/api/bots.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from pydantic import model_validator, Field

from app.services.bot_manager import BotManager
from app.services.position_service import PositionService
from app.services.config_service import ConfigService
from app.core.defaults import BOT_DEFAULTS, RISK_DEFAULTS
from app.core.strategy_registry import get_strategy
from app.services.exchange_service import ExchangeService
from app.core.config_manager import ConfigManager

router = APIRouter()


class BotBaseInfo(BaseModel):
    name: str
    pair: list[str]
    capital: float
    stakeAmount: float = BOT_DEFAULTS["stakeAmount"]
    leverage: int = Field(default=BOT_DEFAULTS["leverage"], ge=1, le=100)
    maxOpenTrades: int = BOT_DEFAULTS["maxOpenTrades"]
    dryRun: bool = BOT_DEFAULTS["dryRun"]
    enableLong: bool = BOT_DEFAULTS["enableLong"]
    enableShort: bool = BOT_DEFAULTS["enableShort"]
    hedgeMode: bool = BOT_DEFAULTS["hedgeMode"]
    exchangeAccountId: Optional[str] = None
    exchangeAccount: Optional[dict] = None
    tradingMode: str = BOT_DEFAULTS["tradingMode"]
    marginMode: str = BOT_DEFAULTS["marginMode"]
    strategyType: str = "dca"
    pairSelectionMode: str = "manual"

    @model_validator(mode="after")
    def _check_direction(self):
        # ▼▼▼ 加上这行 ▼▼▼
        print(f"\n🚨🚨🚨 [API DEBUG] 收到请求！strategyType={self.strategyType!r}, pairCount={len(self.pair)} 🚨🚨🚨\n", flush=True)

        if not self.enableLong and not self.enableShort:
            raise ValueError("必须启用一个方向（多头或空头）")
        if self.enableLong and self.enableShort:
            if self.tradingMode != "futures":
                raise ValueError("双向持仓模式只支持合约")
            self.hedgeMode = True
        if self.tradingMode not in ("spot", "futures"):
            raise ValueError("tradingMode 必须是 spot 或 futures")
        if self.tradingMode == "futures" and self.marginMode not in ("cross", "isolated"):
            raise ValueError("marginMode 必须是 cross 或 isolated")
        if self.tradingMode == "spot" and self.enableShort:
            raise ValueError("现货模式不支持做空")

        meta = get_strategy(self.strategyType)

        if self.strategyType == "grid":
            print(f"✅ [API DEBUG] 命中 grid 分支，跳过单币校验！", flush=True)
            return self

        print(f"❌ [API DEBUG] 走到单币校验了，single_pair={meta.get('single_pair')}", flush=True)
        if meta.get("single_pair") and len(self.pair) != 1:
            raise ValueError(f"{meta['label']} 只支持单个交易对")
        return self


class BotRiskConfig(BaseModel):
    tp_enabled: bool = RISK_DEFAULTS["tp_enabled"]
    tp_mode: str = RISK_DEFAULTS["tp_mode"]
    tp_amount: float = RISK_DEFAULTS["tp_amount"]
    tp_ratio: float = RISK_DEFAULTS["tp_ratio"]
    sl_enabled: bool = RISK_DEFAULTS["sl_enabled"]
    sl_mode: str = RISK_DEFAULTS["sl_mode"]
    sl_amount: float = RISK_DEFAULTS["sl_amount"]
    sl_ratio: float = RISK_DEFAULTS["sl_ratio"]
    trail_enabled: bool = RISK_DEFAULTS["trail_enabled"]
    trail_mode: str = RISK_DEFAULTS["trail_mode"]
    trail_activate_amount: float = RISK_DEFAULTS["trail_activate_amount"]
    trail_activate_ratio: float = RISK_DEFAULTS["trail_activate_ratio"]
    trail_drawdown_amount: float = RISK_DEFAULTS["trail_drawdown_amount"]
    trail_drawdown_ratio: float = RISK_DEFAULTS["trail_drawdown_ratio"]
    auto_stop_on_tp: bool = RISK_DEFAULTS["auto_stop_on_tp"]
    auto_stop_on_sl: bool = RISK_DEFAULTS["auto_stop_on_sl"]
    auto_stop_on_trail: bool = RISK_DEFAULTS["auto_stop_on_trail"]


class BotPayload(BaseModel):
    base: BotBaseInfo
    risk: Optional[BotRiskConfig] = None
    longConfig: Optional[dict] = None
    shortConfig: Optional[dict] = None
    gridConfig: Optional[dict] = None

    @model_validator(mode="after")
    def _check_grid_pair_mode(self):
        if self.base.strategyType != "grid":
            return self

        grid = (self.gridConfig or {}).get("grid") or {}

        # 判定是否为多因子模式（满足任一即可）
        is_scanner = (
            self.base.pairSelectionMode == "scanner"
            or bool(grid.get("smart_range_mode"))
            or len(self.base.pair) > 1   # ★ 兜底：多币必定是多因子
        )

        if not is_scanner and len(self.base.pair) != 1:
            raise ValueError("手动网格模式只支持单个交易对")

        # ★ 多因子模式下：maxOpenTrades 必须 >= 1 且 <= pair 数量
        if is_scanner:
            if len(self.base.pair) < 1:
                raise ValueError("多因子网格至少需要 1 个交易对")
            if self.base.maxOpenTrades < 1:
                raise ValueError("多因子网格 maxOpenTrades 必须 >= 1")
            if self.base.maxOpenTrades > len(self.base.pair):
                # 自动修正而不是报错，避免前端改值麻烦
                self.base.maxOpenTrades = len(self.base.pair)

        return self


# =========================================================
# ★ 给单个 bot 补上收益字段（累计 / 多头 / 空头）
# =========================================================
def _attach_profit(bot: dict) -> dict:
    bot_id = bot.get("id")
    try:
        summary = PositionService.get_total_profit_summary(bot_id=bot_id)
        bot["total_profit"] = round(float(summary.get("total_profit", 0.0) or 0.0), 2)
        bot["long_profit"] = round(float(summary.get("long_total_profit", 0.0) or 0.0), 2)
        bot["short_profit"] = round(float(summary.get("short_total_profit", 0.0) or 0.0), 2)
    except Exception as e:
        print(f"[bots] attach profit failed bot={bot_id}: {e}")
        bot["total_profit"] = 0.0
        bot["long_profit"] = 0.0
        bot["short_profit"] = 0.0
    return bot


def _attach_profit_batch(bots: list[dict]) -> list[dict]:
    """并行给一批 bot 补收益，最多 8 个并发"""
    if not bots:
        return bots
    with ThreadPoolExecutor(max_workers=8) as executor:
        return list(executor.map(_attach_profit, bots))


# =========================================================
# ★ 新增：网格资金校验工具函数
# =========================================================
def _validate_grid_capital(data: dict):
    base = data.get("base", {})
    if base.get("strategyType") != "grid":
        return

    grid_config = data.get("gridConfig") or {}
    grid = grid_config.get("grid", {})

    total_capital = float(base.get("capital", 0))
    leverage = float(base.get("leverage", 1))
    count = int(grid.get("grid_count", 20))
    max_open = int(base.get("maxOpenTrades", 1))

    # 识别是否是多因子模式
    is_scanner = bool(grid.get("smart_range_mode"))

    # ★ 计算实际用于单币的资金
    actual_capital = total_capital / max_open if is_scanner else total_capital

    min_notional = float(grid.get("min_notional_value", 10))
    pair = (base.get("pair") or [None])[0]
    if pair:
        pair_limits = ExchangeService.get_binance_usdt_futures_pair_limits(pair)
        if pair_limits:
            min_notional = float(pair_limits["min_notional"])

    if count <= 0:
        raise HTTPException(400, "网格数量必须大于 0")

    # 单币最低总资金 = (最小名义价值 / 杠杆) * 网格数量
    min_total_capital = (min_notional / leverage) * count

    # ★★★ 新增：如果单币所需的最低资金 > 实际分配给单币的资金，直接报错，不允许保存
    if actual_capital < min_total_capital:
        mode_str = f"多因子并发 {max_open} 个币，分摊后单币" if is_scanner else "当前"
        raise HTTPException(
            400,
            f"资金不足：{mode_str}可用资金 {actual_capital:.2f} USDT，"
            f"而当前杠杆 {leverage}x 下 {count} 格网格最低需要 {min_total_capital:.2f} USDT。"
            f"【强烈建议】增加总资金，或减少【最大持仓数】，或增加【单格分配资金】！"
        )

    # ★★★ 新增：校验每格保证金是否满足最小下单名义价值 ★★★
    per_grid_capital = actual_capital / count
    per_grid_notional = per_grid_capital * leverage
    if per_grid_notional < min_notional:
        raise HTTPException(
            400,
            f"单格资金过低：每个网格分配 {per_grid_capital:.2f} USDT，乘以 {leverage}x 杠杆后为 {per_grid_notional:.2f} USDT，"
            f"低于该交易对的最低要求 {min_notional:.2f} USDT。请减少网格数量（count={count}）或增加资金！"
        )


# =========================================================
# 路由
# =========================================================

@router.get("")
async def list_bots(dry_run: bool | None = Query(None)):
    bots = BotManager.list_all()
    if dry_run is not None:
        bots = [bot for bot in bots if bool(bot.get("dryRun")) == dry_run]
    return _attach_profit_batch(bots)


@router.post("/draft")
async def create_draft_bot(
    strategyType: str = "dca",
    dry_run: bool | None = Query(None),
):
    """新建草稿 bot，模式由当前前端交易模式明确传入。"""
    bot = BotManager.create_draft(strategy_type=strategyType, dry_run=dry_run)
    try:
        ConfigService.generate_configs(bot["id"], {
            "base": {
                "name": bot["name"],
                "pair": bot["pair"],
                "capital": bot.get("capital", BOT_DEFAULTS["capital"]),
                "stakeAmount": bot.get("stakeAmount", BOT_DEFAULTS["stakeAmount"]),
                "leverage": bot.get("leverage", BOT_DEFAULTS["leverage"]),
                "maxOpenTrades": bot.get("maxOpenTrades", BOT_DEFAULTS["maxOpenTrades"]),
                "dryRun": bot.get("dryRun", BOT_DEFAULTS["dryRun"]),
                "enableLong": bot.get("enableLong", BOT_DEFAULTS["enableLong"]),
                "enableShort": bot.get("enableShort", BOT_DEFAULTS["enableShort"]),
                "tradingMode": bot.get("tradingMode", BOT_DEFAULTS["tradingMode"]),
                "marginMode": bot.get("marginMode", BOT_DEFAULTS["marginMode"]),
                "strategyType": bot.get("strategyType", strategyType),
            },
            "risk": {},
            "longConfig": bot.get("longConfig"),
            "shortConfig": bot.get("shortConfig"),
            "gridConfig": bot.get("gridConfig"),
        })
    except Exception as e:
        print(f"[draft] generate_configs failed (non-fatal): {e}")
    return _attach_profit(bot)


@router.get("/{bot_id}")
async def get_bot(bot_id: int):
    bot = BotManager.get(bot_id)
    if not bot:
        raise HTTPException(404, "bot not found")
    return _attach_profit(bot)


@router.post("")
async def create_bot(payload: BotPayload):
    data = payload.model_dump()

    # ★ 调用网格资金校验
    _validate_grid_capital(data)

    bot = BotManager.create(data)
    ConfigService.generate_configs(bot["id"], data)
    return _attach_profit(bot)


@router.put("/{bot_id}")
async def update_bot(bot_id: int, payload: BotPayload):
    data = payload.model_dump()

    # ★ 调用网格资金校验
    _validate_grid_capital(data)

    bot = BotManager.update(bot_id, data)
    if not bot:
        raise HTTPException(404, "bot not found")
    ConfigService.generate_configs(bot_id, data)
    return _attach_profit(bot)


@router.delete("/{bot_id}")
async def delete_bot(bot_id: int):
    import time

    bot = BotManager.get(bot_id)
    if not bot:
        return {"ok": True, "deleted": False, "reason": "not found"}

    if bot.get("status") == "running":
        try:
            BotManager.stop(bot_id)
        except Exception as e:
            print(f"[delete_bot] stop failed: {e}")

        for _ in range(20):
            try:
                cur = BotManager.get(bot_id)
                if not cur or cur.get("status") != "running":
                    break
            except Exception:
                break
            time.sleep(0.2)
        time.sleep(0.3)

    try:
        BotManager.delete(bot_id)
    except Exception as e:
        print(f"[delete_bot] delete db record failed: {e}")
        raise HTTPException(500, f"删除记录失败: {e}")

    try:
        ConfigService.remove_bot_dir(bot_id)
    except Exception as e:
        print(f"[delete_bot] remove dir failed: {e}")

    return {"ok": True, "deleted": True}


@router.delete("/{bot_id}/draft")
async def delete_draft_bot(bot_id: int):
    """只允许删除 status='draft' 的 bot；正式 bot 返回 400"""
    bot = BotManager.get(bot_id)
    if not bot:
        return {"success": True, "deleted": False, "reason": "not found"}

    if bot.get("status") != "draft":
        raise HTTPException(400, "只能删除草稿机器人")

    ok = BotManager.delete_draft(bot_id)
    return {"success": True, "deleted": ok}


@router.post("/{bot_id}/start")
async def start_bot(bot_id: int):
    bot = BotManager.get(bot_id)
    if not bot:
        raise HTTPException(404, "bot not found")
    if bot.get("status") == "draft":
        BotManager.promote(bot_id)
    return BotManager.start(bot_id)


@router.post("/{bot_id}/stop")
async def stop_bot(bot_id: int):
    return BotManager.stop(bot_id)


@router.get("/{bot_id}/status")
async def bot_status(bot_id: int):
    return BotManager.status(bot_id)


# 找到 bots.py 中的 grid_runtime 路由
@router.get("/{bot_id}/grid-runtime")
async def grid_runtime(bot_id: int, side: str = Query("long")):
    bot = BotManager.get(bot_id)
    if not bot:
        return {"active": False, "side": side, "error": "bot not found"}
    normalized = "short" if str(side).lower() == "short" else "long"

    # 尝试从数据库读取真实的运行状态
    state = ConfigManager.get_bot_kv(
        f"grid_runtime_state_{bot_id}_{normalized}"
    )
    if not isinstance(state, dict):
        return {"active": False, "side": normalized}

    grid_config = (bot.get("gridConfig") or {}).get("grid") or {}

    # ★ 核心修复：去掉 lower_price 和 upper_price，与 GridBotBase.py 保持绝对一致！
    signature = "|".join(
        str(grid_config.get(key, ""))
        for key in ("grid_count", "spacing_algo")
    )

    if state.get("signature") != signature:
        return {"active": False, "side": normalized}

    return {"active": True, **state}


# =========================================================
# 动态白名单相关 API
# =========================================================
class DynamicWhitelistRequest(BaseModel):
    bot_id: int
    side: str = "long"
    direction: str = "LONG"  # LONG 或 SHORT
    exclude_pairs: list[str] = []
    closed_pair: str = ""  # ★ 本次平仓触发替换的交易对

def _whitelist_lock_key(bot_id: int, side: str) -> str:
    return f"grid_whitelist_scan_lock_{bot_id}_{side}"


def _whitelist_state_key(bot_id: int, side: str) -> str:
    return f"grid_whitelist_state_{bot_id}_{side}"

@router.post("/{bot_id}/dynamic-whitelist-scan")
async def dynamic_whitelist_scan(bot_id: int, payload: DynamicWhitelistRequest):
    """
    动态白名单扫描严格顺序：
    1. 写入扫描锁（阻止期间新开仓）
    2. 扫描最优币 + 计算区间
    3. 写入新白名单配置 & prefetch kv
    4. 若机器人正在运行，重启/重载使其生效，并更新生效状态
    5. 释放扫描锁，允许后续正常开仓
    """
    import asyncio
    import time as _time
    from app.services.grid_scanner import GridScanner
    from app.services.config_service import ConfigService
    from app.services.bot_manager import BotManager

    print(f"[API] 收到动态白名单扫描请求: bot_id={bot_id}, payload={payload}")

    bot = BotManager.get(bot_id)
    if not bot:
        raise HTTPException(404, "bot not found")

    strategy_type = bot.get("strategyType") or "dca"
    if strategy_type not in ("grid", "dca"):
        raise HTTPException(400, f"动态白名单暂不支持策略类型: {strategy_type}")

    side = "short" if payload.direction.upper() == "SHORT" else "long"
    if side == "long" and not bot.get("enableLong"):
        return {"success": False, "error": "多头未启用"}
    if side == "short" and not bot.get("enableShort"):
        return {"success": False, "error": "空头未启用"}

    # 按策略类型读取各自的动态白名单开关
    if strategy_type == "grid":
        grid_config = (bot.get("gridConfig") or {}).get("grid") or {}
        whitelist_enabled = bool(grid_config.get("dynamic_whitelist", False))
    else:
        side_cfg = bot.get(f"{side}Config") or bot.get("longConfig") or {}
        ps_cfg = side_cfg.get("pair_switch") or {}
        whitelist_enabled = (
            str(ps_cfg.get("mode", "manual")).lower() == "scanner"
            and bool(ps_cfg.get("dynamic_whitelist", False))
        )

    if not whitelist_enabled:
        raise HTTPException(400, "该机器人未启用动态白名单模式")

    lock_key = _whitelist_lock_key(bot_id, side)
    state_key = _whitelist_state_key(bot_id, side)
    now_ts = _time.time()

    # 1) 写扫描锁（超时 240s 自动视为过期，防止异常卡死）
    ConfigManager.set_bot_kv(lock_key, {
        "scanning": True,
        "started_at": now_ts,
        "expire_at": now_ts + 240,
        "closed_pair": payload.closed_pair,
    })

    try:
        # 2) 多因子扫描
        scanner = GridScanner()
        best_pair_info = await asyncio.to_thread(
            scanner.select_best_pair,
            payload.direction.upper(),
            payload.exclude_pairs,
        )

        if not best_pair_info:
            ConfigManager.set_bot_kv(lock_key, {"scanning": False, "updated_at": _time.time()})
            return {"success": False, "error": "未找到符合条件的交易对"}

        new_pair = best_pair_info["name"]
        print(f"[API] 扫描到最优币: {new_pair}")

        # 3) 计算新币区间（仅网格需要；DCA 换币不消费区间数据）
        new_pair_range = None
        if strategy_type == "grid":
            days_map = {"aggressive": 7, "moderate": 30, "conservative": 90}
            days = days_map.get(
                str(grid_config.get("smart_range_mode", "moderate")).lower(), 30
            )
            new_pair_range = await asyncio.to_thread(
                scanner.get_range, new_pair, days
            )
            print(f"[API] 新币 {new_pair} 区间: {new_pair_range}")

        # 4) 生成并写入新白名单配置
        current_pairs = [
            (item.get("name") if isinstance(item, dict) else item)
            for item in (bot.get("pair") or [])
        ]
        current_pairs = [p for p in current_pairs if isinstance(p, str) and p]

        # ★ 白名单容量 = 当前白名单长度（即多因子选币的目标数量），
        whitelist_cap = max(len(current_pairs), 1)

        new_whitelist = [p for p in current_pairs if p != payload.closed_pair]
        if new_pair not in new_whitelist:
            new_whitelist.append(new_pair)

        if len(new_whitelist) > whitelist_cap:
            protected = {new_pair} | set(payload.exclude_pairs or [])
            head = [p for p in new_whitelist if p in protected]
            tail = [p for p in new_whitelist if p not in protected]
            new_whitelist = (head + tail)[:whitelist_cap]

        # ★ 定时刷新场景下大多数扫描结果与现有白名单一致：
        #   以策略实际生效的白名单（state kv，缺省回退 bot.pair）为基线，
        #   集合相同则跳过配置重写与进程重启，仅刷新状态时间戳。
        baseline = list(current_pairs)
        try:
            prev_state = ConfigManager.get_bot_kv(state_key)
            if isinstance(prev_state, dict) and prev_state.get("whitelist"):
                baseline = prev_state["whitelist"]
        except Exception:
            pass
        whitelist_unchanged = (
            len(new_whitelist) == len(baseline)
            and set(new_whitelist) == set(baseline)
        )

        if whitelist_unchanged:
            success = True
        else:
            success = await asyncio.to_thread(
                ConfigService.update_whitelist, bot_id, side, new_whitelist
            )
            if not success:
                ConfigManager.set_bot_kv(lock_key, {"scanning": False, "updated_at": _time.time()})
                return {"success": False, "error": "白名单更新失败"}

        # 同步新币区间到 prefetch kv（仅网格需要）
        if strategy_type == "grid":
            try:
                kv_key = f"grid_prefetch_range_{bot_id}_{side}"
                kv_data = ConfigManager.get_bot_kv(kv_key) or {"days": days, "pairs": {}}
                kv_data.setdefault("pairs", {})[new_pair] = new_pair_range
                kv_data["generated_at"] = _time.time()
                ConfigManager.set_bot_kv(kv_key, kv_data)
            except Exception as e:
                print(f"[API] 同步区间到 kv 失败（非致命）: {e}")

        # ★ 白名单无变化：不清运行时 KV、不重写配置、不重启，仅刷新状态时间戳
        if whitelist_unchanged:
            ConfigManager.set_bot_kv(state_key, {
                "whitelist": new_whitelist,
                "new_pair": new_pair,
                "restarted": False,
                "unchanged": True,
                "applied_at": _time.time(),
            })
            ConfigManager.set_bot_kv(lock_key, {
                "scanning": False,
                "completed_at": _time.time(),
                "new_pair": new_pair,
                "new_whitelist": new_whitelist,
                "unchanged": True,
            })
            return {
                "success": True,
                "new_pair": new_pair,
                "new_pair_range": new_pair_range,
                "new_whitelist": new_whitelist,
                "restarted": False,
                "unchanged": True,
                "message": f"白名单无变化（{new_pair} 已在有效名单内），无需重启",
            }

        # ★ 新增：重启前清理旧的动态区间 KV，防止重启后回退到历史区间（仅网格）
        if strategy_type == "grid":
            for runtime_key in (
                    f"grid_runtime_lower_{bot_id}_{side}",
                    f"grid_runtime_upper_{bot_id}_{side}",
                    f"grid_runtime_state_{bot_id}_{side}",
            ):
                try:
                    ConfigManager.set_bot_kv(runtime_key, None)
                except Exception as e:
                    print(f"[API] 清理 {runtime_key} 失败（非致命）: {e}")

        # 5) 让新配置/白名单真正生效：若机器人正在运行，执行重启使其加载新白名单
        restarted = False
        latest_bot = BotManager.get(bot_id)
        if latest_bot and latest_bot.get("status") == "running":
            print(f"[API] 白名单已写入，重启 bot={bot_id} 使新白名单生效...")
            await asyncio.to_thread(BotManager.restart, bot_id, True)
            restarted = True

        ConfigManager.set_bot_kv(state_key, {
            "whitelist": new_whitelist,
            "new_pair": new_pair,
            "restarted": restarted,
            "applied_at": _time.time(),
        })
        ConfigManager.set_bot_kv(lock_key, {
            "scanning": False,
            "completed_at": _time.time(),
            "new_pair": new_pair,
            "new_whitelist": new_whitelist,
        })

        return {
            "success": True,
            "new_pair": new_pair,
            "new_pair_range": new_pair_range,
            "new_whitelist": new_whitelist,
            "restarted": restarted,
            "message": f"已更新白名单并生效，新币 {new_pair} 可正常参与开仓",
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        ConfigManager.set_bot_kv(lock_key, {
            "scanning": False,
            "error_at": _time.time(),
            "error": str(e),
        })
        raise HTTPException(500, f"动态白名单扫描失败: {str(e)}")