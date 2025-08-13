import streamlit as st
import pandas as pd
import numpy as np
import akshare as ak
import plotly.express as px

st.set_page_config(page_title="大单成交分析（AKShare）BY 周梓洋", page_icon="💹", layout="wide")

st.title("A股逐笔成交 · 大单筛选与分析 by zzy")
st.caption("Author:周梓洋 基于 AKShare 的 `stock_zh_a_tick_tx_js` 数据接口")

# --- Sidebar controls
with st.sidebar:
    st.header("参数设置")
    symbol = st.text_input(
        "证券代码（带交易所前缀）",
        value="sh600941",
        help="例如：上交所前缀 sh，如 sh600941；深交所前缀 sz，如 sz000001",
    )
    # 手写输入下限与上限
    col_min, col_max = st.columns(2)
    with col_min:
        min_amt = st.number_input("金额下限（元）", min_value=0, value=2_000_000, step=100_000)
    with col_max:
        max_amt = st.number_input("金额上限（元）", min_value=0, value=10_000_000, step=100_000)

    show_raw = st.checkbox("显示原始明细", value=False)
    st.markdown("---")
    st.caption("提示：AKShare 接口一般返回当日数据；")

# 自动纠正：若用户把上下限填反，则交换
if max_amt < min_amt:
    st.warning(f"检测到金额上限（{max_amt:,}）小于下限（{min_amt:,}），已自动调整为正确区间。")
    min_amt, max_amt = max_amt, min_amt

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
c3.metric("金额区间（元）", f"{min_amt:,.0f} ~ {max_amt:,.0f}")

# --- 自定义金额区间筛选（原有功能保留）
st.markdown(f"### 金额区间筛选：≥ {min_amt:,} 且 ≤ {max_amt:,}")
if "成交金额" not in df.columns:
    st.warning("数据中未包含“成交金额”列，无法进行金额区间筛选。")
    st.stop()

section = df[(df["成交金额"] >= min_amt) & (df["成交金额"] <= max_amt)].copy()

if section.empty:
    st.info("没有找到落入设定金额区间的成交。可以调宽区间再试。")
else:
    # 按“性质”汇总与金额加权均价
    if "性质" in section.columns:
        agg_sum = section.groupby("性质", dropna=False)["成交金额"].sum().rename("金额合计")

        def wavg(g: pd.DataFrame) -> float:
            amt_sum = g["成交金额"].sum()
            if amt_sum == 0 or "成交价格" not in g.columns:
                return float("nan")
            return float((g["成交价格"] * g["成交金额"]).sum() / amt_sum)

        wavg_series = section.groupby("性质").apply(wavg).rename("金额加权均价")
        summary = pd.concat([agg_sum, wavg_series], axis=1).sort_values("金额合计", ascending=False)
    else:
        summary = pd.DataFrame()

    if not summary.empty:
        st.markdown("#### 按性质统计（当前金额区间）")
        st.dataframe(
            summary.style.format({"金额合计": "{:,.2f}", "金额加权均价": "{:,.4f}"}),
            use_container_width=True,
        )

    st.markdown("#### 区间内成交明细")
    st.dataframe(section, use_container_width=True, height=420)

    # 下载按钮（CSV）
    @st.cache_data
    def to_csv_bytes(x: pd.DataFrame) -> bytes:
        return x.to_csv(index=False).encode("utf-8-sig")

    col_dl1, col_dl2 = st.columns(2)
    col_dl1.download_button(
        "下载区间明细 CSV",
        data=to_csv_bytes(section),
        file_name=f"{symbol}_trades_{int(min_amt)}_{int(max_amt)}.csv",
        mime="text/csv",
    )
    if not summary.empty:
        col_dl2.download_button(
            "下载区间统计 CSV",
            data=to_csv_bytes(summary.reset_index()),
            file_name=f"{symbol}_trades_summary_{int(min_amt)}_{int(max_amt)}.csv",
            mime="text/csv",
        )

# === 分档统计（新增） =======================================================
st.markdown("---")
st.subheader("成交金额分档统计（全量数据）")

# 1) 定义分档
bins = [0, 150_000, 500_000, 2_000_000, np.inf]
labels = ["0-15万", "15-50万", "50-200万", "200万以上"]

# 2) 选择统计基准：全量 df（若想受自定义区间限制，把 base = section）
base = df.copy()
base = base[pd.notna(base.get("成交金额"))].copy()
base["金额区间"] = pd.cut(
    base["成交金额"],
    bins=bins,
    labels=labels,
    right=False,            # 左闭右开：[a,b)
    include_lowest=True
)

# 3) 按分档汇总：笔数/金额合计/金额加权均价
def wavg_group(g: pd.DataFrame) -> float:
    if "成交价格" not in g.columns:
        return float("nan")
    amt = g["成交金额"].sum()
    if amt == 0:
        return float("nan")
    return float((g["成交价格"] * g["成交金额"]).sum() / amt)

summary_band = base.groupby("金额区间", dropna=False).agg(
    笔数=("成交金额", "size"),
    金额合计=("成交金额", "sum")
)
summary_band["金额加权均价"] = base.groupby("金额区间").apply(wavg_group).values

# 4) 分档 × 性质 透视表（金额合计）
if "性质" in base.columns:
    pivot_band_kind = pd.pivot_table(
        base,
        index="金额区间",
        columns="性质",
        values="成交金额",
        aggfunc="sum",
        fill_value=0,
        margins=True,           # ← 开启总计
        margins_name="总计",     # ← 总计行/列名称
    )
else:
    pivot_band_kind = pd.DataFrame()


# 5) 展示
st.markdown("##### 按分档汇总")
st.dataframe(
    summary_band.style.format({"金额合计": "{:,.2f}", "金额加权均价": "{:,.4f}"}),
    use_container_width=True,
)

if not pivot_band_kind.empty:
    st.markdown("##### 分档 × 性质 金额合计（元）")
    st.dataframe(
        pivot_band_kind.style.format("{:,.2f}"),
        use_container_width=True,
    )
# === 分档统计（新增）结束 ===================================================


# === 成交价格分布直方图（x轴为成交金额，y轴为成交价格） ===
def plot_price_hist(data, title):
    if "成交价格" not in data.columns or "成交金额" not in data.columns:
        st.warning("数据中未包含“成交价格”或“成交金额”列，无法绘制价格分布图。")
        return
    # 按价格分组统计成交金额
    price_amounts = (
        data.groupby("成交价格")["成交金额"]
        .sum()
        .reset_index(name="成交金额合计")
        .sort_values("成交价格")
    )
    fig = px.bar(
        price_amounts,
        x="成交金额合计",
        y="成交价格",
        orientation="h",
        title=title,
        labels={"成交金额合计": "成交金额（元）", "成交价格": "成交价格（元）"},
    )
    fig.update_layout(
        yaxis=dict(showgrid=False),
        xaxis=dict(showgrid=False),
        height=600,
        bargap=0,
    )
    st.plotly_chart(fig, use_container_width=True)

# 总计
plot_price_hist(base, "成交价格分布（总计）")

# 各金额区间
for label in labels:  # labels 来自前面定义 ["0-15万", "15-50万", "50-200万", "200万以上"]
    subset = base[base["金额区间"] == label]
    if not subset.empty:
        plot_price_hist(subset, f"成交价格分布（{label}）")

# 可选：显示原始数据
if show_raw:
    st.markdown("---")
    st.markdown("### 原始逐笔数据预览")
    st.dataframe(df, use_container_width=True, height=350)

st.markdown("---")
st.caption("© 作者声明：本工具仅用于学习与研究，不构成投资建议。by zzy")
