from pathlib import Path
import re
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

LOG_FILES = {
    "backend": BASE_DIR / "backend/logs/backend.log",
    "frontend": BASE_DIR / "frontend/logs/frontend.log",
    "long": BASE_DIR / "freqtrade/logs/long.log",
    "short": BASE_DIR / "freqtrade/logs/short.log",
}

def _bot_log_path(bot_id: int, side: str):
    return BASE_DIR / "freqtrade" / "user_data" / "bots" / str(bot_id) / "logs" / f"{side}.log"

# 更稳健的 ANSI 转义序列正则（覆盖大多数控制序列）
ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')

# Freqtrade 时间格式
TIME_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)")


def clean_text(text):

    text = ANSI_ESCAPE.sub('', text)

    # 清理残留ESC字符
    text = re.sub(
        r'\x1b\[[0-9;]*[mK]',
        '',
        text
    )

    return text


def parse_time(line: str) -> float:
    match = TIME_PATTERN.search(line)
    if match:
        time_str = match.group(1)
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S,%f")
        return dt.timestamp()
    return 0


class LogService:
    @staticmethod
    def parse_line(line: str, source: str) -> dict:
        clean = clean_text(line.strip())

        level = "INFO"
        if "ERROR" in clean:
            level = "ERROR"
        elif "WARNING" in clean or "WARN" in clean:
            level = "WARNING"

        return {
            "source": source,
            "level": level,
            "message": clean,
            # 真实日志时间
            "time": parse_time(clean),
        }

    @classmethod
    def read(cls, source: str, limit: int = 200, bot_id: int = None) -> list:
        if bot_id is not None and source in ("long", "short"):
            path = _bot_log_path(bot_id, source)
        else:
            path = LOG_FILES.get(source)
        if not path or not path.exists():
            return []

        result = []

        # 使用 UTF-8 读取并忽略不可解码字节，避免出现替换字符（�）
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()

        # 仅取最后 N 行
        tail_lines = lines[-limit:]

        for index, line in enumerate(tail_lines):
            # 清理并解析每行
            clean_line = clean_text(line)
            item = cls.parse_line(clean_line, source)
            item["index"] = index
            result.append(item)

        return result

    @classmethod
    def all(cls) -> list:
        result = []
        for source in LOG_FILES:
            logs = cls.read(source)
            if logs:
                result.extend(logs)

        result.sort(key=lambda x: (x.get("time", 0), x.get("index", 0)))
        return result[-500:]
