import pandas as pd

# load dataset
df = pd.read_csv("D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_executed_dataset_extended.csv")

# clean whitespace / tabs
df['payload'] = df['payload'].astype(str).str.strip()
df['context'] = df['context'].astype(str).str.strip()

print("Total rows:", len(df))

# -----------------------------
# Remove duplicates
# -----------------------------
df = df.drop_duplicates()
print("After removing duplicates:", len(df))

# -----------------------------
# Label balance
# -----------------------------
print("\nLabel balance:")
print(df['exec'].value_counts())

# -----------------------------
# Context balance
# -----------------------------
print("\nContext balance:")
print(df['context'].value_counts())

# -----------------------------
# Conflicting labels
# -----------------------------
print("\nChecking conflicts...")

conflicts = df.groupby(['payload','context'])['exec'].nunique()
conflicts = conflicts[conflicts > 1]

print("Conflicts found:", len(conflicts))

# -----------------------------
# Null values
# -----------------------------
print("\nNull values:")
print(df.isnull().sum())

# -----------------------------
# CLEANING STEP
# -----------------------------

# remove null rows
df = df.dropna()

# remove very rare context
df = df[df['context'] != 'svg_context']

# remove conflicting payload/context pairs
conflicts = df.groupby(['payload','context'])['exec'].nunique()
bad = conflicts[conflicts > 1].index
df = df[~df.set_index(['payload','context']).index.isin(bad)]

# convert labels to integer
df['exec'] = df['exec'].astype(int)

print("\nAfter cleaning:", len(df))

# -----------------------------
# NEW: COMBINED FEATURE
# -----------------------------

df["combined"] = "CONTEXT_" + df["context"] + " " + df["payload"]

# -----------------------------
# Final balance check
# -----------------------------
print("\nFinal Label balance:")
print(df['exec'].value_counts())

print("\nFinal Context balance:")
print(df['context'].value_counts())

# -----------------------------
# Save clean dataset
# -----------------------------
df.to_csv(
    "D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_dataset_clean.csv",
    index=False
)

print("\nClean dataset saved as postfilter_dataset_clean.csv")