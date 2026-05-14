# AStock Analysis

AStock Analysis 是一个基于 Python、Streamlit 和 AKShare 的 A 股日内逐笔成交分析项目。项目用于观察分时成交、大单/超大单、主动买卖盘、主力资金流入流出估算、成交价位分布、逐笔行为提示以及可选机器学习示例。

> 风险提示：本项目所有结果仅供学习、研究和数据观察，不构成任何投资建议或交易依据。AKShare 数据接口、字段和可用性可能随数据源变化。

## 当前项目常见问题

重构前项目主要是脚本式结构，几个 Streamlit/命令行文件平铺在根目录中，数据获取、字段清洗、指标计算、可视化和页面逻辑混在一起。这样会带来几个问题：

- AKShare 字段变化时，需要在多个页面重复修改。
- 大单、买卖盘、价格分布等逻辑复用困难。
- 缺少统一异常处理、空数据处理、缓存、日志和配置。
- 机器学习功能没有独立边界，容易影响主程序稳定性。
- 缺少 README、依赖文件和目录说明，后续维护成本较高。

## 功能

- 支持 AKShare 逐笔数据接口：
  - `stock_zh_a_tick_tx_js`
  - `stock_intraday_em`
- 日内核心指标：
  - 日内高点、低点、VWAP、均价
  - 成交金额、成交量、分钟级变化
  - 成交点位分布
- 大单与买卖盘：
  - 大单/超大单识别
  - 主动买入、主动卖出金额统计
  - 主力资金净流入估算
  - 买卖盘强弱展示
- 逐笔成交行为提示：
  - 价格拉升
  - 砸盘
  - 疑似吸筹
  - 疑似出货
  - 疑似对倒
  - 脉冲式放量
- 时间段分析：
  - 开盘
  - 盘中
  - 尾盘
- 异常提醒：
  - 突然放量
  - 大单密集
  - 价格快速波动
- 可视化：
  - 价格走势与成交金额
  - 大单分布
  - 买卖方向
  - 资金净流入
  - 成交价位分布
- 可选机器学习：
  - IsolationForest 异常成交检测
  - LogisticRegression / RandomForest 短期方向分类示例
  - KMeans 成交行为聚类
  - 分钟级特征构造与解释

## 安装

建议使用 Python 3.10 及以上版本。

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

如果只想安装主程序依赖，也可以使用：

```bash
pip install .
```

机器学习功能需要：

```bash
pip install ".[ml]"
```

## 运行

推荐入口：

```bash
streamlit run app.py
```

旧入口仍保留兼容：

```bash
streamlit run sellbuyAnalyis.py
streamlit run 日内分时数据实时刷新.py
python 昨日大金额买卖盘分析.py
```

## 推荐目录结构

```text
AStock_Analysis/
  app.py                         # Streamlit 主入口
  config.yaml                    # 默认配置
  requirements.txt               # 依赖列表
  pyproject.toml                 # 项目元数据与可选依赖
  README.md                      # 项目说明
  sellbuyAnalyis.py              # 旧 Streamlit 入口兼容
  日内分时数据实时刷新.py          # 旧 Streamlit 入口兼容
  昨日大金额买卖盘分析.py          # 命令行示例
  astock_analysis/
    config.py                    # 配置读取
    data/
      cleaning.py                # 字段兼容、标准化、股票代码规范化
      fetchers.py                # AKShare 数据获取
    indicators/
      intraday.py                # 日内指标、资金流、分档、时间段分析
      tick_patterns.py           # 逐笔行为识别与异常提醒
    ml/
      features.py                # 分钟级特征工程
      models.py                  # IsolationForest、分类、聚类示例
    visualization/
      charts.py                  # Plotly 图表
    utils/
      logging.py                 # 日志
```

## 数据源说明

项目使用 AKShare 获取 A 股日内逐笔/分时成交数据。不同接口返回字段可能不同，因此项目统一转换为标准字段：

| 标准字段 | 含义 | 兼容来源字段示例 |
| --- | --- | --- |
| `time` | 成交时间 | 时间、成交时间 |
| `price` | 成交价格 | 成交价格、成交价、价格 |
| `volume` | 成交量或手数 | 成交量、手数、成交手数 |
| `amount` | 成交金额 | 成交金额、金额 |
| `side` | 买卖盘方向 | 性质、买卖盘性质、方向 |

当接口没有直接返回成交金额时，项目会使用 `成交价 * 手数 * 100` 进行估算。

## 指标解释

- VWAP：成交量加权平均价格，用于观察日内成交重心。
- 大单/超大单：按成交金额阈值划分，默认大单为 50 万元，超大单为 200 万元。
- 主动买入占比：主动买入金额占总成交金额的比例。
- 主力净流入估算：主动买入金额减主动卖出金额。由于逐笔数据的方向判定依赖数据源，该值只能作为估算。
- 成交密集价位：成交金额最大的价位，可用于观察日内资金集中成交区域。
- 分钟级波动率：分钟内最高价与最低价的相对差值。
- 异常提醒：基于规则判断突然放量、大单密集和价格快速波动，仅作研究提示。

## 机器学习示例

机器学习模块位于 `astock_analysis/ml/`，默认不影响主程序运行。页面中勾选“启用机器学习示例”后才会运行。

特征包括：

- 价格涨跌幅
- 成交量变化率
- 大单金额占比
- 主动买入占比
- 主力净流入
- VWAP 偏离
- 分钟级波动率
- 成交密集价位偏离

代码示例：

```python
from astock_analysis.data.fetchers import fetch_tick_tx
from astock_analysis.ml.features import build_minute_features
from astock_analysis.ml.models import detect_anomalies, train_direction_classifier, cluster_behaviour

df = fetch_tick_tx("sh600941")
features = build_minute_features(df, big_threshold=500_000)

anomaly_result = detect_anomalies(features)
direction_result = train_direction_classifier(features, model_type="logistic")
cluster_result = cluster_behaviour(features, n_clusters=3)

print(anomaly_result.output)
print(direction_result.output)
print(cluster_result.output)
```

## 文件用途

- `app.py`：统一 Streamlit 页面，包含总览、大单、逐笔行为、异常提醒、机器学习和数据查看。
- `astock_analysis/data/fetchers.py`：封装 AKShare 接口和异常处理。
- `astock_analysis/data/cleaning.py`：字段兼容、标准化、股票代码格式处理。
- `astock_analysis/indicators/intraday.py`：核心指标计算。
- `astock_analysis/indicators/tick_patterns.py`：逐笔行为识别和异常提醒。
- `astock_analysis/visualization/charts.py`：Plotly 图表。
- `astock_analysis/ml/features.py`：机器学习特征构造。
- `astock_analysis/ml/models.py`：模型训练、预测和解释示例。
- `config.yaml`：默认股票代码、缓存时间、大单阈值、异常提醒阈值。

## 后续扩展方向

- 增加历史日内数据落盘和多日回测。
- 增加多股票监控列表与板块维度对比。
- 增加盘口委托队列、买一卖一变化和撤单分析。
- 增加更严格的交易行为规则校验，降低误报。
- 接入本地数据库，例如 SQLite、DuckDB 或 PostgreSQL。
- 为机器学习模块增加标签生成、训练集管理、模型保存和离线评估。
- 增加单元测试和模拟 AKShare 字段变化的回归测试。

## 风险提示

本项目不是量化交易系统，也不提供买卖建议。逐笔成交方向、主力资金流和交易行为标签均依赖数据源字段与规则估算，可能存在延迟、缺失、误判或接口变化。任何投资决策都需要结合更多信息并自行承担风险。
