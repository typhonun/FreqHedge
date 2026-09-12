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


class FreqtradeService:

    @classmethod
    def start_bot_service(cls, data):

        try:

            current_state = StateService.load()

            # ==========================
            # 确保 Freqtrade 进程存在
            # ==========================

            ProcessService.start_freqtrade()

            # ==========================
            # LONG
            # ==========================

            if data.get("long"):

                if not ProcessService.wait_until_alive(
                        LONG_URL
                ):
                    return {
                        "success": False,
                        "error": "LONG Freqtrade API 启动超时"
                    }

                FreqtradeClient.start_bot(
                    LONG_URL
                )

                current_state["long"] = True

            # ==========================
            # SHORT
            # ==========================

            if data.get("short"):

                if not ProcessService.wait_until_alive(
                        SHORT_URL
                ):
                    return {
                        "success": False,
                        "error": "SHORT Freqtrade API 启动超时"
                    }

                FreqtradeClient.start_bot(
                    SHORT_URL
                )

                current_state["short"] = True

            # ==========================
            # 保存状态
            # ==========================

            StateService.save(
                current_state["long"],
                current_state["short"]
            )

            return {
                "success": True
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e)
            }

    @classmethod
    def stop_bot_service(cls, data: dict):

        try:

            # 当前管理器状态
            current_state = StateService.load()

            # =========================
            # LONG
            # =========================

            if data.get("long"):

                FreqtradeClient.stop_bot(LONG_URL)

                for i in range(20):

                    state = FreqtradeClient.get_bot_state(LONG_URL)

                    print(
                        "LONG STOP WAIT:",
                        state
                    )

                    if state == "STOPPED":
                        break

                    time.sleep(1)

                current_state["long"] = False

            # =========================
            # SHORT
            # =========================

            if data.get("short"):

                FreqtradeClient.stop_bot(SHORT_URL)

                for i in range(20):

                    state = FreqtradeClient.get_bot_state(SHORT_URL)

                    print(
                        "SHORT STOP WAIT:",
                        state
                    )

                    if state == "STOPPED":
                        break

                    time.sleep(1)

                current_state["short"] = False

            # =========================
            # 保存自己的状态
            # =========================

            StateService.save(
                current_state["long"],
                current_state["short"]
            )

            # =========================
            # 返回状态
            # =========================

            return {

                "success": True,

                "long":
                    current_state["long"],

                "short":
                    current_state["short"]

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
        current_state = StateService.load()

        return {

            "long":
                "RUNNING"
                if current_state["long"]
                else "STOPPED",

            "short":
                "RUNNING"
                if current_state["short"]
                else "STOPPED"

        }
