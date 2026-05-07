import os
import joblib
import pandas as pd


# ==============================
# Resolve Project Root
# ==============================

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, ".."))

# ==============================
# Model Path
# ==============================

MODEL_PATH = os.path.join(
    PROJECT_ROOT,
    "xsstrike_ml",
    "models",
    "xss_postfilter_model.pkl"
)

if not os.path.exists(MODEL_PATH):
    raise FileNotFoundError(f"Model not found at: {MODEL_PATH}")

model = joblib.load(MODEL_PATH)

print("[ML] Postfilter model loaded")


# ==============================
# Predict Function
# ==============================
def evaluate_payload(payload, context, threshold=0.9):

    payload = str(payload)
    context = str(context)

    interaction = payload + " CONTEXT_" + context

    X = pd.DataFrame([{
        "payload": payload,
        "context": context,
        "interaction": interaction
    }])

    proba = model.predict_proba(X)[0][1]
    pred = 1 if proba >= threshold else 0

    return pred, proba
# ==============================
# Filter Payload List
# ==============================

def filter_payloads(payloads, context, threshold=0.9):

    filtered = []

    for payload in payloads:
        pred, prob = evaluate_payload(payload, context, threshold)

        if pred == 1:
            filtered.append((payload, prob))

    # sort by confidence
    filtered.sort(key=lambda x: x[1], reverse=True)

    return [p[0] for p in filtered]


# ==============================
# Debug Test
# ==============================

if __name__ == "__main__":

    test_payloads = [
        "<img src=x onerror=alert(1)>",
        "<script>alert(1)</script>",
        "javascript:alert(1)",
        "hello world"
    ]

    results = filter_payloads(test_payloads, "html_tag")

    print("\nFiltered payloads:")
    for r in results:
        print(r)