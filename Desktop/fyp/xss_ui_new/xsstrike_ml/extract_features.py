import os
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib

_BASE = os.path.dirname(os.path.abspath(__file__))
df = pd.read_csv(os.path.join(_BASE, "data", "preprocessed_dataset.csv"))

# Fix missing values
df['Processed'] = df['Processed'].fillna('')
df = df[df['Processed'].str.strip() != '']   # remove empty payloads

# TF-IDF Vectorizer
vectorizer = TfidfVectorizer(
    analyzer='word',
    ngram_range=(1, 2),
    max_features=5000,
)

# Fit on processed payloads and transform
X = vectorizer.fit_transform(df['Processed'])
y = df['Label']

# Save vectorizer
joblib.dump(vectorizer, os.path.join(_BASE, "models", "tfidf_lr.pkl"))

print("✔ TF-IDF feature extraction completed!")
print("✔ TF-IDF shape:", X.shape)
print("✔ Vectorizer saved as tfidf_vectorizer.pkl")
