from pathlib import Path
import shutil
import time

from app.core import runtime
from app.services.state_service import StateService
from app.services.process_service import ProcessService
from app.services.freqtrade_client import FreqtradeClient

from config.settings import (
    LONG_URL,
    SHORT_URL,
    FREQTRADE_DIR,
)


class DeleteService:

    BASE_DIR = Path(FREQTRADE_DIR)

    # =========================================================
    # 检查 Freqtrade API 是否还活着
    # =========================================================

    @classmethod
    def is_freqtrade_stopped(cls):

        long_alive = FreqtradeClient.is_freqtrade_alive(
            LONG_URL
        )

        short_alive = FreqtradeClient.is_freqtrade_alive(
            SHORT_URL
        )

        print(
            "FREQTRADE API CHECK:",
            "LONG =", long_alive,
            "SHORT =", short_alive
        )

        return not long_alive and not short_alive

    # =========================================================
    # 强制关闭 Freqtrade
    # =========================================================

    @classmethod
    def stop_processes_for_delete(cls):

        print("==============================")
        print("准备关闭 Freqtrade 进程")
        print("==============================")

        # =====================================================
        # 1. 通知 Freqtrade 停止 Bot
        # =====================================================

        try:

            if FreqtradeClient.is_freqtrade_alive(LONG_URL):

                print("发送 LONG stop")

                try:
                    FreqtradeClient.stop_bot(LONG_URL)
                except Exception as e:
                    print("LONG stop error:", e)

        except Exception as e:

            print("LONG API check error:", e)

        try:

            if FreqtradeClient.is_freqtrade_alive(SHORT_URL):

                print("发送 SHORT stop")

                try:
                    FreqtradeClient.stop_bot(SHORT_URL)
                except Exception as e:
                    print("SHORT stop error:", e)

        except Exception as e:

            print("SHORT API check error:", e)

        # =====================================================
        # 2. 给 Freqtrade 一点时间处理 stop
        # =====================================================

        time.sleep(3)

        # =====================================================
        # 3. 强制结束 runtime 中的进程
        # =====================================================

        processes = [

            (
                runtime.LONG_PROCESS,
                "LONG"
            ),

            (
                runtime.SHORT_PROCESS,
                "SHORT"
            )

        ]

        for process, name in processes:

            if process is not None:

                try:

                    if process.poll() is None:
                        print(
                            f"强制关闭 {name} PID:",
                            process.pid
                        )

                        ProcessService.kill_process(
                            process,
                            name
                        )

                except Exception as e:

                    print(
                        f"{name} kill error:",
                        e
                    )

        runtime.LONG_PROCESS = None
        runtime.SHORT_PROCESS = None

        # =====================================================
        # 4. 根据端口继续清理残留进程
        # =====================================================

        for port, name in [

            (8011, "LONG"),
            (8012, "SHORT")

        ]:

            pids = ProcessService.get_port_pids(
                port
            )

            print(
                f"{name} LISTENING PIDS:",
                pids
            )

            for pid in pids:
                ProcessService.terminate_pid(
                    pid,
                    name
                )

        # =====================================================
        # 5. 等待端口真正释放
        # =====================================================

        print(
            "等待 Freqtrade 进程退出..."
        )

        for i in range(20):

            long_pids = ProcessService.get_port_pids(
                8011
            )

            short_pids = ProcessService.get_port_pids(
                8012
            )

            print(
                f"EXIT CHECK [{i + 1}/20]:",
                "LONG =", long_pids,
                "SHORT =", short_pids
            )

            # =================================================
            # 已经没有 LISTENING PID
            # =================================================

            if not long_pids and not short_pids:
                print(
                    "Freqtrade 进程已完全退出"
                )

                return True

            # =================================================
            # 还有残留进程，继续杀
            # =================================================

            for pid in long_pids:
                ProcessService.terminate_pid(
                    pid,
                    "LONG"
                )

            for pid in short_pids:
                ProcessService.terminate_pid(
                    pid,
                    "SHORT"
                )

            time.sleep(1)

        # =====================================================
        # 6. 最终检查
        # =====================================================

        long_pids = ProcessService.get_port_pids(
            8011
        )

        short_pids = ProcessService.get_port_pids(
            8012
        )

        print(
            "最终检查:",
            "LONG =", long_pids,
            "SHORT =", short_pids
        )

        if not long_pids and not short_pids:
            print(
                "Freqtrade 已完全退出"
            )

            return True

        print(
            "Freqtrade 仍有 LISTENING 进程"
        )

        return False

    # =========================================================
    # 删除交易数据库
    # =========================================================

    @classmethod
    def delete_trade(cls):

        print("========================")
        print("DELETE TRADE START")
        print("========================")

        result = {
            "database": [],
            "logs": []
        }

        # =====================================================
        # 1. 检查管理器状态
        # =====================================================

        current_state = StateService.load()

        print(
            "CURRENT STATE:",
            current_state
        )

        if (
                current_state["long"]
                or
                current_state["short"]
        ):

            return {
                "success": False,
                "error":
                    "请先停止机器人再删除数据库"
            }

        # =====================================================
        # 2. 彻底关闭 Freqtrade
        # =====================================================

        if not cls.stop_processes_for_delete():

            return {
                "success": False,
                "error":
                    "Freqtrade 进程未能完全退出，已中止删除"
            }

        # =====================================================
        # 3. 删除数据库
        # =====================================================

        db_files = [

            "tradesv3_long.sqlite",
            "tradesv3_long.sqlite-shm",
            "tradesv3_long.sqlite-wal",

            "tradesv3_short.sqlite",
            "tradesv3_short.sqlite-shm",
            "tradesv3_short.sqlite-wal",

        ]

        for filename in db_files:

            file_path = cls.BASE_DIR / filename

            if not file_path.exists():
                continue

            try:

                file_path.unlink()

                result["database"].append(
                    filename
                )

                print(
                    "删除数据库文件:",
                    filename
                )

            except Exception as e:

                return {

                    "success": False,

                    "error":
                        f"删除数据库失败: {filename}",

                    "detail":
                        str(e)

                }

        # =====================================================
        # 4. 删除日志
        # =====================================================

        log_dir = (
            cls.BASE_DIR / "logs"
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
                            f"删除日志失败: {item.name}",

                        "detail":
                            str(e)

                    }

        # =====================================================
        # 5. 确保运行状态同步
        # =====================================================

        StateService.save(
            False,
            False
        )

        runtime.LONG_PROCESS = None
        runtime.SHORT_PROCESS = None

        print("========================")
        print("DELETE TRADE SUCCESS")
        print("========================")

        return {

            "success":
                True,

            "message":
                "已成功删除数据库",

            "detail":
                result

        }