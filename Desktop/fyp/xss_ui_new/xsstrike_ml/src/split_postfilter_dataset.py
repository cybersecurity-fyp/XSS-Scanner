#splitting the balanced dataset into train and test sets, while keeping the balance of 0/1 labels in both sets. 

import pandas as pd
from sklearn.model_selection import train_test_split

# load balanced dataset
df = pd.read_csv("D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_dataset_balanced.csv")

print("Total dataset:", len(df))

# stratified split (keeps 0/1 balanced)
train, test = train_test_split(
    df,
    test_size=0.2,
    stratify=df['exec'],
    random_state=42
)

print("\nTrain size:", len(train))
print("Test size:", len(test))

print("\nTrain label balance:")
print(train['exec'].value_counts())

print("\nTest label balance:")
print(test['exec'].value_counts())

# save
train.to_csv(
    "D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_train.csv",
    index=False
)

test.to_csv(
    "D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_test.csv",
    index=False
)

print("\nSaved:")
print("postfilter_train.csv")
print("postfilter_test.csv")