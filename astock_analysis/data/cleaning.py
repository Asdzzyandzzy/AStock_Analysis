"""AKShare 数据字段兼容与标准化。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class TickColumns:
    time: str = "time"
    price: str = "price"
    volume: str = "volume"
    amount: str = "amount"
    side: str = "side"
    source: str = "source"


COLS = TickColumns()

FIELD_ALIASES: dict[str, list[str]] = {
    COLS.time: ["时间", "成交时间", "time", "Time"],
    COLS.price: ["成交价格", "成交价", "价格", "price"],
    COLS.volume: ["成交量", "手数", "成交手数", "volume"],
    COLS.amount: ["成交金额", "金额", "amount"],
    COLS.side: ["性质", "买卖盘性质", "方向", "side"],
}

BUY_WORDS = {"买盘", "主动买入", "B", "买", "买入"}
SELL_WORDS = {"卖盘", "主动卖出", "S", "卖", "卖出"}


def _first_existing(columns: Iterable[str], candidates: Iterable[str]) -> str | None:
    existing = set(columns)
    for candidate in candidates:
        if candidate in existing:
            return candidate
    return None


def normalize_symbol(symbol: str, with_prefix: bool = True) -> str:
    """统一股票代码格式。

    with_prefix=True 返回 sh600000/sz000001；False 返回 600000。
    """

    value = symbol.strip().lower()
    if value.startswith(("sh", "sz", "bj")):
        return value if with_prefix else value[2:]
    if not with_prefix:
        return value
    if value.startswith(("6", "9")):
        return f"sh{value}"
    if value.startswith(("0", "2", "3")):
        return f"sz{value}"
    if value.startswith(("4", "8")):
        return f"bj{value}"
    return value


def standardize_tick_data(df: pd.DataFrame, source: str = "akshare") -> pd.DataFrame:
    """把不同 AKShare 接口返回字段转换为标准字段。

    标准字段：time, price, volume, amount, side, source。
    amount 缺失时用 price * volume * 100 估算，适配“手数”接口。
    """

    if df is None or df.empty:
        return pd.DataFrame(columns=[COLS.time, COLS.price, COLS.volume, COLS.amount, COLS.side, COLS.source])

    out = pd.DataFrame(index=df.index)
    for target, aliases in FIELD_ALIASES.items():
        source_col = _first_existing(df.columns, aliases)
        if source_col is not None:
            out[target] = df[source_col]

    for col in [COLS.price, COLS.volume, COLS.amount]:
        if col in out.columns:
            out[col] = pd.to_numeric(out[col], errors="coerce")

    if COLS.amount not in out.columns or out[COLS.amount].isna().all():
        if {COLS.price, COLS.volume}.issubset(out.columns):
            out[COLS.amount] = out[COLS.price] * out[COLS.volume] * 100
        else:
            out[COLS.amount] = pd.NA

    if COLS.time in out.columns:
        out[COLS.time] = out[COLS.time].astype(str).str.strip()
    else:
        out[COLS.time] = ""

    if COLS.side in out.columns:
        out[COLS.side] = out[COLS.side].astype(str).str.strip()
        out[COLS.side] = out[COLS.side].replace({"nan": "未知", "None": "未知", "": "未知"})
    else:
        out[COLS.side] = "未知"

    out[COLS.source] = source
    out = out.dropna(subset=[COLS.price, COLS.amount], how="all")
    out = out.sort_values(COLS.time, kind="stable").reset_index(drop=True)
    return out


def add_side_flags(df: pd.DataFrame) -> pd.DataFrame:
    """增加主动买卖方向标记。"""

    out = df.copy()
    side = out.get(COLS.side, pd.Series("未知", index=out.index)).astype(str)
    out["is_buy"] = side.isin(BUY_WORDS) | side.str.contains("买", na=False)
    out["is_sell"] = side.isin(SELL_WORDS) | side.str.contains("卖", na=False)
    return out


def ensure_minute_column(df: pd.DataFrame) -> pd.DataFrame:
    """增加分钟列，用于分时聚合。"""

    out = df.copy()
    if COLS.time not in out.columns:
        out["minute"] = ""
        return out
    time_text = out[COLS.time].astype(str)
    out["minute"] = time_text.str.extract(r"(\d{2}:\d{2})", expand=False).fillna(time_text.str.slice(0, 5))
    return out
