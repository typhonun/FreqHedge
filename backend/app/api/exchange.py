from fastapi import APIRouter, Query, Body
from app.services.exchange_service import ExchangeService
from app.services.bot_manager import BotManager
from app.services.config_service import ConfigService

router = APIRouter()


@router.get("/pairs")
def get_pairs(
    exchange: str = Query("binance"),
    market: str = Query("futures"),
):
    if exchange == "binance" and market == "futures":
        return ExchangeService.get_binance_usdt_futures_pairs()
    return []


@router.post("/sync-to-bots")
def sync_to_bots(
    accountId: str = Body(...),
    account: dict = Body(...),
):
    """
    遍历所有 bot，把 base.exchangeAccountJson 里 id 匹配的替换成新密钥，
    并重新生成 config 文件。
    正在运行的 bot 需要用户手动重启（或者你在这里顺手重启）。
    """
    updated = []
    bots = BotManager.list_all()

    for bot in bots:
        if bot.get("exchangeAccountId") != accountId:
            continue

        # 1. 更新 bot 记录里的 exchangeAccountJson
        old_json = bot.get("exchangeAccountJson") or {}
        new_json = {
            "exchange": account["exchange"],
            "apiKey": account["apiKey"],
            "apiSecret": account["apiSecret"],
            "passphrase": account.get("passphrase", ""),
        }

        payload = {
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
                "exchangeAccountId": bot.get("exchangeAccountId"),
                "exchangeAccount": new_json,
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

        # 2. 更新 bot 表 + 重新生成 config
        BotManager.update(bot["id"], payload)
        ConfigService.generate_configs(bot["id"], payload)

        updated.append(bot["id"])

    return {"success": True, "updated_bots": updated, "count": len(updated)}
