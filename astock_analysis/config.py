"""项目配置与默认参数。"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT_DIR / "config.yaml"


@dataclass(frozen=True)
class AppConfig:
    """应用运行配置。"""

    default_symbol: str = "sh600941"
    intraday_symbol: str = "600941"
    cache_ttl_seconds: int = 120
    big_order_amount: float = 500_000
    super_big_order_amount: float = 2_000_000
    sudden_volume_window: int = 5
    sudden_volume_multiplier: float = 3.0
    rapid_price_change_pct: float = 0.006
    log_level: str = "INFO"


def load_config(path: str | Path | None = None) -> AppConfig:
    """读取 YAML 配置，缺失字段使用默认值。"""

    config_path = Path(path) if path else DEFAULT_CONFIG_PATH
    defaults = AppConfig()
    if not config_path.exists():
        return defaults

    try:
        raw: dict[str, Any] = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return defaults

    values = defaults.__dict__.copy()
    values.update({k: v for k, v in raw.items() if k in values})
    return AppConfig(**values)
