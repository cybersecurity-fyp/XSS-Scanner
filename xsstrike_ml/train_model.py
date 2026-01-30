import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, accuracy_score

# Load dataset
df = pd.read_csv(r"D:\XSStrike-master\xsstrike-ml\data\preprocessed_dataset.csv")

# Fix missing values
df['Processed'] = df['Processed'].fillna('')
df = df[df['Processed'].str.strip() != '']

# Load the saved TF-IDF vectorizer
vectorizer = joblib.load(r"D:\XSStrike-master\xsstrike-ml\models\tfidf_vectorizer.pkl")

# Transform text into features
X = vectorizer.transform(df['Processed'])
y = df['Label']

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, shuffle=True
)

print("✔ Training and testing split completed!")

# -----------------------------------------
# MODEL 1: LOGISTIC REGRESSION
# -----------------------------------------
print("\n🔹 Training Logistic Regression...")
lr_model = LogisticRegression(max_iter=2000)
lr_model.fit(X_train, y_train)

lr_pred = lr_model.predict(X_test)
print("\n📌 Logistic Regression Results:")
print(classification_report(y_test, lr_pred))
print("Accuracy:", accuracy_score(y_test, lr_pred))

# Save LR model
joblib.dump(lr_model, r"D:\XSStrike-master\xsstrike-ml\models\logistic_regression_model.pkl")
print("✔ Logistic Regression model saved!")

# -----------------------------------------
# MODEL 2: RANDOM FOREST
# -----------------------------------------
print("\n🔹 Training Random Forest...")
rf_model = RandomForestClassifier(
    n_estimators=300,
    max_depth=None,
    random_state=42,
    n_jobs=-1
)
rf_model.fit(X_train, y_train)

rf_pred = rf_model.predict(X_test)
print("\n📌 Random Forest Results:")
print(classification_report(y_test, rf_pred))
print("Accuracy:", accuracy_score(y_test, rf_pred))

# Save RF model
joblib.dump(rf_model, r"D:\XSStrike-master\xsstrike-ml\models\random_forest_model.pkl")
print("✔ Random Forest model saved!")

print("\n🎉 DONE! Both models trained and saved.")
