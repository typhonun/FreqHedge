# backend/app/services/backtest_job.py
import json
import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict

FREQTRADE_DIR = Path(r"E:\code\python_code\DcaTp\freqtrade")


@dataclass
class BacktestJob:
    job_id: str
    bot_id: int
    kind: str = "backtest"
    status: str = "pending"          # pending | running | success | failed | cancelled
    stage: str = "初始化"
    percent: float = 0.0
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    elapsed: float = 0.0
    result: Optional[dict] = None
    error: Optional[str] = None
    log_tail: str = ""
    _proc: Optional[subprocess.Popen] = None
    _lock: threading.Lock = field(default_factory=threading.Lock)

    def to_public(self, include_result: bool = False) -> dict:
        data = {
            "job_id": self.job_id,
            "bot_id": self.bot_id,
            "kind": self.kind,
            "status": self.status,
            "stage": self.stage,
            "percent": round(self.percent, 1),
            "elapsed": round(self.elapsed, 2),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error,
            "log_tail": self.log_tail[-2000:] if self.log_tail else "",
        }
        if include_result:
            data["result"] = self.result
        return data

    def cancel(self):
        with self._lock:
            if self._proc and self._proc.poll() is None:
                try:
                    self._proc.terminate()
                except Exception:
                    pass
            self.status = "cancelled"
            self.stage = "已取消"
            self.finished_at = time.time()
            self.elapsed = self.finished_at - self.started_at


JOBS: Dict[str, BacktestJob] = {}
JOBS_LOCK = threading.Lock()


def get_job(job_id: str) -> Optional[BacktestJob]:
    with JOBS_LOCK:
        return JOBS.get(job_id)


def list_jobs(bot_id: Optional[int] = None) -> list:
    with JOBS_LOCK:
        jobs = list(JOBS.values())
    if bot_id is not None:
        jobs = [j for j in jobs if j.bot_id == bot_id]
    return [j.to_public() for j in jobs]


def create_job(bot_id: int, kind: str = "backtest") -> BacktestJob:
    job = BacktestJob(job_id=uuid.uuid4().hex[:12], bot_id=bot_id, kind=kind)
    with JOBS_LOCK:
        JOBS[job.job_id] = job
        now = time.time()
        for k in list(JOBS.keys()):
            j = JOBS[k]
            if j.finished_at and now - j.finished_at > 1800:
                JOBS.pop(k, None)
    return job


# ★ 进度关键词：更贴近 freqtrade 真实输出
def _parse_progress_line(line: str) -> Optional[tuple]:
    low = line.lower()

    # 加载 config / 启动
    if "using config" in low or "parameter" in low:
        return ("加载配置", 8)

    # 加载数据
    if "loading data" in low or "load data" in low:
        return ("加载历史数据", 20)
    if "downloaded" in low and "candles" in low:
        return ("数据已就绪", 28)

    # 回测主体
    if "running backtest" in low or "backtesting" in low and "start" in low:
        return ("回测计算中", 40)
    if "backtest loop" in low or "processing" in low:
        return ("回测计算中", 55)

    # 统计
    if "generating report" in low or "backtest result" in low:
        return ("生成回测报告", 80)
    if "backtesting report" in low:
        return ("统计回测结果", 88)
    if "exit reason stats" in low:
        return ("统计退出原因", 92)
    if "summary metrics" in low:
        return ("汇总指标", 96)
    if "left open trades" in low:
        return ("未平仓统计", 97)

    return None


def run_job_async(job: BacktestJob, cmd: list, cwd: str, parse_result_fn):
    """
    后台线程执行 freqtrade，流式读取 stdout 更新进度。
    parse_result_fn(stdout_text) -> dict
    """

    def _worker():
        job.status = "running"
        job.stage = "启动 freqtrade"
        job.percent = 5

        stdout_buf = []
        stop_estimate = threading.Event()
        try:
            # ★ 这里必须写完整参数，不能是 ...
            proc = subprocess.Popen(
                cmd,
                cwd=cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="ignore",
                bufsize=1,
            )
            with job._lock:
                job._proc = proc

            if job.kind == "download":
                def _estimate():
                    elapsed = 0
                    while not stop_estimate.is_set():
                        time.sleep(1)
                        elapsed += 1
                        job.percent = min(95.0, 5.0 + elapsed * 1.5)
                        job.stage = f"下载 K 线数据（已耗时 {elapsed}s）"
                        job.elapsed = time.time() - job.started_at

                threading.Thread(target=_estimate, daemon=True).start()

            for line in iter(proc.stdout.readline, ""):
                stdout_buf.append(line)
                if len(stdout_buf) > 3000:
                    stdout_buf = stdout_buf[-2000:]

                if job.kind != "download":
                    parsed = _parse_progress_line(line)
                    if parsed:
                        job.stage, job.percent = parsed

                job.elapsed = time.time() - job.started_at
                job.log_tail = "".join(stdout_buf[-30:])

            stop_estimate.set()
            proc.wait()
            rc = proc.returncode
            job.elapsed = time.time() - job.started_at

            if job.status == "cancelled":
                return

            if rc != 0:
                job.status = "failed"
                job.stage = "回测失败"
                job.percent = 100
                job.error = "freqtrade 返回非零退出码：\n" + "".join(stdout_buf[-40:])
                job.finished_at = time.time()
                return

            job.stage = "解析结果"
            job.percent = 98

            try:
                result = parse_result_fn("".join(stdout_buf))
                job.result = result
                job.status = "success"
                job.stage = "完成"
                job.percent = 100
            except Exception as pe:
                job.status = "failed"
                job.stage = "解析结果失败"
                job.error = f"结果解析异常: {pe}"
            finally:
                job.finished_at = time.time()
                job.elapsed = job.finished_at - job.started_at

        except Exception as e:
            job.status = "failed"
            job.stage = "异常"
            job.error = str(e)
            job.finished_at = time.time()
            job.elapsed = job.finished_at - job.started_at
        finally:
            stop_estimate.set()

    t = threading.Thread(target=_worker, daemon=True)
    t.start()
    return t