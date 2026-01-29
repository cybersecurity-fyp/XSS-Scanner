import os
import joblib
import re
import sys

# compute base paths relative to this file
_this_dir = os.path.dirname(os.path.abspath(__file__))
# xsstrike-code directory is one level up from core
base_dir = os.path.abspath(os.path.join(_this_dir, ".."))
# model dir inside your ML project (xsstrike-ml)
models_dir = os.path.abspath(os.path.join(base_dir, "..", "xsstrike-ml", "models"))

# fallback: if that path doesn't exist, try sibling folder xsstrike-ml directly under parent
if not os.path.isdir(models_dir):
    models_dir = os.path.abspath(os.path.join(base_dir, "..", "xsstrike-ml", "models"))

# model file names (adjust if you used different names)
VECT_FILE = os.path.join(models_dir, "tfidf_vectorizer.pkl")
RF_MODEL_FILE = os.path.join(models_dir, "random_forest_model.pkl")
LR_MODEL_FILE = os.path.join(models_dir, "logistic_regression_model.pkl")

vectorizer = None
model = None

def safe_print(s):
    # use print for early debugging messages (console)
    try:
        print(s)
    except:
        pass

# load artifacts (prefer RF, fallback to LR)
try:
    if os.path.isfile(VECT_FILE):
        vectorizer = joblib.load(VECT_FILE)
    else:
        raise FileNotFoundError(f"Vectorizer not found at {VECT_FILE}")

    if os.path.isfile(RF_MODEL_FILE):
        model = joblib.load(RF_MODEL_FILE)
    elif os.path.isfile(LR_MODEL_FILE):
        model = joblib.load(LR_MODEL_FILE)
    else:
        raise FileNotFoundError("No classifier model found (RF or LR) in models directory")

    safe_print("[ML] Model & Vectorizer loaded from: " + models_dir)
except Exception as e:
    # If loading fails, set model to None; predict functions will fail-safe
    vectorizer = None
    model = None
    safe_print(f"[ML] ERROR loading models: {e}")

# Preprocessing used consistently
def _preprocess(text):
    text = str(text)
    # mimic same cleaning used in training
    text = text.lower()
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('\t', ' ')
    text = text.replace('\n', ' ')
    text = re.sub(r'[^\x20-\x7E]', '', text)
    return text.strip()

def predict_proba(payload):
    """
    Return probability score for 'malicious' (float 0..1).
    On error or missing model, return 1.0 (conservative: treat as malicious).
    """
    global vectorizer, model
    try:
        if vectorizer is None or model is None:
            return 1.0
        processed = _preprocess(payload)
        X = vectorizer.transform([processed])
        # many sklearn models implement predict_proba; RandomForest and LR do.
        probs = model.predict_proba(X)[0]
        # assume class 1 is malicious
        # find index of class 1 in model.classes_ (safe)
        if hasattr(model, "classes_"):
            classes = list(model.classes_)
            if 1 in classes:
                idx = classes.index(1)
            else:
                # fallback: choose last column
                idx = -1
        else:
            idx = -1
        return float(probs[idx])
    except Exception as e:
        # conservative: if anything goes wrong, return high malicious probability
        safe_print(f"[ML] predict_proba error: {e}", )
        return 1.0

def predict_label(payload, thresh=0.60):
    """
    Return 1 if malicious probability >= thresh else 0.
    Default thresh 0.60 (tunable).
    """
    prob = predict_proba(payload)
    return 1 if prob >= thresh else 0
