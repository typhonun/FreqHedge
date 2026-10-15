# backend/app/services/process_service.py
import subprocess
import sys
import time

from config.settings import FREQTRADE_DIR
from app.services.freqtrade_client import FreqtradeClient
from pathlib import Path


class ProcessService:

    # =========================================================
    # ★ 新增：统一从 config 里读策略类名
    # =========================================================
    @staticmethod
    def _resolve_strategy(cfg_path: Path, side: str) -> str:
        """
        优先从 config_botX_<side>.json 的 "strategy" 字段读；
        读不到再按 side 兜底到 DCA。
        """
        from app.services.config_service import ConfigService  # 延迟 import 避免循环
        try:
            cfg = ConfigService.read_json(cfg_path)
            s = (cfg or {}).get("strategy")
            if s:
                return s
        except Exception as e:
            print(f"[ProcessService] 读取 strategy 失败 {cfg_path}: {e}")

        # 兜底：老 config 或 config 缺 strategy 字段
        return "DcaTpLong" if side == "long" else "DcaTpShort"

    # =========================================================
    # 多实例：启停单 bot
    # =========================================================
    @classmethod
    def start_bot(cls, bot: dict):
        from app.services.config_service import ConfigService

        bot_id = bot["id"]
        base_dir = Path(FREQTRADE_DIR)

        started = []

        for side in ("long", "short"):
            enabled = bot.get("enableLong") if side == "long" else bot.get("enableShort")
            if not enabled:
                continue

            cfg = ConfigService.config_path(bot_id, side)
            if not cfg.exists():
                return {"success": False, "error": f"config {side} missing: {cfg}"}

            port = cls._get_port(bot_id, side)
            old_pids = cls.get_port_pids(port)
            for pid in old_pids:
                cls.terminate_pid(pid, f"bot{bot_id}-{side}")
            time.sleep(0.5)

            log_path = ConfigService.log_path(bot_id, side)

            # ★ 从 config 里读策略类名（支持 grid / dca）
            strategy = cls._resolve_strategy(cfg, side)

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
            print(f"[ProcessService] started bot={bot_id} side={side} strategy={strategy} pid={proc.pid}")
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
    def restart_bot_side(cls, bot_id: int, side: str):
        """停掉指定 side，重新拉起"""
        from app.services.bot_manager import BotManager
        bot = BotManager.get(bot_id)
        if not bot:
            return {"success": False, "error": "bot not found"}

        port = cls._get_port(bot_id, side)
        for pid in cls.get_port_pids(port):
            cls.terminate_pid(pid, f"bot{bot_id}-{side}")
        time.sleep(0.5)

        return cls._start_side(bot, side)

    @classmethod
    def _start_side(cls, bot: dict, side: str):
        """启动单个 side（供 restart_bot_side 用）"""
        from app.services.config_service import ConfigService

        bot_id = bot["id"]
        base_dir = Path(FREQTRADE_DIR)

        cfg = ConfigService.config_path(bot_id, side)
        if not cfg.exists():
            return {"success": False, "error": f"config {side} missing"}

        port = cls._get_port(bot_id, side)
        old_pids = cls.get_port_pids(port)
        for pid in old_pids:
            cls.terminate_pid(pid, f"bot{bot_id}-{side}")
        time.sleep(0.5)

        log_path = ConfigService.log_path(bot_id, side)

        # ★ 从 config 里读策略类名（支持 grid / dca）
        strategy = cls._resolve_strategy(cfg, side)

        subprocess.Popen(
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
        print(f"[ProcessService] restarted bot={bot_id} side={side} strategy={strategy}")

        url = f"http://127.0.0.1:{port}"
        cls.wait_until_alive(url, timeout=30)
        return {"success": True, "side": side}

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
    def _get_port(bot_id: int, side: str) -> int:
        """
        ★ 改为从 DB 读 port 字段
        """
        from app.services.bot_manager import BotManager
        bot = BotManager.get(bot_id)
        if not bot or not bot.get("port"):
            raise ValueError(f"bot {bot_id} 没有分配端口，请检查 DB 完整性")
        else:
            base = int(bot["port"])
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
        try:
            from urllib.parse import urlparse
            return urlparse(url).port
        except Exception:
            return None

    # =========================================================
    # 进程工具（多实例也在用）
    # =========================================================

    @staticmethod
    def kill_process(process, name):
        print("kill_process called:", name)
        if process is None:
            print(name, "PROCESS IS NONE")
            return False
        print("PID:", process.pid)
        result = subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True, text=True
        )
        print("return code:", result.returncode)
        print("stdout:", result.stdout)
        print("stderr:", result.stderr)
        return result.returncode == 0

    @staticmethod
    def terminate_pid(pid, name):
        print(f"正在终止 {name} PID={pid}")
        result = subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True, text=True
        )
        print(result.stdout)
        print(result.stderr)
        return result.returncode == 0

    @staticmethod
    def get_port_pids(port):
        result = subprocess.run(
            ["cmd", "/c", f"netstat -ano | findstr LISTENING | findstr :{port}"],
            capture_output=True, text=True
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
            ["cmd", "/c", f"netstat -ano | findstr LISTENING | findstr :{port}"],
            capture_output=True, text=True
        )
        return bool(result.stdout.strip())