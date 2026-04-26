import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
import joblib

# Load preprocessed data
df = pd.read_csv(r"D:\XSStrike-master\xsstrike-ml\data\preprocessed_dataset.csv")

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
joblib.dump(vectorizer, r"D:\XSStrike-master\xsstrike-ml\models\tfidf_vectorizer.pkl")

print("✔ TF-IDF feature extraction completed!")
print("✔ TF-IDF shape:", X.shape)
print("✔ Vectorizer saved as tfidf_vectorizer.pkl")
