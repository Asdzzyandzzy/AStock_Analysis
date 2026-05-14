"""日内机器学习特征工程。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from astock_analysis.data.cleaning import COLS, add_side_flags, ensure_minute_column
from astock_analysis.indicators.intraday import minute_bars, price_distribution


FEATURE_COLUMNS = [
    "price_return",
    "volume_change_rate",
    "big_amount_ratio",
    "active_buy_ratio",
    "net_inflow",
    "vwap_deviation",
    "minute_volatility",
    "dense_price_distance",
]


def build_minute_features(df: pd.DataFrame, big_threshold: float = 500_000) -> pd.DataFrame:
    """构造分钟级特征。

    特征包括涨跌幅、成交量变化率、大单占比、主动买入占比、主力净流入、
    VWAP 偏离、分钟级波动率、成交密集价位偏离。
    """

    if df.empty:
        return pd.DataFrame(columns=["minute", *FEATURE_COLUMNS])

    ticks = add_side_flags(ensure_minute_column(df))
    amount = ticks[COLS.amount].fillna(0)
    ticks["big_amount"] = np.where(amount >= big_threshold, amount, 0)
    ticks["buy_amount"] = np.where(ticks["is_buy"], amount, 0)
    ticks["sell_amount"] = np.where(ticks["is_sell"], amount, 0)

    bars = minute_bars(ticks)
    if bars.empty:
        return pd.DataFrame(columns=["minute", *FEATURE_COLUMNS])

    agg = ticks.groupby("minute").agg(
        big_amount=("big_amount", "sum"),
        buy_amount=("buy_amount", "sum"),
        sell_amount=("sell_amount", "sum"),
    )
    features = bars.merge(agg.reset_index(), on="minute", how="left").fillna(0)
    features["price_return"] = features["close"].pct_change().fillna(0)
    features["volume_change_rate"] = features["volume"].pct_change().replace([np.inf, -np.inf], np.nan).fillna(0)
    features["big_amount_ratio"] = features["big_amount"] / features["amount"].replace(0, np.nan)
    features["active_buy_ratio"] = features["buy_amount"] / features["amount"].replace(0, np.nan)
    features["net_inflow"] = features["buy_amount"] - features["sell_amount"]

    cum_amount = features["amount"].cumsum()
    cum_shares = (features["volume"] * 100).cumsum()
    features["vwap"] = cum_amount / cum_shares.replace(0, np.nan)
    features["vwap_deviation"] = (features["close"] - features["vwap"]) / features["vwap"].replace(0, np.nan)
    features["minute_volatility"] = features[["high", "low"]].apply(
        lambda row: (row["high"] - row["low"]) / row["low"] if row["low"] else 0,
        axis=1,
    )

    dist = price_distribution(ticks)
    dense_price = float(dist.sort_values("成交金额", ascending=False).iloc[0][COLS.price]) if not dist.empty else np.nan
    features["dense_price_distance"] = (features["close"] - dense_price) / dense_price if dense_price else 0
    features[FEATURE_COLUMNS] = features[FEATURE_COLUMNS].replace([np.inf, -np.inf], np.nan).fillna(0)
    return features[["minute", *FEATURE_COLUMNS]]


def make_direction_target(features: pd.DataFrame, horizon: int = 1) -> pd.Series:
    """构造短期方向标签：未来 horizon 分钟涨为 1，否则 0。"""

    future_return = features["price_return"].shift(-horizon)
    return (future_return > 0).astype(int)
