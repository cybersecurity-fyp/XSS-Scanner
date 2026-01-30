import joblib
import numpy as np
import pandas as pd
import re

from sklearn.metrics import confusion_matrix

# ========= Cleaning =========
def clean(x):
    x = str(x).lower()
    x = re.sub(r'\s+', ' ', x)
    x = re.sub(r'[^\x20-\x7E]', '', x)
    return x.strip()

# ========= Load dataset =========
df = pd.read_csv("../data/xsstrike_prefilter_dataset_generated.csv")
df["payload"] = df["payload"].apply(clean)

X_text = df["payload"]
y_true = df["label"]   # 1 = malicious, 0 = benign

# ========= Load models =========
models = {
    "LR": {
        "model": joblib.load("../models/lr_model.pkl"),
        "tfidf": joblib.load("../models/tfidf_lr.pkl")
    },
    "RF": {
        "model": joblib.load("../models/rf_model.pkl"),
        "tfidf": joblib.load("../models/tfidf_rf.pkl")
    }
}

thresholds = [0.1, 0.2, 0.3, 0.4, 0.5]

print("\n=== Threshold-Based Evaluation ===\n")

for name, obj in models.items():
    print(f"\n--- {name} MODEL ---")

    X_vec = obj["tfidf"].transform(X_text)
    probs = obj["model"].predict_proba(X_vec)[:, 1]

    for t in thresholds:
        y_pred = (probs >= t).astype(int)

        tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()

        print(
            f"Threshold={t:.1f} | "
            f"Skipped benign={tn} | "
            f"False skips (XSS missed!)={fn}"
        )
