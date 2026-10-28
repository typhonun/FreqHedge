# backend/app/api/bots.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
from pydantic import model_validator

from app.services.bot_manager import BotManager
from app.services.position_service import PositionService
from app.services.config_service import ConfigService
from app.core.defaults import BOT_DEFAULTS, RISK_DEFAULTS
from app.core.strategy_registry import get_strategy
from app.services.exchange_service import ExchangeService

router = APIRouter()


class BotBaseInfo(BaseModel):
    name: str
    pair: list[str]
    capital: float
    stakeAmount: float = BOT_DEFAULTS["stakeAmount"]
    leverage: int = BOT_DEFAULTS["leverage"]
    maxOpenTrades: int = BOT_DEFAULTS["maxOpenTrades"]
    dryRun: bool = BOT_DEFAULTS["dryRun"]
    enableLong: bool = BOT_DEFAULTS["enableLong"]
    enableShort: bool = BOT_DEFAULTS["enableShort"]
    exchangeAccountId: Optional[str] = None
    exchangeAccount: Optional[dict] = None
    tradingMode: str = BOT_DEFAULTS["tradingMode"]
    marginMode: str = BOT_DEFAULTS["marginMode"]
    strategyType: str = "dca"

    @model_validator(mode="after")
    def _check_direction(self):
        if self.enableLong and self.enableShort:
            raise ValueError("不允许同时开启多头和空头")
        if not self.enableLong and not self.enableShort:
            raise ValueError("必须启用一个方向（多头或空头）")
        if self.tradingMode not in ("spot", "futures"):
            raise ValueError("tradingMode 必须是 spot 或 futures")
        if self.tradingMode == "futures" and self.marginMode not in ("cross", "isolated"):
            raise ValueError("marginMode 必须是 cross 或 isolated")
        if self.tradingMode == "spot" and self.enableShort:
            raise ValueError("现货模式不支持做空")
        meta = get_strategy(self.strategyType)
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
    """校验网格策略的资金是否满足最低要求，防止无法平仓尾仓"""
    base = data.get("base", {})
    if base.get("strategyType") != "grid":
        return  # 只有网格策略才校验

    grid_config = data.get("gridConfig") or {}
    grid = grid_config.get("grid", {})

    capital = float(base.get("capital", 0))
    leverage = float(base.get("leverage", 1))
    count = int(grid.get("grid_count", 20))
    # 以交易所实时规则为准，配置值只作为接口不可用时的回退。
    min_notional = float(grid.get("min_notional_value", 10))
    pair = (base.get("pair") or [None])[0]
    if pair:
        pair_limits = ExchangeService.get_binance_usdt_futures_pair_limits(pair)
        if pair_limits:
            min_notional = float(pair_limits["min_notional"])

    if count <= 0:
        raise HTTPException(400, "网格数量必须大于 0")

    # 每格最低保证金 = 最小名义价值 / 杠杆
    min_per_grid_capital = min_notional / leverage
    # 最低总资金 = 每格最低保证金 * 网格数量
    min_total_capital = min_per_grid_capital * count

    if capital < min_total_capital:
        raise HTTPException(
            400,
            f"资金不足：当前杠杆 {leverage}x 下，{count} 格网格最低需要 "
            f"{min_total_capital:.2f} USDT，否则极易产生无法平仓的尾仓！"
        )


# =========================================================
# 路由
# =========================================================

@router.get("")
async def list_bots():
    bots = BotManager.list_all()
    return _attach_profit_batch(bots)


@router.post("/draft")
async def create_draft_bot(strategyType: str = "dca"):
    """新建草稿 bot，返回完整 bot 记录（含 id）"""
    bot = BotManager.create_draft(strategy_type=strategyType)
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