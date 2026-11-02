import json
from pathlib import Path

import joblib
import pandas as pd

ROOT = Path(__file__).parent.parent


def test_metrics_quality(trained_artifacts):
    test = trained_artifacts["test"]
    # six balanced genres -> chance is ~17%; audio features alone should clearly beat that
    assert test["accuracy"] > 0.45
    assert test["f1_macro"] > 0.40
    assert test["roc_auc_ovr"] > 0.75


def test_metrics_file_schema():
    info = json.loads((ROOT / "metrics.json").read_text())
    for key in ("model_name", "classes", "features", "feature_stats", "cv", "test"):
        assert key in info
    assert len(info["features"]) == 10
    assert len(info["classes"]) == 6


def test_model_outputs_probabilities():
    model = joblib.load(ROOT / "model.joblib")
    sample = pd.read_csv(ROOT / "sample_batch.csv")
    proba = model.predict_proba(sample[model.feature_names_in_])
    assert proba.shape == (len(sample), 6)
    assert abs(proba.sum(axis=1) - 1).max() < 1e-6
