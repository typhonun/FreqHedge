import time
from app.services.state_service import StateService
import requests

from config.settings import (
    LONG_URL,
    SHORT_URL,
)
from app.core import runtime
from app.services.process_service import ProcessService
from app.services.freqtrade_client import FreqtradeClient

_status_cache = {"ts": 0, "data": None}
_STATUS_CACHE_TTL = 5


class FreqtradeService:

    @classmethod
    def start_bot_service(cls, data):

        try:

            current_state = StateService.load()

            # 确保 Freqtrade 进程存在（拉不起也继续尝试，后面会探活）
            ProcessService.start_freqtrade()

            errors = []

            # =========================
            # LONG
            # =========================

            if data.get("long"):

                if not ProcessService.wait_until_alive(LONG_URL):
                    errors.append("LONG Freqtrade API 启动超时")
                else:
                    try:
                        FreqtradeClient.start_bot(LONG_URL)
                        current_state["long"] = True
                    except Exception as e:
                        errors.append(f"LONG start_bot 失败: {e}")

            # =========================
            # SHORT
            # =========================

            if data.get("short"):

                if not ProcessService.wait_until_alive(SHORT_URL):
                    errors.append("SHORT Freqtrade API 启动超时")
                else:
                    try:
                        FreqtradeClient.start_bot(SHORT_URL)
                        current_state["short"] = True
                    except Exception as e:
                        errors.append(f"SHORT start_bot 失败: {e}")

            # =========================
            # 保存状态
            # =========================

            StateService.save(
                current_state["long"],
                current_state["short"]
            )

            if errors:
                return {
                    "success": False,
                    "error": "; ".join(errors),
                    "long": current_state["long"],
                    "short": current_state["short"]
                }

            return {
                "success": True,
                "long": current_state["long"],
                "short": current_state["short"]
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e)
            }

    @classmethod
    def stop_bot_service(cls, data: dict):

        try:

            current_state = StateService.load()

            # =========================
            # LONG
            # =========================

            if data.get("long"):

                try:
                    FreqtradeClient.stop_bot(LONG_URL)

                    for i in range(20):
                        state = FreqtradeClient.get_bot_state(LONG_URL)
                        print("LONG STOP WAIT:", state)
                        if state == "STOPPED":
                            break
                        time.sleep(1)

                except Exception as e:
                    print(f"stop LONG failed (可能进程已死): {e}")

                current_state["long"] = False

            # =========================
            # SHORT
            # =========================

            if data.get("short"):

                try:
                    FreqtradeClient.stop_bot(SHORT_URL)

                    for i in range(20):
                        state = FreqtradeClient.get_bot_state(SHORT_URL)
                        print("SHORT STOP WAIT:", state)
                        if state == "STOPPED":
                            break
                        time.sleep(1)

                except Exception as e:
                    print(f"stop SHORT failed (可能进程已死): {e}")

                current_state["short"] = False

            StateService.save(
                current_state["long"],
                current_state["short"]
            )

            return {
                "success": True,
                "long": current_state["long"],
                "short": current_state["short"]
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e)
            }

    @classmethod
    def stop_entry(cls, data: dict):

        try:

            # LONG
            if data.get("long"):

                FreqtradeClient.stop_entry(LONG_URL)

                runtime.STOP_ENTRY["long"] = True

            else:

                FreqtradeClient.start_entry(LONG_URL)

                runtime.STOP_ENTRY["long"] = False

            # SHORT
            if data.get("short"):

                FreqtradeClient.stop_entry(SHORT_URL)

                runtime.STOP_ENTRY["short"] = True

            else:

                FreqtradeClient.start_entry(SHORT_URL)

                runtime.STOP_ENTRY["short"] = False

            return {
                "success": True,
                "long": runtime.STOP_ENTRY["long"],
                "short": runtime.STOP_ENTRY["short"]
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e)
            }


    @classmethod
    def reload_service(cls):
        try:
            FreqtradeClient.send_command(LONG_URL, "reload_config")
            FreqtradeClient.send_command(SHORT_URL, "reload_config")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}


    @classmethod
    def get_stop_entry_status(cls):

        return {
            "long": runtime.STOP_ENTRY["long"],
            "short": runtime.STOP_ENTRY["short"]
        }

    @classmethod
    def is_bot_running(cls):
        current_state = StateService.load()

        print(
            "DELETE CHECK:",
            current_state["long"],
            current_state["short"]
        )

        return (
                current_state["long"]
                or
                current_state["short"]
        )

    @classmethod
    def get_status_service(cls):

        now = time.time()
        if (_status_cache["data"]
                and now - _status_cache["ts"] < _STATUS_CACHE_TTL):
            return _status_cache["data"]

        state = StateService.load()

        long_intent = bool(state.get("long", False))
        short_intent = bool(state.get("short", False))

        # 只有 intent=True 才探活，省请求
        long_alive = False
        short_alive = False

        if long_intent:
            try:
                long_alive = FreqtradeClient.is_freqtrade_alive(LONG_URL)
            except Exception as e:
                print("probe LONG_URL failed:", e)

        if short_intent:
            try:
                short_alive = FreqtradeClient.is_freqtrade_alive(SHORT_URL)
            except Exception as e:
                print("probe SHORT_URL failed:", e)

        # ★ 不再回写 StateService，避免污染用户意图

        result = {
            "long": "RUNNING" if long_intent else "STOPPED",
            "short": "RUNNING" if short_intent else "STOPPED",

            "long_alive": long_alive,
            "short_alive": short_alive,
        }

        _status_cache["ts"] = now
        _status_cache["data"] = result
        return result
