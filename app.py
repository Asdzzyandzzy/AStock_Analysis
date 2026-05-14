"""Streamlit 主入口。"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from astock_analysis.config import load_config
from astock_analysis.data.cleaning import COLS, normalize_symbol
from astock_analysis.data.fetchers import DataFetchError, fetch_intraday_em, fetch_tick_tx
from astock_analysis.indicators.intraday import (
    amount_bands,
    classify_order_size,
    money_flow,
    session_analysis,
    summarize_intraday,
)
from astock_analysis.indicators.tick_patterns import detect_alerts, detect_tick_patterns
from astock_analysis.ml.features import build_minute_features
from astock_analysis.ml.models import cluster_behaviour, detect_anomalies, feature_explanation, train_direction_classifier
from astock_analysis.visualization.charts import (
    money_flow_chart,
    order_size_chart,
    price_distribution_chart,
    price_volume_chart,
    side_chart,
)


config = load_config()

st.set_page_config(page_title="A股日内分析系统", page_icon="📈", layout="wide")


@st.cache_data(show_spinner=True, ttl=config.cache_ttl_seconds)
def load_ticks(symbol: str, data_source: str) -> pd.DataFrame:
    """缓存获取逐笔数据。"""

    if data_source == "腾讯逐笔 stock_zh_a_tick_tx_js":
        return fetch_tick_tx(symbol)
    return fetch_intraday_em(symbol)


def csv_bytes(df: pd.DataFrame) -> bytes:
    """导出 CSV。"""

    return df.to_csv(index=False).encode("utf-8-sig")


def metric_text(value: float, digits: int = 2) -> str:
    if pd.isna(value):
        return "--"
    return f"{value:,.{digits}f}"


st.title("A股日内逐笔成交分析")
st.caption("基于 AKShare 的分时/逐笔成交研究工具，仅供研究，不构成投资建议。")

with st.sidebar:
    st.header("参数")
    data_source = st.selectbox(
        "数据接口",
        ["腾讯逐笔 stock_zh_a_tick_tx_js", "东方财富日内 stock_intraday_em"],
        index=0,
    )
    default_symbol = config.default_symbol if data_source.startswith("腾讯") else config.intraday_symbol
    symbol = st.text_input("股票代码", value=default_symbol, help="腾讯接口示例 sh600941；东方财富接口示例 600941")
    col1, col2 = st.columns(2)
    with col1:
        big_threshold = st.number_input("大单阈值", min_value=10_000, value=int(config.big_order_amount), step=50_000)
    with col2:
        super_big_threshold = st.number_input("超大单阈值", min_value=50_000, value=int(config.super_big_order_amount), step=100_000)
    min_amt = st.number_input("筛选金额下限", min_value=0, value=2_000_000, step=100_000)
    max_amt = st.number_input("筛选金额上限", min_value=0, value=10_000_000, step=100_000)
    show_raw = st.checkbox("显示标准化原始数据", value=False)
    use_ml = st.checkbox("启用机器学习示例", value=False)
    refresh = st.button("刷新数据")

if refresh:
    st.cache_data.clear()

if max_amt < min_amt:
    st.warning("金额上限小于下限，已自动交换。")
    min_amt, max_amt = max_amt, min_amt

try:
    df = load_ticks(symbol, data_source)
except DataFetchError as exc:
    st.error(str(exc))
    st.stop()
except Exception as exc:
    st.error(f"获取数据失败：{exc}")
    st.stop()

if df.empty:
    st.warning("未获取到数据。请检查股票代码、交易时段或稍后重试。")
    st.stop()

df = classify_order_size(df, big_threshold=big_threshold, super_big_threshold=super_big_threshold)
summary = summarize_intraday(df)
flow = money_flow(df)

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("逐笔条数", f"{int(summary['rows']):,}")
k2.metric("日内高点", metric_text(summary["high"]))
k3.metric("日内低点", metric_text(summary["low"]))
k4.metric("VWAP", metric_text(summary["vwap"], 4))
k5.metric("总成交金额", metric_text(summary["total_amount"], 0))

k6, k7, k8, k9 = st.columns(4)
k6.metric("主动买入金额", metric_text(flow["buy_amount"], 0))
k7.metric("主动卖出金额", metric_text(flow["sell_amount"], 0))
k8.metric("估算净流入", metric_text(flow["net_inflow"], 0))
k9.metric("主动买入占比", f"{flow['buy_ratio']:.2%}")

tabs = st.tabs(["总览", "大单与买卖盘", "逐笔行为", "时间段与异常", "机器学习", "数据"])

with tabs[0]:
    st.plotly_chart(price_volume_chart(df), use_container_width=True)
    st.plotly_chart(money_flow_chart(df), use_container_width=True)
    st.plotly_chart(price_distribution_chart(df), use_container_width=True)

with tabs[1]:
    section = df[(df[COLS.amount] >= min_amt) & (df[COLS.amount] <= max_amt)].copy()
    st.subheader("金额区间筛选")
    if section.empty:
        st.info("当前金额区间内没有成交记录。")
    else:
        by_side = section.groupby(COLS.side, dropna=False).agg(
            笔数=(COLS.amount, "size"),
            金额=(COLS.amount, "sum"),
            均价=(COLS.price, "mean"),
        )
        st.dataframe(by_side, use_container_width=True)
        st.download_button(
            "下载区间明细 CSV",
            data=csv_bytes(section),
            file_name=f"{normalize_symbol(symbol)}_{int(min_amt)}_{int(max_amt)}.csv",
            mime="text/csv",
        )
        st.dataframe(section, use_container_width=True, height=320)

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(order_size_chart(df), use_container_width=True)
    with c2:
        st.plotly_chart(side_chart(df), use_container_width=True)
    st.subheader("成交金额分档")
    st.dataframe(amount_bands(df), use_container_width=True)

with tabs[2]:
    st.subheader("逐笔成交行为识别")
    st.caption("规则标签只用于研究提示，不代表真实交易意图。")
    patterns = detect_tick_patterns(df, big_threshold=big_threshold)
    if patterns.empty:
        st.info("暂未识别到明显的拉升、砸盘、吸筹、出货、对倒或脉冲放量提示。")
    else:
        st.dataframe(patterns, use_container_width=True, height=460)
        st.download_button("下载行为识别 CSV", data=csv_bytes(patterns), file_name=f"{normalize_symbol(symbol)}_patterns.csv")

with tabs[3]:
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("时间段分析")
        st.dataframe(session_analysis(df), use_container_width=True)
    with c2:
        st.subheader("异常成交提醒")
        alerts = detect_alerts(
            df,
            big_threshold=big_threshold,
            volume_window=config.sudden_volume_window,
            volume_multiplier=config.sudden_volume_multiplier,
            rapid_price_change_pct=config.rapid_price_change_pct,
        )
        if alerts.empty:
            st.info("暂无异常提醒。")
        else:
            st.dataframe(alerts, use_container_width=True)

with tabs[4]:
    st.subheader("可选机器学习示例")
    if not use_ml:
        st.info("请在侧边栏勾选“启用机器学习示例”。主程序默认不依赖模型结果。")
    else:
        features = build_minute_features(df, big_threshold=big_threshold)
        st.markdown("##### 分钟级特征")
        st.dataframe(features, use_container_width=True, height=260)
        st.markdown("##### 特征解释")
        st.dataframe(feature_explanation(features), use_container_width=True)
        try:
            c1, c2, c3 = st.columns(3)
            with c1:
                anomaly = detect_anomalies(features)
                st.caption(anomaly.description)
                st.dataframe(anomaly.output, use_container_width=True, height=260)
            with c2:
                classifier = train_direction_classifier(features, model_type="logistic")
                st.caption(classifier.description)
                st.dataframe(classifier.output, use_container_width=True, height=260)
            with c3:
                clusters = cluster_behaviour(features, n_clusters=3)
                st.caption(clusters.description)
                st.dataframe(clusters.output, use_container_width=True, height=260)
        except ImportError as exc:
            st.warning(str(exc))

with tabs[5]:
    if show_raw:
        st.dataframe(df, use_container_width=True, height=520)
    else:
        st.info("在侧边栏勾选“显示标准化原始数据”后查看。")

st.markdown("---")
st.caption("风险提示：本工具所有结果仅供学习、研究和数据观察，不构成任何投资建议或交易依据。")
