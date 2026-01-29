import joblib
import pandas as pd
import sys
from sklearn.feature_extraction.text import TfidfVectorizer
import re

# ----------------------------
# Preprocessing (same as before)
# ----------------------------
def preprocess_text(text):
    text = str(text).lower()
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('\t', ' ')
    text = text.replace('\n', ' ')
    text = re.sub(r'[^\x20-\x7E]', '', text)
    return text.strip()

# ----------------------------
# Load vectorizer + model
# ----------------------------
vectorizer = joblib.load(r"D:\XSStrike-master\xsstrike-ml\models\tfidf_vectorizer.pkl")
model = joblib.load(r"D:\XSStrike-master\xsstrike-ml\models\random_forest_model.pkl")
# You can also load logistic regression if needed

# ----------------------------
# Read input payload
# ----------------------------
if len(sys.argv) < 2:
    print("Usage: python predict.py \"<payload>\"")
    sys.exit()

payload = sys.argv[1]
processed = preprocess_text(payload)

# Extract features
X = vectorizer.transform([processed])

# Predict
pred = model.predict(X)[0]

# Output
label = "Malicious XSS" if pred == 1 else "Benign"
print(f"\nPayload: {payload}")
print(f"Prediction: {label}\n")
