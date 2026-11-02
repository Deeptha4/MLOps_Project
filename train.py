"""Train, compare and persist a song-genre classifier (Spotify audio features).

Data: data/spotify_tracks.csv, 5,400 tracks (900 per genre) sampled from the public
TidyTuesday "Spotify songs" dataset (Spotify API audio features, 6 playlist genres).

Outputs (next to this file):
    model.joblib      best model by 5-fold cross-validated macro-F1
    metrics.json      test metrics, CV comparison, confusion matrix, feature stats/importance
    sample_batch.csv  50 held-out tracks (with names) for the app's CSV upload
"""

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).parent
DATA = ROOT / "data" / "spotify_tracks.csv"
TARGET = "playlist_genre"
FEATURES = [
    "danceability",
    "energy",
    "loudness",
    "speechiness",
    "acousticness",
    "instrumentalness",
    "liveness",
    "valence",
    "tempo",
    "duration_ms",
]


def candidates():
    return {
        "logistic_regression": make_pipeline(
            StandardScaler(), LogisticRegression(max_iter=2000, random_state=42)
        ),
        "random_forest": RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1),
        "hist_gradient_boosting": HistGradientBoostingClassifier(random_state=42),
    }


def main(out_dir: Path = ROOT) -> dict:
    df = pd.read_csv(DATA)
    X, y = df[FEATURES], df[TARGET]

    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )

    cv = {}
    for name, est in candidates().items():
        scores = cross_val_score(est, X_tr, y_tr, cv=5, scoring="f1_macro")
        cv[name] = {"mean": float(scores.mean()), "std": float(scores.std())}
        print(f"{name:24s} CV macro-F1 = {scores.mean():.4f} +/- {scores.std():.4f}")

    best_name = max(cv, key=lambda n: cv[n]["mean"])
    model = candidates()[best_name].fit(X_tr, y_tr)
    classes = [str(c) for c in model.classes_]

    pred = model.predict(X_te)
    test = {
        "accuracy": accuracy_score(y_te, pred),
        "precision_macro": precision_score(y_te, pred, average="macro"),
        "recall_macro": recall_score(y_te, pred, average="macro"),
        "f1_macro": f1_score(y_te, pred, average="macro"),
        "roc_auc_ovr": roc_auc_score(y_te, model.predict_proba(X_te), multi_class="ovr"),
    }
    test = {k: float(v) for k, v in test.items()}
    per_class_f1 = dict(
        zip(classes, (float(v) for v in f1_score(y_te, pred, average=None, labels=classes)),
            strict=True)
    )

    imp = permutation_importance(model, X_te, y_te, n_repeats=5, random_state=42, n_jobs=-1)
    importance = {f: float(v) for f, v in zip(FEATURES, imp.importances_mean, strict=True)}

    info = {
        "model_name": best_name,
        "classes": classes,
        "features": FEATURES,
        # slider ranges use the 1st-99th percentile so outliers don't stretch the UI
        "feature_stats": {
            f: {
                "min": float(X_tr[f].quantile(0.01)),
                "max": float(X_tr[f].quantile(0.99)),
                "default": float(X_tr[f].median()),
            }
            for f in FEATURES
        },
        "n_train": len(X_tr),
        "n_test": len(X_te),
        "cv": cv,
        "test": test,
        "per_class_f1": per_class_f1,
        "confusion_matrix": confusion_matrix(y_te, pred, labels=classes).tolist(),
        "importance": importance,
    }

    joblib.dump(model, out_dir / "model.joblib")
    (out_dir / "metrics.json").write_text(json.dumps(info, indent=2))
    sample = df.loc[X_te.index[:50], ["track_name", "track_artist", TARGET, *FEATURES]]
    sample.rename(columns={TARGET: "actual_genre"}).to_csv(
        out_dir / "sample_batch.csv", index=False
    )

    print(f"\nBest model: {best_name}")
    print({k: round(v, 3) for k, v in test.items()})
    return info


if __name__ == "__main__":
    main()
