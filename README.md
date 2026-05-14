# AStock Analysis

AStock Analysis is a Python and Streamlit project for intraday A-share tick analysis. It uses AKShare as the data source and provides research-oriented views for intraday prices, large orders, active buy/sell flow, estimated main-fund movement, price-level distribution, tick-level behavior signals, anomaly alerts, and optional machine learning examples.

> Risk disclaimer: This project is for learning, research, and data observation only. It does not constitute investment advice, trading advice, or a recommendation to buy or sell any security. AKShare data availability, latency, and field names may change with upstream data providers.

## Existing Project Issues

Before refactoring, the project was mostly organized as several standalone scripts in the repository root. Data fetching, field cleaning, indicator calculation, visualization, and Streamlit UI logic were tightly coupled. This created several maintenance risks:

- AKShare field changes had to be handled repeatedly in multiple scripts.
- Large-order, buy/sell-flow, and price-distribution logic was difficult to reuse.
- Error handling, empty-data handling, caching, logging, and configuration were not centralized.
- Machine learning code had no clear boundary and could affect the main application.
- The project lacked dependency files, project metadata, and complete documentation.

## Features

- AKShare intraday/tick data support:
  - `stock_zh_a_tick_tx_js`
  - `stock_intraday_em`
- Intraday indicators:
  - Intraday high and low
  - VWAP and average price
  - Turnover amount and volume changes
  - Price-level transaction distribution
- Large order and order-flow analysis:
  - Large-order and super-large-order identification
  - Active buy and active sell amount
  - Estimated main-fund net inflow
  - Buy/sell strength comparison
- Tick-level behavior signals:
  - Price lift
  - Heavy sell pressure
  - Possible accumulation
  - Possible distribution
  - Possible wash trading
  - Pulse-like volume spike
- Session analysis:
  - Opening session
  - Midday/intraday session
  - Closing session
- Anomaly alerts:
  - Sudden volume spike
  - Dense large-order activity
  - Rapid price movement
- Visualizations:
  - Intraday price and turnover chart
  - Large-order distribution
  - Buy/sell direction chart
  - Estimated net-fund-flow chart
  - Transaction price-level distribution
- Optional machine learning examples:
  - IsolationForest for abnormal transaction detection
  - LogisticRegression / RandomForest for short-term direction classification
  - KMeans for transaction behavior clustering
  - Feature construction and feature explanation examples

## Installation

Python 3.10 or later is recommended.

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

You can also install the main package dependencies with:

```bash
pip install .
```

Machine learning features require the optional ML dependencies:

```bash
pip install ".[ml]"
```

## Run

Recommended entry point:

```bash
streamlit run app.py
```

Legacy entry points are still kept for compatibility:

```bash
streamlit run sellbuyAnalyis.py
streamlit run 日内分时数据实时刷新.py
python 昨日大金额买卖盘分析.py
```

## Recommended Directory Structure

```text
AStock_Analysis/
  app.py                         # Main Streamlit entry point
  config.yaml                    # Default runtime configuration
  requirements.txt               # Dependency list
  pyproject.toml                 # Project metadata and optional dependencies
  README.md                      # Project documentation
  sellbuyAnalyis.py              # Legacy Streamlit entry point
  日内分时数据实时刷新.py          # Legacy Streamlit entry point
  昨日大金额买卖盘分析.py          # Command-line example
  astock_analysis/
    config.py                    # Config loader
    data/
      cleaning.py                # Field compatibility and normalization
      fetchers.py                # AKShare data fetchers
    indicators/
      intraday.py                # Intraday indicators and session analysis
      tick_patterns.py           # Tick-level behavior signals and alerts
    ml/
      features.py                # Minute-level feature engineering
      models.py                  # IsolationForest, classifiers, and clustering examples
    visualization/
      charts.py                  # Plotly charts
    utils/
      logging.py                 # Logging utilities
```

## Data Sources

The project uses AKShare to fetch A-share intraday and tick-level transaction data. Different AKShare interfaces may return different field names, so the project normalizes input data into a standard schema:

| Standard Field | Meaning | Compatible Source Fields |
| --- | --- | --- |
| `time` | Transaction time | 时间, 成交时间 |
| `price` | Transaction price | 成交价格, 成交价, 价格 |
| `volume` | Volume or lots | 成交量, 手数, 成交手数 |
| `amount` | Transaction amount | 成交金额, 金额 |
| `side` | Buy/sell direction | 性质, 买卖盘性质, 方向 |

If a data interface does not directly provide transaction amount, the project estimates it with:

```text
price * lots * 100
```

## Indicator Notes

- VWAP: Volume-weighted average price. It is used to observe the intraday transaction center of gravity.
- Large order / super-large order: Orders are classified by transaction amount. Defaults are RMB 500,000 for large orders and RMB 2,000,000 for super-large orders.
- Active buy ratio: Active buy amount divided by total transaction amount.
- Estimated main-fund net inflow: Active buy amount minus active sell amount. This is only an estimate because buy/sell direction depends on the upstream data source.
- Dense transaction price: The price level with the largest transaction amount.
- Minute-level volatility: The relative range between minute high and minute low.
- Anomaly alerts: Rule-based hints for sudden volume spikes, dense large-order activity, and rapid price movement.

## Machine Learning Examples

The ML module is located in `astock_analysis/ml/`. It is optional and does not affect the main application unless enabled in the Streamlit sidebar.

Minute-level features include:

- Price return
- Volume change rate
- Large-order amount ratio
- Active buy ratio
- Estimated main-fund net inflow
- VWAP deviation
- Minute-level volatility
- Distance from dense transaction price

Example:

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

## File Guide

- `app.py`: Unified Streamlit app with overview, large-order analysis, tick behavior signals, anomaly alerts, ML examples, and raw data views.
- `astock_analysis/data/fetchers.py`: AKShare interface wrappers and fetch error handling.
- `astock_analysis/data/cleaning.py`: Field compatibility, normalization, and stock-code formatting.
- `astock_analysis/indicators/intraday.py`: Core intraday indicators.
- `astock_analysis/indicators/tick_patterns.py`: Tick-level behavior signal detection and anomaly alerts.
- `astock_analysis/visualization/charts.py`: Plotly chart builders.
- `astock_analysis/ml/features.py`: Machine learning feature construction.
- `astock_analysis/ml/models.py`: Model training, prediction, clustering, and feature explanation examples.
- `config.yaml`: Default symbol, cache TTL, large-order thresholds, and alert thresholds.

## Future Extensions

- Persist historical intraday data and support multi-day backtesting.
- Add multi-stock watchlists and sector-level comparison.
- Add order-book queue analysis and bid/ask change tracking.
- Improve behavior-signal validation rules to reduce false positives.
- Add local storage with SQLite, DuckDB, or PostgreSQL.
- Add ML dataset management, label generation, model persistence, and offline evaluation.
- Add unit tests and regression tests for AKShare field-name changes.

## Risk Disclaimer

This project is not a trading system and does not provide investment advice. Tick direction, estimated main-fund flow, and behavior labels are derived from upstream data fields and rule-based estimates. They may be delayed, incomplete, inaccurate, or affected by data-interface changes. Any investment decision requires independent judgment and risk assessment.
