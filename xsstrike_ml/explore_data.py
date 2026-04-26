import pandas as pd


df = pd.read_csv(r"D:\XSStrike-master\xsstrike-ml\data\xsstrike_prefilter_dataset_45k.csv")


print(df.columns)
print(df['Label'].value_counts())
print(df['Sentence'].sample(10).tolist())
