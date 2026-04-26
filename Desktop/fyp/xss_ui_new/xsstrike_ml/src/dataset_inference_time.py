import time
import pandas as pd
import joblib
import re

# ========= Cleaning =========
def clean(x):
    x = str(x).lower()
    x = re.sub(r'\s+', ' ', x)
    x = re.sub(r'[^\x20-\x7E]', '', x)
    return x.strip()

# ========= Load dataset =========
df = pd.read_csv("../data/xsstrike_prefilter_dataset_generated.csv")
df["payload"] = df["payload"].apply(clean)
payloads = df["payload"].tolist()

print(f"\nTotal payloads: {len(payloads)}")

# ========= Load LR =========
lr_model = joblib.load("../models/lr_model.pkl")
lr_tfidf = joblib.load("../models/tfidf_lr.pkl")

# ========= Load RF =========
rf_model = joblib.load("../models/rf_model.pkl")
rf_tfidf = joblib.load("../models/tfidf_rf.pkl")

# ========= LR Inference =========
start = time.perf_counter()
X_lr = lr_tfidf.transform(payloads)
_ = lr_model.predict_proba(X_lr)
lr_time = time.perf_counter() - start

# ========= RF Inference =========
start = time.perf_counter()
X_rf = rf_tfidf.transform(payloads)
_ = rf_model.predict_proba(X_rf)
rf_time = time.perf_counter() - start

# ========= Results =========
print("\n=== Dataset-wide Inference Time ===")
print(f"LR total time: {lr_time:.4f} sec")
print(f"RF total time: {rf_time:.4f} sec")

print("\nAverage per payload:")
print(f"LR: {lr_time / len(payloads) * 1000:.4f} ms")
print(f"RF: {rf_time / len(payloads) * 1000:.4f} ms")
