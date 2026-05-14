"""可选机器学习模型示例。"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from astock_analysis.ml.features import FEATURE_COLUMNS, make_direction_target


@dataclass
class MLResult:
    """模型输出容器。"""

    name: str
    output: pd.DataFrame
    description: str


def _load_sklearn():
    """延迟导入 sklearn，避免主程序因可选依赖缺失而失败。"""

    try:
        from sklearn.ensemble import IsolationForest, RandomForestClassifier
        from sklearn.cluster import KMeans
        from sklearn.linear_model import LogisticRegression
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
    except Exception as exc:
        raise ImportError("机器学习功能需要安装 scikit-learn：pip install scikit-learn") from exc
    return IsolationForest, RandomForestClassifier, KMeans, LogisticRegression, make_pipeline, StandardScaler


def detect_anomalies(features: pd.DataFrame) -> MLResult:
    """IsolationForest 异常成交检测。"""

    IsolationForest, _, _, _, _, _ = _load_sklearn()
    x = features[FEATURE_COLUMNS]
    model = IsolationForest(n_estimators=100, contamination="auto", random_state=42)
    score = model.fit_predict(x)
    out = features[["minute"]].copy()
    out["anomaly"] = score == -1
    out["score"] = model.decision_function(x)
    return MLResult("IsolationForest", out, "用于发现分钟级特征中偏离常态的成交片段。")


def train_direction_classifier(features: pd.DataFrame, model_type: str = "logistic") -> MLResult:
    """短期方向分类 LogisticRegression / RandomForest 示例。"""

    _, RandomForestClassifier, _, LogisticRegression, make_pipeline, StandardScaler = _load_sklearn()
    data = features.copy()
    data["target"] = make_direction_target(data)
    data = data.iloc[:-1].copy()
    if data.empty or data["target"].nunique() < 2:
        return MLResult("DirectionClassifier", pd.DataFrame(), "样本或标签不足，无法训练方向分类模型。")

    x = data[FEATURE_COLUMNS]
    y = data["target"]
    if model_type == "random_forest":
        model = RandomForestClassifier(n_estimators=100, max_depth=4, random_state=42)
    else:
        model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    model.fit(x, y)
    proba = model.predict_proba(x)[:, 1]
    out = data[["minute"]].copy()
    out["up_probability"] = proba
    out["target"] = y.values
    return MLResult(model_type, out, "示例模型：基于分钟级特征估计下一分钟上涨概率。")


def cluster_behaviour(features: pd.DataFrame, n_clusters: int = 3) -> MLResult:
    """KMeans 聚类识别成交行为。"""

    _, _, KMeans, _, make_pipeline, StandardScaler = _load_sklearn()
    if len(features) < n_clusters:
        return MLResult("KMeans", pd.DataFrame(), "样本数量不足，无法聚类。")
    model = make_pipeline(StandardScaler(), KMeans(n_clusters=n_clusters, n_init=10, random_state=42))
    labels = model.fit_predict(features[FEATURE_COLUMNS])
    out = features[["minute"]].copy()
    out["cluster"] = labels
    return MLResult("KMeans", out, "把分钟级成交行为聚为若干类，便于观察放量、强买盘、弱波动等片段。")


def feature_explanation(features: pd.DataFrame) -> pd.DataFrame:
    """简单特征解释：返回均值、标准差、最大最小。"""

    if features.empty:
        return pd.DataFrame()
    return features[FEATURE_COLUMNS].describe().T.rename(
        columns={"mean": "均值", "std": "标准差", "min": "最小值", "max": "最大值"}
    )[["均值", "标准差", "最小值", "最大值"]]
