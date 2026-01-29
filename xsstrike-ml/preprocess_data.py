import pandas as pd
import re

# Load cleaned dataset
df = pd.read_csv(r"D:\XSStrike-master\xsstrike-ml\data\clean_dataset.csv")

# Function to preprocess each payload
def preprocess_text(text):
    text = str(text).lower()                      # lowercase
    text = re.sub(r'\s+', ' ', text)              # remove excessive whitespace
    text = text.replace('\t', ' ')                # remove tabs
    text = text.replace('\n', ' ')                # remove newlines
    text = re.sub(r'[^\x20-\x7E]', '', text)      # remove non-printable chars
    return text.strip()

# Apply preprocessing
df['Processed'] = df['Sentence'].apply(preprocess_text)

# Save preprocessed data
df.to_csv(r"D:\XSStrike-master\xsstrike-ml\data\preprocessed_dataset.csv", index=False)

print("✔ Preprocessing complete!")
print(df[['Sentence', 'Processed']].head())
