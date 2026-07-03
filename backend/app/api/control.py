from fastapi import APIRouter
from pydantic import BaseModel
from pathlib import Path

import json
import requests

import app.core.runtime as runtime
import subprocess

router = APIRouter()
LONG_API = "http://127.0.0.1:8011"
SHORT_API = "http://127.0.0.1:8012"

AUTH = (
    "freqtrader",
    "zy147258"
)

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parents[3]
)

FREQTRADE_DIR = (
        BASE_DIR
        / "freqtrade"
)

LONG_CONFIG = (
        FREQTRADE_DIR
        / "user_data"
        / "config_long.json"
)

SHORT_CONFIG = (
        FREQTRADE_DIR
        / "user_data"
        / "config_short.json"
)


def start_freqtrade():

    if runtime.LONG_PROCESS is None or \
       runtime.LONG_PROCESS.poll() is not None:

        runtime.LONG_PROCESS = subprocess.Popen(
            [
                "freqtrade",
                "trade",
                "--config",
                "user_data/config_long.json",
                "--strategy",
                "DcaTpLong"
            ],
            cwd=str(FREQTRADE_DIR)
        )

        print(
            "LONG PID:",
            runtime.LONG_PROCESS.pid
        )

    if runtime.SHORT_PROCESS is None or \
       runtime.SHORT_PROCESS.poll() is not None:

        runtime.SHORT_PROCESS = subprocess.Popen(
            [
                "freqtrade",
                "trade",
                "--config",
                "user_data/config_short.json",
                "--strategy",
                "DcaTpShort"
            ],
            cwd=str(FREQTRADE_DIR)
        )

        print(
            "SHORT PID:",
            runtime.SHORT_PROCESS.pid
        )


@router.get("/config/all")
def get_all_config():
    long_cfg = read_json(LONG_CONFIG)
    short_cfg = read_json(SHORT_CONFIG)

    return {
        "long": {
            "dry_run_wallet":
                long_cfg.get(
                    "dry_run_wallet",
                    300
                ),

            "stake_amount":
                long_cfg.get(
                    "stake_amount",
                    15
                ),

            "max_open_trades":
                long_cfg.get(
                    "max_open_trades",
                    3
                ),

            "max_usage":
                long_cfg.get(
                    "tradable_balance_ratio",
                    0.9
                ) * 100,

            "pair_whitelist":
                long_cfg["exchange"].get(
                    "pair_whitelist",
                    []
                ),

            "pair_blacklist":
                long_cfg["exchange"].get(
                    "pair_blacklist",
                    []
                )
        },

        "short": {
            "dry_run_wallet":
                short_cfg.get(
                    "dry_run_wallet",
                    300
                ),

            "stake_amount":
                short_cfg.get(
                    "stake_amount",
                    15
                ),

            "max_open_trades":
                short_cfg.get(
                    "max_open_trades",
                    3
                ),

            "max_usage":
                short_cfg.get(
                    "tradable_balance_ratio",
                    0.9
                ) * 100,

            "pair_whitelist":
                short_cfg["exchange"].get(
                    "pair_whitelist",
                    []
                ),

            "pair_blacklist":
                short_cfg["exchange"].get(
                    "pair_blacklist",
                    []
                )
        }
    }


@router.post("/config")
def save_config(data: ConfigUpdate):
    if data.side == "long":
        path = LONG_CONFIG

    else:
        path = SHORT_CONFIG

    cfg = read_json(path)

    cfg["stake_amount"] = data.stake_amount

    cfg["dry_run_wallet"] = data.dry_run_wallet

    cfg["max_open_trades"] = data.max_open_trades

    cfg["tradable_balance_ratio"] = (
            data.max_usage / 100
    )

    cfg["exchange"]["pair_whitelist"] = (
        data.pair_whitelist
    )

    cfg["exchange"]["pair_blacklist"] = (
        data.pair_blacklist
    )

    write_json(path, cfg)

    if data.side == "long":

        send_command(
            LONG_API,
            "reload_config"
        )

    else:

        send_command(
            SHORT_API,
            "reload_config"
        )

    return {
        "success": True
    }


def send_command(
        url,
        command
):
    return requests.post(
        f"{url}/api/v1/{command}",
        auth=AUTH,
        timeout=10
    )


@router.post("/start")
def start_bot(data: dict):

    if not get_bot_state(LONG_API) and \
       not get_bot_state(SHORT_API):

        start_freqtrade()

    if data.get("long"):

        requests.post(
            f"{LONG_API}/api/v1/start",
            auth=AUTH
        )

        runtime.RUNNING["long"] = True

    if data.get("short"):

        requests.post(
            f"{SHORT_API}/api/v1/start",
            auth=AUTH
        )

        runtime.RUNNING["short"] = True

    return {
        "success": True
    }


@router.post("/stop")
def stop_bot(data: dict):

    try:

        if data.get("long"):

            requests.post(
                f"{LONG_API}/api/v1/stop",
                auth=AUTH
            )

            runtime.RUNNING["long"] = False

        if data.get("short"):

            requests.post(
                f"{SHORT_API}/api/v1/stop",
                auth=AUTH
            )

            runtime.RUNNING["short"] = False

        return {
            "success": True
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


@router.get("/status")
def get_status():

    return {
        "long": runtime.RUNNING["long"],
        "short": runtime.RUNNING["short"]
    }


@router.post("/reload")
def reload_config():
    try:

        send_command(
            LONG_API,
            "reload_config"
        )

        send_command(
            SHORT_API,
            "reload_config"
        )

        return {
            "success": True
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


@router.post("/stopentry")
def stop_entry(data: dict):
    if data["long"]:
        requests.post(
            f"{LONG_API}/api/v1/stopentry",
            auth=AUTH
        )
    else:
        requests.post(
            f"{LONG_API}/api/v1/startentry",
            auth=AUTH
        )

    if data["short"]:
        requests.post(
            f"{SHORT_API}/api/v1/stopentry",
            auth=AUTH
        )
    else:
        requests.post(
            f"{SHORT_API}/api/v1/startentry",
            auth=AUTH
        )

    return {
        "success": True
    }


@router.post("/delete_trade")
def delete_trade():

    try:

        # 先停止机器人

        requests.post(
            f"{LONG_API}/api/v1/stop",
            auth=AUTH,
            timeout=10
        )

        requests.post(
            f"{SHORT_API}/api/v1/stop",
            auth=AUTH,
            timeout=10
        )

        # 清空数据库记录

        requests.delete(
            f"{LONG_API}/api/v1/delete_trade",
            auth=AUTH,
            timeout=30
        )

        requests.delete(
            f"{SHORT_API}/api/v1/delete_trade",
            auth=AUTH,
            timeout=30
        )

        return {
            "success": True
        }

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }


def get_bot_state(api_url):

    try:

        res = requests.get(
            f"{api_url}/api/v1/status",
            auth=AUTH,
            timeout=3
        )

        print("==============")
        print(api_url)
        print(res.text)
        print("==============")

        return False

    except Exception as e:

        print(e)
        return False


class ConfigUpdate(BaseModel):
    side: str

    dry_run_wallet: float

    stake_amount: float

    max_open_trades: int

    max_usage: float

    pair_whitelist: list[str]

    pair_blacklist: list[str]


def read_json(path):
    with open(
            path,
            "r",
            encoding="utf-8"
    ) as f:
        return json.load(f)


def write_json(
        path,
        data
):
    with open(
            path,
            "w",
            encoding="utf-8"
    ) as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )
