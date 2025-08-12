import akshare as ak
import pandas as pd

# 让 pandas 显示完整数字而不是科学计数法
pd.set_option('display.float_format', '{:.2f}'.format)

# 获取数据
stock_zh_a_tick_tx = ak.stock_zh_a_tick_tx_js(symbol="sh600941")

A = 2000000

# 筛选成交金额 > A
Bigger_than_A = stock_zh_a_tick_tx[stock_zh_a_tick_tx['成交金额'] > A]

# 按性质分组统计总金额
total_amount = Bigger_than_A.groupby("性质")["成交金额"].sum()

# 按金额加权计算均价（金额加权）
weighted_avg_price = Bigger_than_A.groupby("性质") \
    .apply(lambda g: (g["成交价格"] * g["成交金额"]).sum() / g["成交金额"].sum())

# 打印结果
print(stock_zh_a_tick_tx)
print(Bigger_than_A)

print("\n=== 大于 200 万的交易（买/卖）金额统计 ===")
print(total_amount)

print("\n=== 大于 200 万的交易（买/卖）金额加权均价 ===")
print(weighted_avg_price)
