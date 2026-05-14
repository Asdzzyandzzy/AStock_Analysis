"""Plotly 图表封装。"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from astock_analysis.data.cleaning import COLS
from astock_analysis.indicators.intraday import minute_bars, price_distribution


def price_volume_chart(df: pd.DataFrame) -> go.Figure:
    """价格走势与成交金额。"""

    bars = minute_bars(df)
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35], vertical_spacing=0.06)
    if bars.empty:
        fig.update_layout(title="价格走势与成交金额")
        return fig

    fig.add_trace(go.Scatter(x=bars["minute"], y=bars["close"], mode="lines", name="价格"), row=1, col=1)
    fig.add_trace(go.Bar(x=bars["minute"], y=bars["amount"], name="成交金额"), row=2, col=1)
    fig.update_layout(height=520, title="日内价格走势与成交金额", hovermode="x unified", legend_orientation="h")
    fig.update_yaxes(title_text="价格", row=1, col=1)
    fig.update_yaxes(title_text="金额", row=2, col=1)
    return fig


def money_flow_chart(df: pd.DataFrame) -> go.Figure:
    """分钟净流入图。"""

    bars = minute_bars(df)
    if bars.empty:
        return go.Figure()
    bars["cum_net_inflow"] = bars["net_inflow"].cumsum()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(x=bars["minute"], y=bars["net_inflow"], name="分钟净流入"), secondary_y=False)
    fig.add_trace(go.Scatter(x=bars["minute"], y=bars["cum_net_inflow"], mode="lines", name="累计净流入"), secondary_y=True)
    fig.update_layout(height=420, title="主力资金流入流出估算", hovermode="x unified", legend_orientation="h")
    fig.update_yaxes(title_text="分钟净流入", secondary_y=False)
    fig.update_yaxes(title_text="累计净流入", secondary_y=True)
    return fig


def order_size_chart(df: pd.DataFrame) -> go.Figure:
    """大单分布图。"""

    if df.empty or "order_size" not in df.columns:
        return go.Figure()
    agg = df.groupby(["order_size", COLS.side], dropna=False)[COLS.amount].sum().reset_index()
    return px.bar(agg, x="order_size", y=COLS.amount, color=COLS.side, title="大单/超大单分布", labels={COLS.amount: "成交金额"})


def side_chart(df: pd.DataFrame) -> go.Figure:
    """买卖方向强弱图。"""

    if df.empty:
        return go.Figure()
    agg = df.groupby(COLS.side, dropna=False)[COLS.amount].sum().reset_index()
    return px.pie(agg, names=COLS.side, values=COLS.amount, title="主动买入/主动卖出金额占比")


def price_distribution_chart(df: pd.DataFrame) -> go.Figure:
    """成交点位分布横向柱状图。"""

    dist = price_distribution(df)
    if dist.empty:
        return go.Figure()
    fig = px.bar(
        dist,
        x="成交金额",
        y=COLS.price,
        orientation="h",
        title="成交价位分布",
        labels={COLS.price: "成交价格", "成交金额": "成交金额"},
    )
    fig.update_layout(height=520, bargap=0.05)
    return fig
