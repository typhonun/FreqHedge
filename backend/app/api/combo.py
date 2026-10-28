# backend/app/api/combo.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
import json
from pathlib import Path

router = APIRouter()
CONFIG_FILE = Path("config/combo_profit.json")

class ComboGroup(BaseModel):
    id: str
    name: str
    bot_ids: List[int]
    target_profit: float
    auto_stop: bool
    enabled: bool

class ComboConfigPayload(BaseModel):
    groups: List[ComboGroup]


@router.get("")
def get_combo_config():
    if not CONFIG_FILE.exists():
        return {"groups": []}
    try:
        raw = CONFIG_FILE.read_text().strip()
        if not raw:
            return {"groups": []}

        data = json.loads(raw)

        # ★ 如果读到的是之前误存的单对象，直接丢弃并返回空组
        if isinstance(data, dict) and "groups" not in data:
            return {"groups": []}

        # 确保 groups 是列表
        if not isinstance(data.get("groups"), list):
            return {"groups": []}

        return data
    except Exception as e:
        print(f"[Combo] 解析配置失败: {e}")
        return {"groups": []}

@router.post("")
def save_combo_config(cfg: ComboConfigPayload):
    CONFIG_FILE.parent.mkdir(exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg.model_dump(), indent=2))
    return {"success": True}