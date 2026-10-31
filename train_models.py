"""
train_models.py — optional. Re-creates food_models.joblib in the exact format the original
case-study app.py expects (keys: scaler, kmeans, segment_names, clf, features, reco).

The dashboard itself does NOT need this file: it trains the same models at start-up
(deterministic, random_state = 42), so a scikit-learn version mismatch can never break a deployment.

Run:  python train_models.py
"""
from core import build_artifacts, export_models

A = build_artifacts()
print("Saved:", export_models(A))
print("Segments:", A["segment_names"])
