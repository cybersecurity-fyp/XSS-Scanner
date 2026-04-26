import pandas as pd
import argparse
import re
import os
import joblib

from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score


# ========= Args =========
parser = argparse.ArgumentParser()
parser.add_argument("--data", required=True, help="Path to dataset CSV")
parser.add_argument("--model", choices=["lr", "rf"], required=True, help="Model type")
parser.add_argument("--output", required=True, help="Output model path")
args = parser.parse_args()


# ========= Load CSV =========
df = pd.read_csv(args.data)

# ========= Cleaning =========
def clean(x):
    x = str(x).lower()
    x = re.sub(r'\s+', ' ', x)
    x = re.sub(r'[^\x20-\x7E]', '', x)
    return x.strip()

df["payload"] = df["payload"].apply(clean)

X = df["payload"]
y = df["label"]

print("\n=== Dataset Class Distribution ===")
print(y.value_counts())

# ========= TF-IDF =========
tfidf = TfidfVectorizer(
    analyzer="char",
    ngram_range=(3, 6),
    min_df=3
)

X_vec = tfidf.fit_transform(X)

# ========= Split =========
X_train, X_test, y_train, y_test = train_test_split(
    X_vec, y, test_size=0.2, random_state=42, stratify=y
)

# ========= Model Selection =========
if args.model == "lr":
    base_model = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        n_jobs=-1
    )
    print("\n=== Training Logistic Regression ===")

else:
    base_model = RandomForestClassifier(
        n_estimators=300,
        n_jobs=-1,
        class_weight="balanced"
    )
    print("\n=== Training Random Forest ===")

model = CalibratedClassifierCV(base_model, cv=3, method="sigmoid")

# ========= Train =========
model.fit(X_train, y_train)

# ========= Evaluate =========
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]

print("\n=== Classification Report ===")
print(classification_report(y_test, y_pred))

print("\n=== Confusion Matrix ===")
print(confusion_matrix(y_test, y_pred))

auc = roc_auc_score(y_test, y_prob)
print(f"\n=== ROC-AUC: {auc:.4f} ===")

# ========= Save =========
models_dir = os.path.dirname(args.output)
os.makedirs(models_dir, exist_ok=True)

if args.model == "lr":
    tfidf_path = os.path.join(models_dir, "tfidf_lr.pkl")
    model_path = os.path.join(models_dir, "lr_model.pkl")
else:
    tfidf_path = os.path.join(models_dir, "tfidf_rf.pkl")
    model_path = os.path.join(models_dir, "rf_model.pkl")

joblib.dump(tfidf, tfidf_path)
joblib.dump(model, model_path)

print(f"\nSaved model to {model_path}")
print(f"Saved TF-IDF to {tfidf_path}")