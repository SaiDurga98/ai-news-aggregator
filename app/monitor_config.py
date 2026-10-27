from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

DEFAULT_MONITOR_CONFIG_PATH = Path("config/monitor.json")


class MonitorConfig(BaseModel):
    youtube_channels: list[str] = Field(default_factory=list)


def load_monitor_config(path: Path | None = None) -> MonitorConfig:
    config_path = path or DEFAULT_MONITOR_CONFIG_PATH
    if not config_path.is_file():
        raise FileNotFoundError(
            f"Monitor config not found at {config_path}. "
            "Add YouTube channel IDs under youtube_channels."
        )
    data = json.loads(config_path.read_text(encoding="utf-8"))
    return MonitorConfig.model_validate(data)
