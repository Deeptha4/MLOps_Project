"""Song genre predictor: Streamlit UI; metrics are scraped from :8000/metrics (see serve.py)."""

import json
import time
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st
from prometheus_client import Counter, Histogram

BASE = Path(__file__).parent

st.set_page_config(page_title="Song Genre Predictor", page_icon="🎵", layout="wide")


@st.cache_resource
def init_metrics():
    # The HTTP endpoint on :8000 is started by serve.py; here we only define the metrics.
    return {
        "predictions": Counter("predictions_total", "Predictions made", ["label"]),
        "latency": Histogram(
            "prediction_latency_seconds",
            "Model inference latency",
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5),
        ),
        "confidence": Histogram(
            "prediction_confidence",
            "Probability of the predicted genre",
            buckets=(0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
        ),
        "batch_rows": Counter("batch_rows_total", "Rows scored through CSV upload"),
        "errors": Counter("app_errors_total", "Application errors", ["kind"]),
    }


@st.cache_resource
def load_artifacts():
    model = joblib.load(BASE / "model.joblib")
    info = json.loads((BASE / "metrics.json").read_text())
    sample = pd.read_csv(BASE / "sample_batch.csv")
    sample["label"] = sample["track_name"] + " | " + sample["track_artist"]
    return model, info, sample


M = init_metrics()
model, info, SAMPLE = load_artifacts()
FEATURES = info["features"]
STATS = info["feature_stats"]
CLASSES = info["classes"]
CUSTOM = "(custom values)"


def score(df: pd.DataFrame):
    """Predict for every row of df and record metrics."""
    start = time.perf_counter()
    proba = model.predict_proba(df[FEATURES])
    M["latency"].observe(time.perf_counter() - start)
    conf = proba.max(axis=1)
    labels = [CLASSES[i] for i in proba.argmax(axis=1)]
    for label, c in zip(labels, conf, strict=True):
        M["predictions"].labels(label=label).inc()
        M["confidence"].observe(float(c))
    return labels, conf, proba


def load_track():
    """Callback: copy a real track's audio features into the sliders."""
    pick = st.session_state.track_pick
    if pick == CUSTOM:
        return
    row = SAMPLE.loc[SAMPLE["label"] == pick].iloc[0]
    for f in FEATURES:
        s = STATS[f]
        st.session_state[f"s_{f}"] = float(min(max(row[f], s["min"]), s["max"]))


st.title("🎵 Song Genre Predictor")
st.caption(
    "Predicts a track's genre (edm, latin, pop, r&b, rap, rock) from Spotify audio features. "
    f"Model: **{info['model_name']}**"
)

tab_predict, tab_batch, tab_perf, tab_about = st.tabs(
    ["Predict", "Batch (CSV)", "Model performance", "About"]
)

with tab_predict:
    st.selectbox(
        "Start from a real track (held-out test set)",
        [CUSTOM, *SAMPLE["label"]],
        key="track_pick",
        on_change=load_track,
    )
    cols = st.columns(2)
    values = {}
    for i, f in enumerate(FEATURES):
        s = STATS[f]
        st.session_state.setdefault(f"s_{f}", float(s["default"]))
        with cols[i % 2]:
            values[f] = st.slider(
                f,
                float(s["min"]),
                float(s["max"]),
                step=(s["max"] - s["min"]) / 200,
                format="%.3f",
                key=f"s_{f}",
            )
    if st.button("Predict genre", type="primary"):
        labels, conf, proba = score(pd.DataFrame([values]))
        st.success(f"Predicted genre: **{labels[0]}**")
        pick = st.session_state.track_pick
        if pick != CUSTOM:
            actual = SAMPLE.loc[SAMPLE["label"] == pick, "actual_genre"].iloc[0]
            st.caption(f"Actual playlist genre of this track: **{actual}**")
        c1, c2 = st.columns(2)
        c1.metric("Confidence", f"{conf[0]:.1%}")
        c2.bar_chart(pd.Series(proba[0], index=CLASSES, name="probability"))

with tab_batch:
    st.subheader("Score many tracks at once")
    st.write("Upload a CSV containing these columns: " + ", ".join(f"`{f}`" for f in FEATURES))
    st.download_button(
        "Download sample CSV",
        (BASE / "sample_batch.csv").read_bytes(),
        "sample_batch.csv",
        "text/csv",
    )
    up = st.file_uploader("CSV file", type="csv")
    if up is not None:
        key = (up.name, up.size)
        if st.session_state.get("batch_key") != key:  # score each upload only once
            st.session_state.batch_key = key
            try:
                df = pd.read_csv(up)
                missing = [f for f in FEATURES if f not in df.columns]
                if missing:
                    raise ValueError(f"Missing columns: {', '.join(missing)}")
                labels, conf, _ = score(df)
                M["batch_rows"].inc(len(df))
                st.session_state.batch_out = df.assign(
                    predicted_genre=labels, confidence=conf.round(4)
                )
                st.session_state.batch_err = None
            except Exception as exc:
                M["errors"].labels(kind="bad_csv").inc()
                st.session_state.batch_out = None
                st.session_state.batch_err = str(exc)
        if st.session_state.batch_err:
            st.error(st.session_state.batch_err)
        else:
            out = st.session_state.batch_out
            st.dataframe(out, use_container_width=True)
            st.bar_chart(out["predicted_genre"].value_counts())
            st.download_button(
                "Download predictions", out.to_csv(index=False), "predictions.csv", "text/csv"
            )

with tab_perf:
    st.subheader(f"Selected model: {info['model_name']}")
    st.caption(
        f"Trained on {info['n_train']} tracks, evaluated on {info['n_test']} held-out tracks. "
        f"Random guessing would score about {1 / len(CLASSES):.0%} accuracy."
    )
    for col, (k, v) in zip(st.columns(5), info["test"].items(), strict=True):
        col.metric(k.replace("_", " ").title(), f"{v:.3f}")
    left, right = st.columns(2)
    left.markdown("**Model comparison: 5-fold CV macro-F1 (train set)**")
    left.dataframe(pd.DataFrame(info["cv"]).T.round(4))
    left.markdown("**F1 per genre (test set)**")
    left.bar_chart(pd.Series(info["per_class_f1"]))
    right.markdown("**Confusion matrix (test set)**")
    right.dataframe(
        pd.DataFrame(
            info["confusion_matrix"],
            index=[f"actual {c}" for c in CLASSES],
            columns=[f"pred {c}" for c in CLASSES],
        )
    )
    right.markdown("**Permutation feature importance**")
    right.bar_chart(pd.Series(info["importance"]).sort_values())

with tab_about:
    st.markdown(
        """
### Data
5,400 tracks (900 per genre) sampled from the public TidyTuesday *Spotify songs* dataset
(audio features from the Spotify API). Genres overlap musically (pop vs r&b, edm vs latin),
so about 50-55% accuracy on six classes is a realistic result.

### Pipeline behind this app
| Stage | Tool |
|---|---|
| Source control | Git + GitHub (pull-request workflow) |
| CI | GitHub Actions: ruff lint, pytest + coverage, `terraform validate` |
| Packaging | Docker (non-root, health-checked image) published to GHCR |
| Infrastructure | Terraform: Azure resource group + AKS cluster |
| Orchestration | Kubernetes: Deployment, LoadBalancer Service, HPA, probes |
| Observability | Prometheus (ServiceMonitor + alert rules) and Grafana dashboard |

### Custom metrics exposed on `:8000/metrics`
`predictions_total{label}`, `prediction_latency_seconds`, `prediction_confidence`,
`batch_rows_total`, `app_errors_total{kind}`
"""
    )
