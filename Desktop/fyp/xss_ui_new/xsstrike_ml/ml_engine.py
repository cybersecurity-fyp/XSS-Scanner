import os
import joblib
import re

_BASE = os.path.dirname(__file__)
vectorizer = joblib.load(os.path.join(_BASE, "models", "tfidf_lr.pkl"))
model      = joblib.load(os.path.join(_BASE, "models", "lr_model.pkl"))


# -----------------------
# Preprocessing
# -----------------------
def preprocess(payload):
    text = str(payload).lower()
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('\t', ' ')
    text = text.replace('\n', ' ')
    text = re.sub(r'[^\x20-\x7E]', '', text)
    return text.strip()


# -----------------------
# Prediction function
# -----------------------
def predict_payload(payload):
    processed = preprocess(payload)
    X = vectorizer.transform([processed])
    pred = model.predict(X)[0]
    return pred   # 1 = malicious, 0 = benign
