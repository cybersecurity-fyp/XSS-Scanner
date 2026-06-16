# Train Post-Filter Model
import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.metrics import classification_report, accuracy_score


# -----------------------------
# Load datasets
# -----------------------------
train = pd.read_csv("D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_train.csv")
test  = pd.read_csv("D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_test.csv")


print("Train size:", len(train))
print("Test size:", len(test))

# -----------------------------
# Features / labels
# -----------------------------
X_train = train["combined"]
y_train = train["exec"]

X_test = test["combined"]
y_test = test["exec"]

# -----------------------------
# Model pipeline (ONLY TFIDF now)
# -----------------------------

model = Pipeline([
    ("features", FeatureUnion([
        ("word", TfidfVectorizer(
            analyzer="word",
            token_pattern=r"[^\s]+",
            ngram_range=(1,2),
            lowercase=True
        )),
        ("char", TfidfVectorizer(
            analyzer="char",
            ngram_range=(3,5),
            lowercase=True
        ))
    ])),
    ("clf", LogisticRegression(
        max_iter=2000,
        C=2.0,
        class_weight="balanced"
    ))
])
# -----------------------------
# Train
# -----------------------------
print("\nTraining model...")
model.fit(X_train, y_train)

# -----------------------------
# Evaluate
# -----------------------------
print("\nEvaluating...")
pred = model.predict(X_test)

print("\nAccuracy:", accuracy_score(y_test, pred))
print("\nClassification Report:\n")
print(classification_report(y_test, pred))

# -----------------------------
# Save model
# -----------------------------
joblib.dump(
    model,
    "D:\\XSStrike-master\\xsstrike_ml\\models\\xss_postfilter_model.pkl"
)

print("\nModel saved: models/xss_postfilter_model.pkl")