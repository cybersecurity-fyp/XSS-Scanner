import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier 
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    classification_report,
    confusion_matrix,
    roc_auc_score
)
import joblib
import re
import os

# ========= Load CSV =========
csv_path = "D:\\XSStrike-master\\xsstrike-ml\\data\\xsstrike_prefilter_dataset_45k.csv"
df = pd.read_csv(csv_path)

# ========= Basic Cleaning =========
def clean(x):
    x = str(x).lower()
    x = re.sub(r'\s+', ' ', x)
    x = re.sub(r'[^\x20-\x7E]', '', x)
    return x.strip()

df['payload'] = df['payload'].apply(clean)

X = df['payload']
y = df['label']

# ========= Class Distribution =========
print("\n=== Dataset Class Distribution ===")
print(df['label'].value_counts())

# ========= TF-IDF (char analyzer) =========
tfidf = TfidfVectorizer(
    analyzer='char',
    ngram_range=(3, 6),
    min_df=3
)

X_vec = tfidf.fit_transform(X)

# ========= Train Test Split =========
X_train, X_test, y_train, y_test = train_test_split(
    X_vec, y, test_size=0.2, random_state=42
)

# ========= Base Model =========

base_rf = RandomForestClassifier(
    n_estimators=300,
    max_depth=None,
    n_jobs=-1,
    class_weight='balanced'
)
# ========= Probability Calibration =========
model = CalibratedClassifierCV(estimator=base_rf, cv=3, method='sigmoid')


# ========= Train =========
print("\n=== Training Model (Calibrated RF) ===")
model.fit(X_train, y_train)

# ========= Evaluation =========
y_pred = model.predict(X_test)
y_prob = model.predict_proba(X_test)[:, 1]   # malicious probability

print("\n=== Classification Report ===")
print(classification_report(y_test, y_pred))

print("\n=== Confusion Matrix ===")
print(confusion_matrix(y_test, y_pred))

# ========= ROC-AUC =========
auc = roc_auc_score(y_test, y_prob)
print(f"\n=== ROC-AUC: {auc:.4f} ===")

# ========= Save Artefacts =========
models_path = "D:\\XSStrike-master\\xsstrike-ml\\models"
os.makedirs(models_path, exist_ok=True)

joblib.dump(tfidf, os.path.join(models_path, "tfidf_vectorizer.pkl"))
joblib.dump(model, os.path.join(models_path, "random_forest_model.pkl"))

print("\nSaved calibrated RF + TF-IDF to /models")
