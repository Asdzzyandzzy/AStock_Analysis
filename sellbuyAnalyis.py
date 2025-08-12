import streamlit as st
import pandas as pd
import numpy as np
import akshare as ak

st.set_page_config(page_title="大单成交分析（AKShare）BY 周梓洋", page_icon="💹", layout="wide")

st.title("💹 A股逐笔成交 · 大单筛选与分析")
st.caption("Author:周梓洋 基于 AKShare 的 `stock_zh_a_tick_tx_js` 数据接口")

# --- Sidebar controls
with st.sidebar:
    st.header("参数设置")
    symbol = st.text_input(
        "证券代码（带交易所前缀）",
        value="sh600941",
        help="例如：上交所前缀 sh，如 sh600941；深交所前缀 sz，如 sz000001",
    )
    threshold = st.number_input("成交金额阈值（元）", min_value=0, value=2_000_000, step=100_000)
    show_raw = st.checkbox("显示原始明细", value=False)
    st.markdown("---")
    st.caption("提示：AKShare 接口一般返回当日数据；若非交易时段或代码无效，可能为空。")

@st.cache_data(show_spinner=True, ttl=120)
def load_ticks(sym: str) -> pd.DataFrame:
    df = ak.stock_zh_a_tick_tx_js(symbol=sym)
    # 保护性转换：有些列可能是字符串
    for col in ["成交价格", "成交量", "成交金额"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    # 统一时间列类型
    if "时间" in df.columns:
        try:
            df["时间"] = pd.to_datetime(df["时间"])
        except Exception:
            pass
    return df

# --- Load
try:
    df = load_ticks(symbol)
except Exception as e:
    st.error(f"获取数据失败：{e}")
    st.stop()

if df is None or df.empty:
    st.warning("未获取到数据。请检查代码是否正确、是否在交易时段，或稍后再试。")
    st.stop()

# --- KPI: 基本信息
total_rows = len(df)
total_amt = float(np.nansum(df.get("成交金额", pd.Series(dtype=float))))
buy_amt = float(np.nansum(df.loc[df.get("性质", "").eq("买盘"), "成交金额"])) if "性质" in df.columns else np.nan
sell_amt = float(np.nansum(df.loc[df.get("性质", "").eq("卖盘"), "成交金额"])) if "性质" in df.columns else np.nan

c1, c2, c3 = st.columns(3)
c1.metric("逐笔条数", f"{total_rows:,}")
c2.metric("总成交金额（元）", f"{total_amt:,.2f}")
c3.metric("阈值（元）", f"{threshold:,.0f}")

st.markdown("### ≥ 阈值的大单筛选")
bigger = df[df["成交金额"] > threshold] if "成交金额" in df.columns else pd.DataFrame()

if bigger.empty:
    st.info("没有找到大于设定阈值的成交。可以降低阈值再试。")
else:
    # 分组求和与金额加权均价
    if "性质" in bigger.columns:
        agg_sum = bigger.groupby("性质", dropna=False)["成交金额"].sum().rename("金额合计")

        def wavg(g: pd.DataFrame) -> float:
            v = (g["成交价格"] * g["成交金额"]).sum() / g["成交金额"].sum()
            return float(v)

        wavg_series = bigger.groupby("性质").apply(wavg).rename("金额加权均价")
        summary = pd.concat([agg_sum, wavg_series], axis=1).sort_values("金额合计", ascending=False)
    else:
        summary = pd.DataFrame()

    st.dataframe(
        summary.style.format({"金额合计": "{:,.2f}", "金额加权均价": "{:,.4f}"}),
        use_container_width=True,
    )

    st.markdown("#### 大单明细")
    st.dataframe(bigger, use_container_width=True, height=400)

    # 下载按钮（CSV）
    @st.cache_data
    def to_csv_bytes(x: pd.DataFrame) -> bytes:
        return x.to_csv(index=False).encode("utf-8-sig")

    col_dl1, col_dl2 = st.columns(2)
    col_dl1.download_button(
        "下载大单明细 CSV",
        data=to_csv_bytes(bigger),
        file_name=f"{symbol}_big_trades_over_{int(threshold)}.csv",
        mime="text/csv",
    )
    if not summary.empty:
        col_dl2.download_button(
            "下载大单统计 CSV",
            data=to_csv_bytes(summary.reset_index()),
            file_name=f"{symbol}_big_trades_summary.csv",
            mime="text/csv",
        )

if show_raw:
    st.markdown("---")
    st.markdown("### 原始逐笔数据预览")
    st.dataframe(df, use_container_width=True, height=350)

st.markdown("---")
st.caption("© 使用 AKShare 获取行情数据。本工具仅用于学习与研究，不构成投资建议。")
