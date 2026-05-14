"""日内指标计算。"""

from __future__ import annotations

import numpy as np
import pandas as pd

from astock_analysis.data.cleaning import COLS, add_side_flags, ensure_minute_column


def weighted_average_price(df: pd.DataFrame) -> float:
    """按成交金额加权均价。"""

    if df.empty or COLS.price not in df.columns or COLS.amount not in df.columns:
        return float("nan")
    amount_sum = df[COLS.amount].sum()
    if not amount_sum:
        return float("nan")
    return float((df[COLS.price] * df[COLS.amount]).sum() / amount_sum)


def summarize_intraday(df: pd.DataFrame) -> dict[str, float]:
    """计算日内核心指标。"""

    if df.empty:
        return {
            "rows": 0,
            "high": np.nan,
            "low": np.nan,
            "vwap": np.nan,
            "avg_price": np.nan,
            "total_amount": 0.0,
            "total_volume": 0.0,
        }
    amount = df.get(COLS.amount, pd.Series(dtype=float))
    volume = df.get(COLS.volume, pd.Series(dtype=float))
    price = df.get(COLS.price, pd.Series(dtype=float))
    vwap = float(amount.sum() / (volume.sum() * 100)) if volume.sum() else weighted_average_price(df)
    return {
        "rows": float(len(df)),
        "high": float(price.max()) if not price.empty else np.nan,
        "low": float(price.min()) if not price.empty else np.nan,
        "vwap": vwap,
        "avg_price": float(price.mean()) if not price.empty else np.nan,
        "total_amount": float(amount.sum()) if not amount.empty else 0.0,
        "total_volume": float(volume.sum()) if not volume.empty else 0.0,
    }


def classify_order_size(
    df: pd.DataFrame,
    big_threshold: float = 500_000,
    super_big_threshold: float = 2_000_000,
) -> pd.DataFrame:
    """按成交金额识别普通单、大单、超大单。"""

    out = df.copy()
    amount = out.get(COLS.amount, pd.Series(0, index=out.index)).fillna(0)
    out["order_size"] = "普通单"
    out.loc[amount >= big_threshold, "order_size"] = "大单"
    out.loc[amount >= super_big_threshold, "order_size"] = "超大单"
    return out


def money_flow(df: pd.DataFrame) -> dict[str, float]:
    """估算主动买入、主动卖出与主力净流入。"""

    if df.empty:
        return {"buy_amount": 0.0, "sell_amount": 0.0, "net_inflow": 0.0, "buy_ratio": 0.0}
    out = add_side_flags(df)
    amount = out[COLS.amount].fillna(0)
    buy_amount = float(amount[out["is_buy"]].sum())
    sell_amount = float(amount[out["is_sell"]].sum())
    total = float(amount.sum())
    return {
        "buy_amount": buy_amount,
        "sell_amount": sell_amount,
        "net_inflow": buy_amount - sell_amount,
        "buy_ratio": buy_amount / total if total else 0.0,
    }


def amount_bands(df: pd.DataFrame) -> pd.DataFrame:
    """成交金额分档统计。"""

    if df.empty or COLS.amount not in df.columns:
        return pd.DataFrame()
    bins = [0, 150_000, 500_000, 2_000_000, np.inf]
    labels = ["0-15万", "15-50万", "50-200万", "200万以上"]
    out = df.copy()
    out["金额区间"] = pd.cut(out[COLS.amount], bins=bins, labels=labels, right=False, include_lowest=True)
    grouped = out.groupby("金额区间", observed=False).agg(
        笔数=(COLS.amount, "size"),
        金额合计=(COLS.amount, "sum"),
        均价=(COLS.price, "mean"),
    )
    grouped["金额加权均价"] = out.groupby("金额区间", observed=False).apply(weighted_average_price)
    return grouped.reset_index()


def minute_bars(df: pd.DataFrame) -> pd.DataFrame:
    """分钟级价格、成交量、净流入。"""

    if df.empty:
        return pd.DataFrame()
    out = add_side_flags(ensure_minute_column(df))
    amount = out[COLS.amount].fillna(0)
    out["signed_amount"] = np.where(out["is_buy"], amount, np.where(out["is_sell"], -amount, 0))
    bars = out.groupby("minute").agg(
        open=(COLS.price, "first"),
        high=(COLS.price, "max"),
        low=(COLS.price, "min"),
        close=(COLS.price, "last"),
        volume=(COLS.volume, "sum"),
        amount=(COLS.amount, "sum"),
        net_inflow=("signed_amount", "sum"),
    )
    bars["return"] = bars["close"].pct_change().fillna(0)
    bars["volume_change"] = bars["volume"].pct_change().replace([np.inf, -np.inf], np.nan).fillna(0)
    return bars.reset_index()


def price_distribution(df: pd.DataFrame) -> pd.DataFrame:
    """成交点位分布。"""

    if df.empty or COLS.price not in df.columns or COLS.amount not in df.columns:
        return pd.DataFrame()
    return (
        df.groupby(COLS.price)
        .agg(成交金额=(COLS.amount, "sum"), 笔数=(COLS.amount, "size"), 成交量=(COLS.volume, "sum"))
        .reset_index()
        .sort_values(COLS.price)
    )


def session_analysis(df: pd.DataFrame) -> pd.DataFrame:
    """开盘、盘中、尾盘维度统计。"""

    if df.empty:
        return pd.DataFrame()
    out = ensure_minute_column(df)

    def label_session(minute: str) -> str:
        if minute <= "10:00":
            return "开盘"
        if minute >= "14:30":
            return "尾盘"
        return "盘中"

    out["时间段"] = out["minute"].map(label_session)
    grouped = out.groupby("时间段").agg(
        笔数=(COLS.amount, "size"),
        金额=(COLS.amount, "sum"),
        最高价=(COLS.price, "max"),
        最低价=(COLS.price, "min"),
        均价=(COLS.price, "mean"),
    )
    grouped["VWAP"] = out.groupby("时间段").apply(weighted_average_price)
    return grouped.reset_index()
