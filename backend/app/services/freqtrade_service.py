import json
import shutil
import subprocess
import sys
from pathlib import Path
import time

import requests

from config.settings import (
    LONG_URL,
    SHORT_URL,
    AUTH_USER,
    AUTH_PASSWORD
)

from config.settings import FREQTRADE_DIR
from app.core import runtime


class FreqtradeService:
    auth = (AUTH_USER, AUTH_PASSWORD)
    FREQTRADE_DIR = Path(
        r"E:\code\python_code\DcaTp\freqtrade"
    )
    STATE_FILE = FREQTRADE_DIR.parent / "backend_state.json"

    @classmethod
    def load_run_state(cls):

        if not cls.STATE_FILE.exists():
            return {
                "long": runtime.RUNNING["long"],
                "short": runtime.RUNNING["short"]
            }

        with open(
                cls.STATE_FILE,
                "r",
                encoding="utf-8"
        ) as f:
            data = json.load(f)

        return {
            "long": bool(data.get("long", False)),
            "short": bool(data.get("short", False))
        }

    @classmethod
    def save_run_state(cls, long_state, short_state):

        state = {
            "long": bool(long_state),
            "short": bool(short_state)
        }

        with open(
                cls.STATE_FILE,
                "w",
                encoding="utf-8"
        ) as f:
            json.dump(
                state,
                f,
                ensure_ascii=False,
                indent=4
            )

        runtime.RUNNING["long"] = state["long"]
        runtime.RUNNING["short"] = state["short"]

        return state

    @classmethod
    def post(
            cls,
            url,
            endpoint,
            payload=None
    ):

        r = requests.post(
            f"{url}{endpoint}",
            json=payload or {},
            auth=cls.auth,
            timeout=20
        )

        r.raise_for_status()

        return r.json()

    @classmethod
    def get_status(cls, url):
        r = requests.get(
            f"{url}/api/v1/status",
            auth=cls.auth,
            timeout=10
        )

        return r.json()

    @classmethod
    def get_balance(cls, url):
        r = requests.get(
            f"{url}/api/v1/balance",
            auth=cls.auth,
            timeout=10
        )

        return r.json()

    @classmethod
    def get_trades(cls, url):
        r = requests.get(
            f"{url}/api/v1/trades",
            auth=cls.auth,
            timeout=10
        )

        return r.json()

    @classmethod
    def is_freqtrade_alive(cls, url):

        try:

            r = requests.get(
                f"{url}/api/v1/status",
                auth=cls.auth,
                timeout=3
            )

            return r.status_code == 200


        except:

            return False

    @classmethod
    def start_bot(cls, url):
        r = requests.post(
            f"{url}/api/v1/start",
            auth=cls.auth
        )

        return r.json()

    @classmethod
    def stop_bot(cls, url):
        r = requests.post(
            f"{url}/api/v1/stop",
            auth=cls.auth
        )

        return r.json()

    @classmethod
    def start_bot_service(cls, data):

        try:

            current_state = cls.load_run_state()

            # ==========================
            # 确保freqtrade存在
            # ==========================

            cls.start_freqtrade()

            # ==========================
            # 等待API启动
            # ==========================

            for i in range(30):

                long_ok = cls.is_freqtrade_alive(
                    LONG_URL
                )

                short_ok = cls.is_freqtrade_alive(
                    SHORT_URL
                )

                if long_ok and short_ok:
                    break

                time.sleep(1)

            # ==========================
            # 启动bot
            # ==========================

            if data.get("long"):
                requests.post(
                    f"{LONG_URL}/api/v1/start",
                    auth=cls.auth,
                    timeout=10
                )

                current_state["long"] = True

            if data.get("short"):
                requests.post(
                    f"{SHORT_URL}/api/v1/start",
                    auth=cls.auth,
                    timeout=10
                )

                current_state["short"] = True

            cls.save_run_state(
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

    @staticmethod
    def kill_port(port, name):

        print("========================")
        print(
            f"准备关闭 {name}, port={port}"
        )

        # 查找占用端口的PID
        result = subprocess.run(
            [
                "cmd",
                "/c",
                f"netstat -ano | findstr :{port}"
            ],
            capture_output=True,
            text=True
        )

        output = result.stdout.strip()

        print(
            "netstat:",
            output
        )

        if not output:
            print(
                f"{name} 没有发现占用端口"
            )
            return False

        pids = set()

        for line in output.splitlines():

            parts = line.split()

            if len(parts) >= 5:

                pid = parts[-1]

                # 排除一些异常
                if pid.isdigit():
                    pids.add(pid)

        print(
            "发现PID:",
            pids
        )

        success = False

        for pid in pids:

            print(
                f"正在杀死 {name} PID={pid}"
            )

            kill_result = subprocess.run(
                [
                    "taskkill",
                    "/F",
                    "/T",
                    "/PID",
                    pid
                ],
                capture_output=True,
                text=True
            )

            print(
                kill_result.stdout
            )

            print(
                kill_result.stderr
            )

            if kill_result.returncode == 0:
                success = True

        time.sleep(2)

        return success

    @staticmethod
    def kill_process(process, name):

        print(
            "kill_process called:",
            name
        )

        if process is None:
            print(
                name,
                "PROCESS IS NONE"
            )

            return False

        print(
            "PID:",
            process.pid
        )

        result = subprocess.run(
            [
                "taskkill",
                "/F",
                "/T",
                "/PID",
                str(process.pid)
            ],
            capture_output=True,
            text=True
        )

        print(
            "return code:",
            result.returncode
        )

        print(
            "stdout:",
            result.stdout
        )

        print(
            "stderr:",
            result.stderr
        )

        return result.returncode == 0

    @classmethod
    def stop_bot_service(cls, data: dict):

        try:

            # 当前管理器状态
            current_state = cls.load_run_state()

            # =========================
            # LONG
            # =========================

            if data.get("long"):

                requests.post(
                    f"{LONG_URL}/api/v1/stop",
                    auth=cls.auth,
                    timeout=5
                )

                for i in range(20):

                    state = cls.get_bot_state(
                        LONG_URL
                    )

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

                requests.post(
                    f"{SHORT_URL}/api/v1/stop",
                    auth=cls.auth,
                    timeout=5
                )

                for i in range(20):

                    state = cls.get_bot_state(
                        SHORT_URL
                    )

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

            cls.save_run_state(
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
    def reload_service(cls):
        try:
            cls.send_command(LONG_URL, "reload_config")
            cls.send_command(SHORT_URL, "reload_config")
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def get_bot_state(cls, url):

        try:

            r = requests.get(
                f"{url}/api/v1/status",
                auth=cls.auth,
                timeout=5
            )

            data = r.json()

            print(
                "DEBUG STATUS:",
                data
            )

            if isinstance(data, dict):

                state = data.get("state")

                if state:
                    return state.upper()

            return "STOPPED"


        except Exception as e:

            print(
                "status error:",
                e
            )

            return "STOPPED"

    @classmethod
    def stop_entry(cls, data: dict):

        # LONG

        if data["long"]:

            requests.post(
                f"{LONG_URL}/api/v1/stopentry",
                auth=cls.auth
            )

        else:

            requests.post(
                f"{LONG_URL}/api/v1/startentry",
                auth=cls.auth
            )

            state = cls.get_bot_state(
                LONG_URL
            )

            if state == "PAUSED":
                requests.post(
                    f"{LONG_URL}/api/v1/start",
                    auth=cls.auth
                )

        # SHORT

        if data["short"]:

            requests.post(
                f"{SHORT_URL}/api/v1/stopentry",
                auth=cls.auth
            )

        else:

            requests.post(
                f"{SHORT_URL}/api/v1/startentry",
                auth=cls.auth
            )

            state = cls.get_bot_state(
                SHORT_URL
            )

            if state == "PAUSED":
                requests.post(
                    f"{SHORT_URL}/api/v1/start",
                    auth=cls.auth
                )

        return {
            "success": True
        }

    @classmethod
    def get_stop_entry_status(cls):

        return {
            "long": runtime.STOP_ENTRY["long"],
            "short": runtime.STOP_ENTRY["short"]
        }

    @staticmethod
    def check_port(port):

        result = subprocess.run(
            [
                "cmd",
                "/c",
                f"netstat -ano | findstr :{port}"
            ],
            capture_output=True,
            text=True
        )

        return bool(result.stdout.strip())

    @staticmethod
    def get_port_pids(port):

        result = subprocess.run(
            [
                "cmd",
                "/c",
                f"netstat -ano | findstr :{port}"
            ],
            capture_output=True,
            text=True
        )

        pids = []

        for line in result.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 5:
                pid = parts[-1]
                if pid.isdigit() and pid not in pids:
                    pids.append(pid)

        return pids

    @staticmethod
    def terminate_pid(pid, name):

        print(
            f"正在终止 {name} PID={pid}"
        )

        result = subprocess.run(
            [
                "taskkill",
                "/F",
                "/T",
                "/PID",
                str(pid)
            ],
            capture_output=True,
            text=True
        )

        print(
            result.stdout
        )
        print(
            result.stderr
        )

        return result.returncode == 0

    @classmethod
    def kill_freqtrade_worker(cls, name, process, port):

        stopped = False

        if process is not None and process.poll() is None:
            stopped = cls.kill_process(
                process,
                name
            )

        if not stopped:
            for pid in cls.get_port_pids(port):
                if cls.terminate_pid(pid, name):
                    stopped = True

        if process is not None and process.poll() is not None:
            stopped = True

        return stopped

    @classmethod
    def is_bot_running(cls):
        current_state = cls.load_run_state()

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
    def is_process_running(cls):

        long_alive = (
                runtime.LONG_PROCESS is not None
                and runtime.LONG_PROCESS.poll() is None
        )

        short_alive = (
                runtime.SHORT_PROCESS is not None
                and runtime.SHORT_PROCESS.poll() is None
        )

        print(
            "PROCESS CHECK:",
            long_alive,
            short_alive
        )

        return long_alive or short_alive

    @classmethod
    def shutdown_process(cls):

        print(
            "关闭freqtrade进程"
        )

        if runtime.LONG_PROCESS:
            cls.kill_process(
                runtime.LONG_PROCESS,
                "LONG"
            )

            runtime.LONG_PROCESS = None

        if runtime.SHORT_PROCESS:
            cls.kill_process(
                runtime.SHORT_PROCESS,
                "SHORT"
            )

            runtime.SHORT_PROCESS = None

        time.sleep(3)

    @classmethod
    def wait_sqlite_release(cls):

        for i in range(20):

            locked = False

            for name in [
                "tradesv3_long.sqlite",
                "tradesv3_short.sqlite"
            ]:

                path = cls.FREQTRADE_DIR / name

                if path.exists():

                    try:

                        with open(
                                path,
                                "a"
                        ):
                            pass


                    except PermissionError:

                        locked = True

            if not locked:
                print(
                    "SQLite文件已释放"
                )
                return True

            print(
                "等待SQLite释放..."
            )

            time.sleep(1)

        return False

    @classmethod
    def stop_processes_for_delete(cls):

        print(
            "准备关闭freqtrade"
        )

        # 1. 优雅关闭

        try:

            requests.post(
                f"{LONG_URL}/api/v1/stop",
                auth=cls.auth,
                timeout=5
            )

        except:
            pass

        try:

            requests.post(
                f"{SHORT_URL}/api/v1/stop",
                auth=cls.auth,
                timeout=5
            )

        except:
            pass

        # 2. 等待进程

        time.sleep(5)

        # 3. 强杀

        if runtime.LONG_PROCESS:
            cls.kill_process(
                runtime.LONG_PROCESS,
                "LONG"
            )

        if runtime.SHORT_PROCESS:
            cls.kill_process(
                runtime.SHORT_PROCESS,
                "SHORT"
            )

        runtime.LONG_PROCESS = None
        runtime.SHORT_PROCESS = None

        # 4. 根据端口杀残留

        for port, name in [
            (8011, "LONG"),
            (8012, "SHORT")
        ]:

            for pid in cls.get_port_pids(port):
                cls.terminate_pid(
                    pid,
                    name
                )

        # 5. 等待释放

        time.sleep(3)

        return True

    @classmethod
    def delete_trade(cls):

        print("========================")
        print("DELETE TRADE START")

        result = {

            "database": [],

            "logs": []

        }

        # ======================
        # 0. 检查机器人状态
        # ======================

        if cls.is_bot_running():
            return {

                "success": False,

                "error":
                    "请先停止机器人再删除数据库"

            }

        # 删除前只关闭进程，不改运行状态

        if not cls.stop_processes_for_delete():
            return {
                "success": False,
                "error": "freqtrade进程未能正常退出，已中止删除"
            }

        # 等待sqlite释放

        if not cls.wait_sqlite_release():
            return {

                "success": False,

                "error":
                    "数据库文件仍被占用"

            }

        # ======================
        # 删除数据库
        # ======================

        db_files = [

            "tradesv3_long.sqlite",

            "tradesv3_long.sqlite-shm",

            "tradesv3_long.sqlite-wal",

            "tradesv3_short.sqlite",

            "tradesv3_short.sqlite-shm",

            "tradesv3_short.sqlite-wal",

        ]

        for filename in db_files:

            file_path = (
                    cls.FREQTRADE_DIR
                    /
                    filename
            )

            if file_path.exists():

                try:

                    file_path.unlink()

                    result["database"].append(
                        filename
                    )

                    print(
                        "删除:",
                        filename
                    )


                except Exception as e:

                    return {

                        "success": False,

                        "error":
                            f"删除数据库失败 {filename}",

                        "detail":
                            str(e)

                    }

        # ======================
        # 删除日志
        # ======================

        log_dir = (

                cls.FREQTRADE_DIR

                /

                "logs"

        )

        if log_dir.exists():

            for item in log_dir.iterdir():

                try:

                    if item.is_file():

                        item.unlink()

                        result["logs"].append(
                            item.name
                        )


                    elif item.is_dir():

                        shutil.rmtree(item)

                        result["logs"].append(
                            item.name
                        )


                except Exception as e:

                    return {

                        "success": False,

                        "error":
                            f"删除日志失败 {item.name}",

                        "detail":
                            str(e)

                    }

        return {

            "success": True,

            "message":
                "已成功删除数据库",

            "detail":
                result

        }

    @classmethod
    def get_status_service(cls):
        current_state = cls.load_run_state()

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

    @classmethod
    def send_command(cls, url, command):
        return requests.post(
            f"{url}/api/v1/{command}",
            auth=cls.auth,
            timeout=10
        )

    @classmethod
    def start_freqtrade(cls):

        log_dir = cls.FREQTRADE_DIR / "logs"

        log_dir.mkdir(
            exist_ok=True
        )

        if not cls.is_freqtrade_alive(LONG_URL):

            if runtime.LONG_PROCESS is None or \
                    runtime.LONG_PROCESS.poll() is not None:
                runtime.LONG_PROCESS = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "freqtrade",
                        "trade",

                        "--config",
                        "user_data/config_long.json",

                        "--strategy",
                        "DcaTpLong",

                        "--logfile",
                        "logs/long.log"
                    ],

                    cwd=str(cls.FREQTRADE_DIR),

                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )

                print(
                    "LONG PID:",
                    runtime.LONG_PROCESS.pid
                )

        if not cls.is_freqtrade_alive(SHORT_URL):

            if runtime.SHORT_PROCESS is None or \
                    runtime.SHORT_PROCESS.poll() is not None:
                runtime.SHORT_PROCESS = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "freqtrade",
                        "trade",

                        "--config",
                        "user_data/config_short.json",

                        "--strategy",
                        "DcaTpShort",

                        "--logfile",
                        "logs/short.log"
                    ],

                    cwd=str(cls.FREQTRADE_DIR),

                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )

                print(
                    "SHORT PID:",
                    runtime.SHORT_PROCESS.pid
                )

    @classmethod
    def get_whitelist(cls, url):

        r = requests.get(
            f"{url}/api/v1/whitelist",
            auth=cls.auth,
            timeout=10
        )

        return r.json()

    @classmethod
    def force_enter(
            cls,
            side: str,
            pair: str,
            stakeamount: float
    ):

        base_url = (
            LONG_URL
            if side == "long"
            else SHORT_URL
        )

        payload = {
            "pair": pair,
            "side": side,
            "stakeamount": stakeamount,
            "ordertype": "market"
        }

        return cls.post(
            base_url,
            "/api/v1/forceenter",
            payload
        )
