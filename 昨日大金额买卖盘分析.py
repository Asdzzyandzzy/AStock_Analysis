"""命令行示例：大金额买卖盘分析。"""

from __future__ import annotations

import pandas as pd

from astock_analysis.data.cleaning import COLS
from astock_analysis.data.fetchers import fetch_tick_tx
from astock_analysis.indicators.intraday import weighted_average_price

pd.set_option("display.float_format", "{:.2f}".format)


def main(symbol: str = "sh600941", threshold: float = 2_000_000) -> None:
    df = fetch_tick_tx(symbol)
    bigger = df[df[COLS.amount] > threshold].copy()
    print(df)
    print(bigger)

    if bigger.empty:
        print(f"\n没有发现大于 {threshold:,.0f} 元的成交。")
        return

    total_amount = bigger.groupby(COLS.side)[COLS.amount].sum()
    weighted_avg_price = bigger.groupby(COLS.side).apply(weighted_average_price)
    print(f"\n=== 大于 {threshold:,.0f} 元的交易（买/卖）金额统计 ===")
    print(total_amount)
    print(f"\n=== 大于 {threshold:,.0f} 元的交易（买/卖）金额加权均价 ===")
    print(weighted_avg_price)
    print("\n风险提示：结果仅供研究，不构成投资建议。")


if __name__ == "__main__":
    main()
