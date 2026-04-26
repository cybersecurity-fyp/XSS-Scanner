import os
import pandas as pd
import re

_BASE = os.path.dirname(os.path.abspath(__file__))

df = pd.read_csv(os.path.join(_BASE, "data", "clean_dataset.csv"))

def preprocess_text(text):
    text = str(text).lower()
    text = re.sub(r'\s+', ' ', text)
    text = text.replace('\t', ' ')
    text = text.replace('\n', ' ')
    text = re.sub(r'[^\x20-\x7E]', '', text)
    return text.strip()

df['Processed'] = df['Sentence'].apply(preprocess_text)
df.to_csv(os.path.join(_BASE, "data", "preprocessed_dataset.csv"), index=False)

print("✔ Preprocessing complete!")
print(df[['Sentence', 'Processed']].head())
