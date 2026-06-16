# Balance Post-Filter Dataset
import pandas as pd

# load cleaned dataset
df = pd.read_csv("D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_dataset_clean.csv")

print("Before balancing:")
print(df['exec'].value_counts())
print("\nContext distribution:")
print(df['context'].value_counts())

# separate classes
df_0 = df[df['exec'] == 0]
df_1 = df[df['exec'] == 1]

# number of malicious samples
target = len(df_1)

print("\nTarget per class:", target)

# downsample benign class
df_0_balanced = df_0.sample(n=target, random_state=42)

# combine
df_balanced = pd.concat([df_0_balanced, df_1])

# shuffle
df_balanced = df_balanced.sample(frac=1, random_state=42).reset_index(drop=True)

print("\nAfter balancing:")
print(df_balanced['exec'].value_counts())

print("\nBalanced context distribution:")
print(df_balanced['context'].value_counts())

# save
df_balanced.to_csv(
    "D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_dataset_balanced.csv",
    index=False
)

print("\nBalanced dataset saved: postfilter_dataset_balanced.csv")