import subprocess
import sys
import time

from app.core import runtime
from config.settings import (
    LONG_URL,
    SHORT_URL,
    FREQTRADE_DIR
)
from app.services.freqtrade_client import FreqtradeClient
from pathlib import Path

class ProcessService:

    @classmethod
    def start_bot(cls, bot: dict):
        import subprocess, sys, time

        bot_id = bot["id"]
        base_dir = Path(FREQTRADE_DIR)   # ← 用局部变量名，别叫 FREQTRADE_DIR

        started = []

        for side in ("long", "short"):
            enabled = bot.get("enableLong") if side == "long" else bot.get("enableShort")
            if not enabled:
                continue

            cfg = base_dir / f"user_data/bots/{bot_id}/config_{side}.json"
            if not cfg.exists():
                return {"success": False, "error": f"config {side} missing"}

            port = cls._get_port(bot_id, side)
            old_pids = cls.get_port_pids(port)
            for pid in old_pids:
                cls.terminate_pid(pid, f"bot{bot_id}-{side}")
            time.sleep(0.5)

            log_path = base_dir / f"user_data/bots/{bot_id}/logs/{side}.log"
            strategy = "DcaTpLong" if side == "long" else "DcaTpShort"

            proc = subprocess.Popen(
                [
                    sys.executable, "-m", "freqtrade", "trade",
                    "--config", str(cfg),
                    "--strategy", strategy,
                    "--strategy-path", str(base_dir / "user_data/strategies"),
                    "--logfile", str(log_path),
                ],
                cwd=str(base_dir),
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
            )
            started.append((side, proc.pid))

        for side, _ in started:
            url = f"http://127.0.0.1:{cls._get_port(bot_id, side)}"
            cls.wait_until_alive(url, timeout=30)

        return {"success": True, "started": [s for s, _ in started]}

    @classmethod
    def stop_bot(cls, bot: dict):
        bot_id = bot["id"]
        stopped = []
        for side in ("long", "short"):
            port = cls._get_port(bot_id, side)
            for pid in cls.get_port_pids(port):
                cls.terminate_pid(pid, f"bot{bot_id}-{side}")
                stopped.append(side)
        return {"success": True, "stopped": stopped}

    @classmethod
    def status_bot(cls, bot: dict):
        bot_id = bot["id"]
        result = {}
        for side in ("long", "short"):
            port = cls._get_port(bot_id, side)
            url = f"http://127.0.0.1:{port}"
            result[side] = FreqtradeClient.is_freqtrade_alive(url)
        return result

    @staticmethod
    def _get_port(bot_id, side):
        base = 8011 + bot_id * 2
        return base if side == "long" else base + 1

    @classmethod
    def wait_until_alive(cls, url, timeout=30):

        for _ in range(timeout):

            if FreqtradeClient.is_freqtrade_alive(url):
                return True

            time.sleep(1)

        return False

    @staticmethod
    def _port_of(url):
        """
        从 http://127.0.0.1:8011 里解析出 8011
        """
        try:
            from urllib.parse import urlparse
            return urlparse(url).port
        except Exception:
            return None

    @classmethod
    def start_freqtrade(cls):
        BASE_DIR = Path(FREQTRADE_DIR)
        log_dir = BASE_DIR / "logs"

        log_dir.mkdir(
            exist_ok=True
        )

        # ================= LONG =================
        if not FreqtradeClient.is_freqtrade_alive(LONG_URL):

            if runtime.LONG_PROCESS is None or \
                    runtime.LONG_PROCESS.poll() is not None:

                # ★ 起新进程前先清端口，避免"API 挂 + 进程对象丢失"起出多个
                long_port = cls._port_of(LONG_URL)
                old_pids = cls.get_port_pids(long_port)

                if old_pids:
                    print(
                        f"[start_freqtrade] LONG 端口 {long_port} "
                        f"被占用，先清理: {old_pids}"
                    )
                    for pid in old_pids:
                        cls.terminate_pid(pid, "LONG")

                    # 给系统一点时间释放端口
                    time.sleep(1)

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
                    cwd=str(FREQTRADE_DIR),
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )

                print(
                    "LONG PID:",
                    runtime.LONG_PROCESS.pid
                )

        # ================= SHORT =================
        if not FreqtradeClient.is_freqtrade_alive(SHORT_URL):

            if runtime.SHORT_PROCESS is None or \
                    runtime.SHORT_PROCESS.poll() is not None:

                short_port = cls._port_of(SHORT_URL)
                old_pids = cls.get_port_pids(short_port)

                if old_pids:
                    print(
                        f"[start_freqtrade] SHORT 端口 {short_port} "
                        f"被占用，先清理: {old_pids}"
                    )
                    for pid in old_pids:
                        cls.terminate_pid(pid, "SHORT")

                    time.sleep(1)

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
                    cwd=str(FREQTRADE_DIR),
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )

                print(
                    "SHORT PID:",
                    runtime.SHORT_PROCESS.pid
                )

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

    @staticmethod
    def get_port_pids(port):

        result = subprocess.run(
            [
                "cmd",
                "/c",
                f"netstat -ano | findstr LISTENING | findstr :{port}"
            ],
            capture_output=True,
            text=True
        )

        pids = []

        for line in result.stdout.splitlines():

            parts = line.split()

            if len(parts) >= 5:

                pid = parts[-1]

                if pid.isdigit() and pid != "0":

                    if pid not in pids:
                        pids.append(pid)

        return pids

    @staticmethod
    def check_port(port):

        result = subprocess.run(
            [
                "cmd",
                "/c",
                f"netstat -ano | findstr LISTENING | findstr :{port}"
            ],
            capture_output=True,
            text=True
        )

        return bool(result.stdout.strip())

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