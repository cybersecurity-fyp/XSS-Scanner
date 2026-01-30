import time
import joblib

# ========= Load models =========
lr_model = joblib.load("../models/lr_model.pkl")
lr_tfidf = joblib.load("../models/tfidf_lr.pkl")

rf_model = joblib.load("../models/rf_model.pkl")
rf_tfidf = joblib.load("../models/tfidf_rf.pkl")

# ========= Sample payloads =========
payloads = [
    '<test attr=foo>',
    '<select name=artist>',
    '<div data-src="hello">',
    '<script>alert(1)</script>',
    '<img src=x onerror=alert(1)>'
] * 1000   # repeat to simulate load (5000 payloads)

# ========= Measure LR =========
start = time.perf_counter()
X_lr = lr_tfidf.transform(payloads)
_ = lr_model.predict_proba(X_lr)
lr_time = time.perf_counter() - start

# ========= Measure RF =========
start = time.perf_counter()
X_rf = rf_tfidf.transform(payloads)
_ = rf_model.predict_proba(X_rf)
rf_time = time.perf_counter() - start

print("\n=== Inference Time Results ===")
print(f"LR total time (5000 payloads): {lr_time:.4f} sec")
print(f"RF total time (5000 payloads): {rf_time:.4f} sec")

print("\nAverage per payload:")
print(f"LR: {lr_time / 5000 * 1000:.4f} ms")
print(f"RF: {rf_time / 5000 * 1000:.4f} ms")
