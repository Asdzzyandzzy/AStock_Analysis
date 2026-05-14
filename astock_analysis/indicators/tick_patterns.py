"""逐笔交易行为与异常成交识别。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from astock_analysis.data.cleaning import COLS, add_side_flags, ensure_minute_column
from astock_analysis.indicators.intraday import classify_order_size, minute_bars


def detect_tick_patterns(df: pd.DataFrame, big_threshold: float = 500_000) -> pd.DataFrame:
    """识别拉升、砸盘、吸筹、出货、对倒、脉冲放量等可能现象。

    这些标签是基于规则的研究提示，不代表真实交易意图。
    """

    if df.empty:
        return pd.DataFrame(columns=["time", "pattern", "reason", "amount", "price"])

    out = add_side_flags(classify_order_size(df, big_threshold=big_threshold))
    out["price_change"] = out[COLS.price].pct_change().fillna(0)
    out["amount_ma"] = out[COLS.amount].rolling(20, min_periods=5).mean()
    out["amount_ratio"] = out[COLS.amount] / out["amount_ma"].replace(0, np.nan)

    events: list[dict[str, object]] = []
    for _, row in out.iterrows():
        patterns: list[str] = []
        if row["price_change"] > 0.004 and row[COLS.amount] >= big_threshold:
            patterns.append("价格拉升")
        if row["price_change"] < -0.004 and row[COLS.amount] >= big_threshold:
            patterns.append("砸盘")
        if row["is_buy"] and row[COLS.amount] >= big_threshold and abs(row["price_change"]) < 0.002:
            patterns.append("疑似吸筹")
        if row["is_sell"] and row[COLS.amount] >= big_threshold and abs(row["price_change"]) < 0.002:
            patterns.append("疑似出货")
        if row.get("amount_ratio", 0) >= 4:
            patterns.append("脉冲式放量")
        if patterns:
            events.append(
                {
                    "time": row.get(COLS.time, ""),
                    "pattern": "、".join(patterns),
                    "reason": f"金额 {row[COLS.amount]:,.0f} 元，价格变化 {row['price_change']:.2%}",
                    "amount": row[COLS.amount],
                    "price": row[COLS.price],
                }
            )

    # 对倒通常表现为相近价位、相近金额的买卖快速交替，这里只做弱规则提示。
    out["prev_side"] = out[COLS.side].shift()
    out["prev_price"] = out[COLS.price].shift()
    out["prev_amount"] = out[COLS.amount].shift()
    cross = out[
        (out[COLS.amount] >= big_threshold)
        & (out["prev_amount"] >= big_threshold)
        & (out[COLS.side] != out["prev_side"])
        & ((out[COLS.price] - out["prev_price"]).abs() / out[COLS.price] < 0.001)
    ]
    for _, row in cross.iterrows():
        events.append(
            {
                "time": row.get(COLS.time, ""),
                "pattern": "疑似对倒",
                "reason": "相近价位出现大额买卖快速切换",
                "amount": row[COLS.amount],
                "price": row[COLS.price],
            }
        )

    return pd.DataFrame(events).sort_values(["time", "amount"], ascending=[True, False]).reset_index(drop=True)


def detect_alerts(
    df: pd.DataFrame,
    big_threshold: float = 500_000,
    volume_window: int = 5,
    volume_multiplier: float = 3.0,
    rapid_price_change_pct: float = 0.006,
) -> pd.DataFrame:
    """异常成交提醒：突然放量、大单密集、价格快速波动。"""

    bars = minute_bars(df)
    if bars.empty:
        return pd.DataFrame(columns=["minute", "alert", "detail"])

    alerts: list[dict[str, object]] = []
    bars["volume_ma"] = bars["volume"].rolling(volume_window, min_periods=2).mean()
    for _, row in bars.iterrows():
        if row["volume_ma"] and row["volume"] >= row["volume_ma"] * volume_multiplier:
            alerts.append({"minute": row["minute"], "alert": "突然放量", "detail": f"成交量约为均量 {row['volume'] / row['volume_ma']:.1f} 倍"})
        if abs(row["return"]) >= rapid_price_change_pct:
            alerts.append({"minute": row["minute"], "alert": "价格快速波动", "detail": f"分钟涨跌幅 {row['return']:.2%}"})

    out = ensure_minute_column(classify_order_size(df, big_threshold=big_threshold))
    dense = out[out[COLS.amount] >= big_threshold].groupby("minute").size()
    for minute, count in dense[dense >= 3].items():
        alerts.append({"minute": minute, "alert": "大单密集", "detail": f"该分钟大单 {count} 笔"})

    return pd.DataFrame(alerts).sort_values("minute").reset_index(drop=True)
