# -*- coding: utf-8 -*-
import time
import pandas as pd
import streamlit as st
import akshare as ak

# ===== 页面设置 =====
st.set_page_config(
    page_title="日内逐笔监控盘",
    page_icon="📈",
    layout="wide",
)

# ===== 侧边栏参数 =====
st.sidebar.title("⚙️ 参数设置")
symbol = st.sidebar.text_input("股票代码（不带交易所前缀）", value="600941", help="示例：600941 或 000001")
refresh_ms = st.sidebar.slider("刷新间隔（毫秒）", min_value=1000, max_value=15000, value=5000, step=500)
big_thresh = st.sidebar.number_input("大单阈值（元）", min_value=10000, value=500000, step=50000)
max_rows_live = st.sidebar.slider("实时区显示最近N行", 50, 2000, 300, 50)

# ===== 会话内持久化：大单表 =====
if "big_trades" not in st.session_state:
    st.session_state.big_trades = pd.DataFrame(columns=["时间", "成交价", "手数", "买卖盘性质", "金额"])

# ===== 工具函数 =====
def fetch_intraday(symbol_code: str) -> pd.DataFrame:
    """
    使用东财逐笔接口：ak.stock_intraday_em(symbol="000001")
    返回列：时间、成交价、手数、买卖盘性质，并新增 金额 = 成交价 * 手数 * 100
    """
    df = ak.stock_intraday_em(symbol=symbol_code)
    # 兼容&清洗
    expected = {"时间", "成交价", "手数", "买卖盘性质"}
    missing = expected - set(df.columns)
    if missing:
        # 如果字段不同，打印看看
        st.warning(f"返回列与预期不同，缺少：{missing}，实际列：{list(df.columns)}")
    # 类型转换
    df["成交价"] = pd.to_numeric(df["成交价"], errors="coerce")
    df["手数"] = pd.to_numeric(df["手数"], errors="coerce")
    # 金额（元）：成交价 * 手数 * 100（1手=100股）
    df["金额"] = df["成交价"] * df["手数"] * 100
    # 去掉空值
    df = df.dropna(subset=["时间", "成交价", "手数", "金额"])
    # 排序按时间
    # 时间是字符串 "HH:MM:SS"，按字符串排序等同时间排序
    df = df.sort_values("时间").reset_index(drop=True)
    return df

def append_big_trades(df: pd.DataFrame, threshold: float):
    """把新增的大单并入会话持久区（去重）"""
    new_big = df[df["金额"] >= threshold].copy()
    if new_big.empty:
        return
    # 用一个“唯一键”避免重复：时间+成交价+手数
    new_big["key"] = new_big["时间"].astype(str) + "_" + new_big["成交价"].astype(str) + "_" + new_big["手数"].astype(str)
    if not st.session_state.big_trades.empty:
        st.session_state.big_trades["key"] = (
            st.session_state.big_trades["时间"].astype(str) + "_" +
            st.session_state.big_trades["成交价"].astype(str) + "_" +
            st.session_state.big_trades["手数"].astype(str)
        )
        merged = pd.concat([st.session_state.big_trades, new_big], ignore_index=True)
        st.session_state.big_trades = merged.drop_duplicates(subset=["key"]).drop(columns=["key"])
    else:
        st.session_state.big_trades = new_big.drop(columns=["key"])

def fmt_df_for_view(df: pd.DataFrame) -> pd.DataFrame:
    """美化展示：千分位、两位小数"""
    if df.empty:
        return df
    df_view = df.copy()
    # 保证显示不是科学计数法
    pd.options.display.float_format = '{:.2f}'.format
    # 转换为更友好的字符串
    for col in ["成交价"]:
        df_view[col] = df_view[col].map(lambda x: f"{x:,.2f}")
    for col in ["手数"]:
        df_view[col] = df_view[col].map(lambda x: f"{int(x):,}")
    for col in ["金额"]:
        df_view[col] = df_view[col].map(lambda x: f"{x:,.0f}")
    return df_view

# ===== 页面头部 =====
st.markdown(
    """
    <style>
    .metric-small .stMetric { background: rgba(255,255,255,0.6); border-radius: 16px; padding: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    .box { background: #ffffff; border-radius: 16px; padding: 14px; box-shadow: 0 8px 24px rgba(0,0,0,0.06); }
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("📊 A股日内逐笔监控盘")
st.caption("左侧实时刷新；右侧大单（≥阈值）独立累积、不随刷新清空。")

# ===== 自动刷新 =====
st_autorefresh = st.experimental_rerun  # 兼容；我们使用 st.empty() 循环来刷新
# 更简单：使用内置的 autorefresh
st.experimental_set_query_params(ts=int(time.time()))  # 避免浏览器缓存
st_autorefresh_token = st.experimental_data_editor if False else None  # 占位避免lint

st_autorefresh_placeholder = st.empty()
st_autorefresh_placeholder.write(f"⏱ 正在每 {refresh_ms/1000:.1f}s 自动刷新…")

# ===== 主体布局 =====
col_live, col_big = st.columns([2, 1])

# ===== 数据抓取与显示 =====
df = fetch_intraday(symbol)

# 更新累计大单
append_big_trades(df, big_thresh)

# 顶部统计
total_amt = df["金额"].sum() if not df.empty else 0
big_cnt = len(st.session_state.big_trades)
last_time = df["时间"].iloc[-1] if not df.empty else "--"

m1, m2, m3 = st.columns(3)
m1.metric("当日成交金额(估算, 元)", f"{total_amt:,.0f}")
m2.metric(f"累计大单(≥{big_thresh:,.0f})笔数", f"{big_cnt:,}")
m3.metric("最新时间", f"{last_time}")

# ===== 左：实时数据（可刷新） =====
with col_live:
    st.subheader("📈 实时逐笔（自动刷新）")
    df_live = df.tail(max_rows_live)
    st.dataframe(
        fmt_df_for_view(df_live)[["时间", "成交价", "手数", "买卖盘性质", "金额"]],
        use_container_width=True,
        height=520
    )

# ===== 右：大单池（不清空） =====
with col_big:
    st.subheader(f"💰 大单池（≥{big_thresh:,.0f} 元）— 会话内常驻")
    st.caption("此区域内容不会因为左侧刷新而清空；仅去重新增。")
    st.dataframe(
        fmt_df_for_view(st.session_state.big_trades)[["时间", "成交价", "手数", "买卖盘性质", "金额"]],
        use_container_width=True,
        height=520
    )
    if not st.session_state.big_trades.empty:
        csv = st.session_state.big_trades.to_csv(index=False).encode("utf-8-sig")
        st.download_button("下载大单CSV", data=csv, file_name=f"{symbol}_big_trades.csv", mime="text/csv")

# ===== 自动刷新实现 =====
# Streamlit提供 st.experimental_rerun，但更简单：用 st.experimental_singleton? 这里用 JS 刷新更稳
st.markdown(
    f"""
    <script>
    setInterval(function(){{
        window.location.reload();
    }}, {refresh_ms});
    </script>
    """,
    unsafe_allow_html=True
)
