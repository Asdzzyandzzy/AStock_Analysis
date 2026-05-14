"""AKShare 数据获取封装。"""

from __future__ import annotations

import pandas as pd
import akshare as ak

from astock_analysis.data.cleaning import normalize_symbol, standardize_tick_data
from astock_analysis.utils.logging import get_logger

logger = get_logger(__name__)


class DataFetchError(RuntimeError):
    """数据获取失败。"""


def fetch_tick_tx(symbol: str) -> pd.DataFrame:
    """腾讯逐笔成交接口：ak.stock_zh_a_tick_tx_js。"""

    normalized = normalize_symbol(symbol, with_prefix=True)
    try:
        raw = ak.stock_zh_a_tick_tx_js(symbol=normalized)
    except Exception as exc:
        logger.exception("获取腾讯逐笔成交失败: %s", normalized)
        raise DataFetchError(f"获取 {normalized} 逐笔成交失败：{exc}") from exc
    return standardize_tick_data(raw, source="stock_zh_a_tick_tx_js")


def fetch_intraday_em(symbol: str) -> pd.DataFrame:
    """东方财富日内逐笔接口：ak.stock_intraday_em。"""

    normalized = normalize_symbol(symbol, with_prefix=False)
    try:
        raw = ak.stock_intraday_em(symbol=normalized)
    except Exception as exc:
        logger.exception("获取东财日内逐笔失败: %s", normalized)
        raise DataFetchError(f"获取 {normalized} 日内逐笔失败：{exc}") from exc
    return standardize_tick_data(raw, source="stock_intraday_em")
