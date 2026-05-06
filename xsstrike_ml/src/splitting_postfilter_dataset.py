# splitting merged postfilter dataset
import pandas as pd
from sklearn.model_selection import train_test_split

df = pd.read_csv(
"D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_merged_dataset_clean.csv"
)

print("Total:", len(df))

# split by payload (prevents leakage)
payloads = df["payload"].unique()

train_payloads, test_payloads = train_test_split(
    payloads,
    test_size=0.2,
    random_state=42
)

train = df[df["payload"].isin(train_payloads)]
test  = df[df["payload"].isin(test_payloads)]

print("\nTrain size:", len(train))
print("Test size:", len(test))

print("\nTrain label:")
print(train["exec"].value_counts())

print("\nTest label:")
print(test["exec"].value_counts())

train.to_csv(
"D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_training_data.csv",
index=False
)

test.to_csv(
"D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_testing_data.csv",
index=False
)

print("\nSaved train/test")