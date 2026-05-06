import os
import joblib

BASE_DIR = os.path.dirname(__file__)
MODELS_DIR = os.path.join(BASE_DIR, "models")

# ===== Choose model here =====
MODEL_TYPE = "lr"   # change to "rf" if needed

if MODEL_TYPE == "lr":
    MODEL_PATH = os.path.join(MODELS_DIR, "lr_model.pkl")
    TFIDF_PATH = os.path.join(MODELS_DIR, "tfidf_lr.pkl")
else:
    MODEL_PATH = os.path.join(MODELS_DIR, "rf_model.pkl")
    TFIDF_PATH = os.path.join(MODELS_DIR, "tfidf_rf.pkl")

try:
    model = joblib.load(MODEL_PATH)
    vectorizer = joblib.load(TFIDF_PATH)
    print(f"[ML] Loaded {MODEL_TYPE.upper()} model for prefiltering")
except Exception as e:
    print(f"[ML] ERROR loading models: {e}")
    model = None
    vectorizer = None


def is_malicious(payload, threshold=0.95):
    if model is None or vectorizer is None:
        return True  # fail-open (do not break scanner)

    X = vectorizer.transform([payload])
    prob = model.predict_proba(X)[0][1]

    # DEBUG PRINT 
    #print(f"[PREFILTER] prob={prob:.2f} payload={payload[:60]}")
    print(payload, "=>", prob)

    return prob >= threshold
