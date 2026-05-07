#preprocessing of merged dataset
import pandas as pd

# load mreged dataset
df = pd.read_csv(
    "D:\\XSStrike-master\\xsstrike_ml\\data\\merged_postfilter_dataset.csv"
)

# drop old combined column if exists
if 'combined' in df.columns:
    df = df.drop(columns=['combined'])

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

# remove misleading contexts
df = df[df['context'] != 'svg_context']

# remove conflicting payload/context pairs
conflicts = df.groupby(['payload','context'])['exec'].nunique()
bad = conflicts[conflicts > 1].index
df = df[~df.set_index(['payload','context']).index.isin(bad)]

# convert labels to integer
df['exec'] = df['exec'].astype(int)

print("\nAfter cleaning:", len(df))

# -----------------------------
# PER-CONTEXT BALANCING
# -----------------------------
print("\nBalancing per context...")

balanced = []

for ctx in df['context'].unique():
    subset = df[df['context'] == ctx]

    df0 = subset[subset['exec'] == 0]
    df1 = subset[subset['exec'] == 1]

    if len(df0) == 0 or len(df1) == 0:
        continue

    n = min(len(df0), len(df1))

    df0 = df0.sample(n, random_state=42)
    df1 = df1.sample(n, random_state=42)

    balanced.append(pd.concat([df0, df1]))

df = pd.concat(balanced).reset_index(drop=True)

df = df.sample(frac=1, random_state=42).reset_index(drop=True)

print("\nAfter per-context balancing:")
print(df['exec'].value_counts())

print("\nContext balance:")
print(df['context'].value_counts())


# -----------------------------
# NEW: COMBINED FEATURE (context weighted)
# -----------------------------

df["combined"] = (
    "CTX_" + df["context"] + " " +
    "CTX_" + df["context"] + " " +
    "CTX_" + df["context"] + " " +
    df["payload"]
)

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
    "D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_merged_dataset_clean.csv",
    index=False
)

print("\nClean dataset saved as postfilter_merged_dataset_clean.csv")