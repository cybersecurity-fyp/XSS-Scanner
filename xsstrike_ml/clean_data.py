import pandas as pd

# Load raw dataset
df = pd.read_csv(r"D:\XSStrike-master\xsstrike-ml\data\XSS_dataset.csv")

# Remove unnecessary column
if "Unnamed: 0" in df.columns:
    df = df.drop(columns=["Unnamed: 0"])

# Ensure 'Sentence' is string type
df['Sentence'] = df['Sentence'].astype(str)

# Save cleaned dataset
df.to_csv(r"D:\XSStrike-master\xsstrike-ml\data\clean_dataset.csv", index=False)

print("✔ Cleaned dataset saved as clean_dataset.csv!")
print(df.head())
