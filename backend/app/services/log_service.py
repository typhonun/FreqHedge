from pathlib import Path
import re
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent

LOG_FILES = {
    "backend":  BASE_DIR / "backend/logs/backend.log",
    "frontend": BASE_DIR / "frontend/logs/frontend.log",
}

BOTS_DIR = BASE_DIR / "freqtrade" / "user_data" / "bots"

def _bot_log_paths(bot_id: int) -> list[Path]:
    """返回该 bot 所有 strategy*.log（兼容单/双方向）"""
    log_dir = BOTS_DIR / str(bot_id) / "logs"
    if not log_dir.exists():
        return []
    # 优先单方向；如果存在 _long/_short 就都返回
    single = log_dir / "strategy.log"
    if single.exists():
        return [single]
    return sorted(log_dir.glob("strategy_*.log"))


def _bot_log_path(bot_id: int, source: str = "strategy") -> Path:
    """单文件读取路径（保留兼容，读第一个）"""
    paths = _bot_log_paths(bot_id)
    return paths[0] if paths else (BOTS_DIR / str(bot_id) / "logs" / f"{source}.log")

def _discover_strategy_logs() -> list[Path]:
    if not BOTS_DIR.exists():
        return []
    result = []
    for bot_dir in BOTS_DIR.iterdir():
        if not bot_dir.is_dir():
            continue
        try:
            bot_id = int(bot_dir.name)
        except ValueError:
            continue
        result.extend(_bot_log_paths(bot_id))
    return result

ANSI_ESCAPE = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
TIME_PATTERN = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d+)")


def clean_text(text):
    text = ANSI_ESCAPE.sub('', text)
    text = re.sub(r'\x1b\[[0-9;]*[mK]', '', text)
    return text


def parse_time(line: str) -> float:
    match = TIME_PATTERN.search(line)
    if match:
        dt = datetime.strptime(match.group(1), "%Y-%m-%d %H:%M:%S,%f")
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
            "time": parse_time(clean),
        }

    @classmethod
    def _read_file(cls, path: Path, source: str, limit: int) -> list:
        if not path or not path.exists():
            return []
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        result = []
        for index, line in enumerate(lines[-limit:]):
            item = cls.parse_line(clean_text(line), source)
            item["index"] = index
            result.append(item)
        return result

    @classmethod
    def read(cls, source: str, limit: int = 200, bot_id: int = None) -> list:
        if source == "strategy":
            if bot_id is None:
                return []
            result = []
            for p in _bot_log_paths(bot_id):
                result.extend(cls._read_file(p, "strategy", limit))
            result.sort(key=lambda x: (x.get("time", 0), x.get("index", 0)))
            return result[-limit:]

        path = LOG_FILES.get(source)
        if not path:
            return []
        return cls._read_file(path, source, limit)

    @classmethod
    def all(cls) -> list:
        result = []

        # backend / frontend
        for source in LOG_FILES:
            result.extend(cls.read(source, limit=200))

        # strategy：每个 bot 取最近 100 行
        for path in _discover_strategy_logs():
            result.extend(cls._read_file(path, "strategy", limit=100))

        result.sort(key=lambda x: (x.get("time", 0), x.get("index", 0)))
        return result[-500:]