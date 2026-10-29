# backend/app/api/exchange.py
from fastapi import APIRouter, Query, Body, HTTPException
from pydantic import BaseModel
import ccxt
from app.services.exchange_service import ExchangeService
from app.services.bot_manager import BotManager
from app.services.config_service import ConfigService
from app.services.freqtrade_client import FreqtradeClient
from app.services.bot_runtime import list_running_bots, list_all_bots, get_bot_url

router = APIRouter()


class ExchangeConnectionRequest(BaseModel):
    exchange: str
    apiKey: str
    apiSecret: str
    passphrase: str = ""
    tradingMode: str = "futures"


@router.post("/balance")
def account_balance(data: ExchangeConnectionRequest):
    try:
        return ExchangeService.get_account_balance(
            data.exchange, data.apiKey.strip(), data.apiSecret.strip(),
            data.passphrase.strip(), data.tradingMode
        )
    except Exception as exc:
        raise HTTPException(400, f"获取交易所余额失败：{str(exc)[:240]}")


@router.post("/wallets")
def account_wallets(data: ExchangeConnectionRequest):
    try:
        return ExchangeService.get_account_wallets(
            data.exchange, data.apiKey.strip(), data.apiSecret.strip(), data.passphrase.strip()
        )
    except Exception as exc:
        raise HTTPException(400, f"获取交易所钱包余额失败：{str(exc)[:240]}")


@router.post("/test-connection")
def test_connection(data: ExchangeConnectionRequest):
    """Validate real exchange credentials without persisting them."""
    exchange_name = {"gate": "gateio", "huobi": "htx"}.get(data.exchange, data.exchange)
    exchange_class = getattr(ccxt, exchange_name, None)
    if exchange_class is None:
        raise HTTPException(400, "不支持的交易所")
    if not data.apiKey.strip() or not data.apiSecret.strip():
        raise HTTPException(400, "API Key 和 API Secret 不能为空")

    config = {
        "apiKey": data.apiKey.strip(),
        "secret": data.apiSecret.strip(),
        "enableRateLimit": True,
        "timeout": 10000,
    }
    config["options"] = {"defaultType": "future"}
    if data.passphrase.strip():
        config["password"] = data.passphrase.strip()

    try:
        client = exchange_class(config)
        client.fetch_balance({"type": "future"})
        return {"success": True}
    except Exception as exc:
        raise HTTPException(400, f"交易所连接失败：{str(exc)[:240]}")

@router.get("/pairs")
def get_pairs(
    exchange: str = Query("binance"),
    market: str = Query("futures"),
):
    if exchange == "binance" and market == "futures":
        return ExchangeService.get_binance_usdt_futures_pairs()
    return []


@router.get("/pair_limits")
def get_pair_limits(pair: str = Query(...)):
    """
    动态获取指定交易对的最小下单量和最小名义价值 (USDT)
    """
    default_res = {"min_qty": 0.001, "min_notional": 10.0}

    try:
        # Binance exchangeInfo is authoritative for the selected Binance
        # futures pair, including quantity-derived minimum notional.
        direct_limits = ExchangeService.get_binance_usdt_futures_pair_limits(pair)
        if direct_limits:
            return direct_limits

        # 1. 优先找正在运行的 bot
        bots = list_running_bots()
        if not bots:
            # 如果没有正在运行的，找所有非草稿状态的机器人（即使是停止的）
            bots = [b for b in list_all_bots() if b.get("status") != "draft"]

        if not bots:
            # 草稿阶段没有可借用的 bot，直接从币安获取交易对限额。
            direct_limits = ExchangeService.get_binance_usdt_futures_pair_limits(pair)
            return direct_limits or default_res

        # 2. 借用这个 bot 的 API 去查
        bot = bots[0]
        url = get_bot_url(bot["id"], "long")

        # 3. 请求 /api/v1/markets
        markets = FreqtradeClient.get(url, "/api/v1/markets")

        # 4. 解析目标交易对
        if pair not in markets:
            direct_limits = ExchangeService.get_binance_usdt_futures_pair_limits(pair)
            return direct_limits or default_res

        limits = markets[pair].get("limits", {})
        amount_limits = limits.get("amount", {})
        cost_limits = limits.get("cost", {})

        min_qty = amount_limits.get("min")
        min_notional = cost_limits.get("min")

        result = {
            "min_qty": float(min_qty) if min_qty else 0.001,
            "min_notional": float(min_notional) if min_notional else 10.0
        }
        if not min_qty and not min_notional:
            direct_limits = ExchangeService.get_binance_usdt_futures_pair_limits(pair)
            return direct_limits or result
        return result

    except Exception as e:
        print(f"[exchange] get_pair_limits failed: {e}")
        try:
            return (
                ExchangeService.get_binance_usdt_futures_pair_limits(pair)
                or default_res
            )
        except Exception as direct_error:
            print(f"[exchange] direct pair limits lookup failed: {direct_error}")
            return default_res


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
