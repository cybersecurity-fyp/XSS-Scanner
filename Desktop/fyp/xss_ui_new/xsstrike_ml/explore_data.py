import os
import pandas as pd

_BASE = os.path.dirname(os.path.abspath(__file__))

df = pd.read_csv(os.path.join(_BASE, "data", "xsstrike_prefilter_dataset_45k.csv"))

print(df.columns)
print(df['Label'].value_counts())
print(df['Sentence'].sample(10).tolist())
