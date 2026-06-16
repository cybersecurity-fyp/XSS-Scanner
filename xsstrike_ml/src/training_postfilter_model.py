# Train Post-Filter Model on merged dataset
import pandas as pd
import joblib

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report, accuracy_score
from sklearn.compose import ColumnTransformer


# -----------------------------
# Load datasets
# -----------------------------
train = pd.read_csv("D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_training_data.csv")
test  = pd.read_csv("D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_testing_data.csv")

print("Train size:", len(train))
print("Test size:", len(test))


# -----------------------------
# Features / labels
# -----------------------------
train["interaction"] = ("CONTEXT_" + train["context"] + " ") * 2 + train["payload"]
test["interaction"]  = ("CONTEXT_" + test["context"]  + " ") * 2 + test["payload"]

X_train = train[["payload", "context", "interaction"]]
y_train = train["exec"]

X_test = test[["payload", "context", "interaction"]]
y_test = test["exec"]


# -----------------------------
# Model pipeline (BOOSTED CONTEXT)
# -----------------------------
model = Pipeline([
    ("features", ColumnTransformer([
        
        ("payload_word",
         TfidfVectorizer(
            analyzer="word",
            token_pattern=r"[^\s]+",
            ngram_range=(1,2),
            lowercase=True
         ),
         "payload"
        ),

        ("payload_char",
         TfidfVectorizer(
            analyzer="char",
            ngram_range=(3,5),
            lowercase=True
         ),
         "payload"
        ),

        ("context",
         TfidfVectorizer(
            analyzer="word",
            ngram_range=(1,2),
            lowercase=True
         ),
         "context"
        ),

        # NEW: interaction feature (MOST IMPORTANT)
        ("interaction",
         TfidfVectorizer(
            analyzer="word",
            token_pattern=r"[^\s]+",
            ngram_range=(1,2),
            lowercase=True
         ),
         "interaction"
        )

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