import pandas as pd

df1 = pd.read_csv(
    "D:\\XSStrike-master\\xsstrike_ml\\data\\postfilter_dataset_clean.csv"
)

df2 = pd.read_csv(
    "D:\\XSStrike-master\\xsstrike_ml\\data\\xsstrike_payloads_dataset.csv"
)

print("Dataset 1:", len(df1))
print("Dataset 2:", len(df2))

df = pd.concat([df1, df2], ignore_index=True)

print("Merged:", len(df))

df.to_csv(
    "D:\\XSStrike-master\\xsstrike_ml\\data\\merged_postfilter_dataset.csv",
    index=False
)

print("Saved: merged_postfilter_dataset.csv")