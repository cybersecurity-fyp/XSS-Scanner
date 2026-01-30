import pandas as pd
import joblib

# Load artifacts
# for logistic regression model
#tfidf = joblib.load("../models/tfidf_lr.pkl")
#model = joblib.load("../models/lr_model.pkl")
# for random forest model
tfidf = joblib.load("../models/tfidf_rf.pkl")
model = joblib.load("../models/rf_model.pkl")


# Load test data
df = pd.read_csv("../data/hard_negatives.csv")

X = tfidf.transform(df["payload"])
probs = model.predict_proba(X)[:, 1]
#print("\n lr model probs:")
print("\n rf model probs:")
print("\n=== Hard Negative Test ===")
for payload, p in zip(df["payload"], probs):
    print(f"{p:.3f}  ->  {payload}")
