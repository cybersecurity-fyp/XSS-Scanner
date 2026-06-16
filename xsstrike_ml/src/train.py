import pandas as pd
import argparse
import re
import os
import joblib
import urllib.parse
import html

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import classification_report, confusion_matrix, roc_auc_score
from sklearn.model_selection import train_test_split

# ========= Args =========
parser = argparse.ArgumentParser()
parser.add_argument("--synthetic", required=True)
parser.add_argument("--real", required=True)
parser.add_argument("--model", choices=["lr", "rf"], required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--threshold", type=float, default=0.4)
parser.add_argument("--use_normalization", action="store_true")

args = parser.parse_args()

# ========= Preprocessing =========
def normalize_payload(x):
    for _ in range(2):
        x = urllib.parse.unquote(str(x))
    return html.unescape(x)

def clean(x):
    x = str(x).lower()
    return re.sub(r'\s+', ' ', x).strip()

def preprocess(x):
    if args.use_normalization:
        x = normalize_payload(x)
    return clean(x)

# ========= Load Data =========
df_syn = pd.read_csv(args.synthetic)
df_syn.columns = df_syn.columns.str.strip()

df_real = pd.read_csv(args.real)
df_real.columns = df_real.columns.str.strip()

# 🔥 FIX: handle different column names
if "Sentence" in df_real.columns:
    df_real = df_real.rename(columns={"Sentence": "payload"})
if "Label" in df_real.columns:
    df_real = df_real.rename(columns={"Label": "label"})

# 🔥 FIX: remove NaN + bad labels
df_syn = df_syn.dropna(subset=["payload", "label"])
df_real = df_real.dropna(subset=["payload", "label"])

df_syn["label"] = pd.to_numeric(df_syn["label"], errors="coerce")
df_real["label"] = pd.to_numeric(df_real["label"], errors="coerce")

df_syn = df_syn.dropna(subset=["label"])
df_real = df_real.dropna(subset=["label"])

df_syn["label"] = df_syn["label"].astype(int)
df_real["label"] = df_real["label"].astype(int)

# ========= Preprocess =========
df_syn["payload"] = df_syn["payload"].apply(preprocess)
df_syn = df_syn.drop_duplicates()

# Reduce synthetic dominance
df_syn = df_syn.sample(frac=0.6, random_state=42)

df_real["payload"] = df_real["payload"].apply(preprocess)
df_real = df_real.drop_duplicates()

# Remove leakage
df_real = df_real[~df_real["payload"].isin(df_syn["payload"])]

# Combine
df_all = pd.concat([df_syn, df_real], ignore_index=True)
df_all = df_all.dropna(subset=["payload", "label"])
df_all = df_all.sample(frac=1, random_state=42)

# 🔥 SAFETY: ensure both classes exist
if df_all["label"].nunique() < 2:
    raise ValueError("Dataset has only one class after cleaning.")

train_df, test_df = train_test_split(
    df_all, test_size=0.2, stratify=df_all["label"], random_state=42
)

# ========= Vectorizer =========
tfidf = TfidfVectorizer(
    analyzer="char",
    ngram_range=(3, 6),
    min_df=3
)

X_train = tfidf.fit_transform(train_df["payload"])
y_train = train_df["label"]

X_test = tfidf.transform(test_df["payload"])
y_test = test_df["label"]

# ========= Model =========
if args.model == "lr":
    base_model = LogisticRegression(max_iter=2000, class_weight="balanced")
else:
    base_model = RandomForestClassifier(n_estimators=300, class_weight="balanced")

# Calibration
model = CalibratedClassifierCV(base_model, cv=3, method="sigmoid")
model.fit(X_train, y_train)

# ========= Evaluation =========
y_prob = model.predict_proba(X_test)[:, 1]
y_pred = (y_prob >= args.threshold).astype(int)

print("\n=== Probability Distribution ===")
print(pd.Series(y_prob).describe())

print("\n=== Evaluation ===")
print(classification_report(y_test, y_pred))
print(confusion_matrix(y_test, y_pred))
print("ROC-AUC:", roc_auc_score(y_test, y_prob))

# ========= Save =========
os.makedirs(args.output, exist_ok=True)
joblib.dump(tfidf, os.path.join(args.output, f"tfidf_{args.model}.pkl"))
joblib.dump(model, os.path.join(args.output, f"{args.model}_model.pkl"))

print("\nModel saved.")