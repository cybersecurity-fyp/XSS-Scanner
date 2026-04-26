import os
import pandas as pd
_BASE = os.path.dirname(os.path.abspath(__file__))

# Load raw dataset
df = pd.read_csv(os.path.join(_BASE, "data", "XSS_dataset.csv"))

# Remove unnecessary column
if "Unnamed: 0" in df.columns:
    df = df.drop(columns=["Unnamed: 0"])

# Ensure 'Sentence' is string type
df['Sentence'] = df['Sentence'].astype(str)

# Save cleaned dataset
df.to_csv(os.path.join(_BASE, "data", "clean_dataset.csv"), index=False)

print("✔ Cleaned dataset saved as clean_dataset.csv!")
print(df.head())
