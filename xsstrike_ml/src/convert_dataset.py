# to convert xsstrike payloads dataset from text file to csv file with columns: payload, context, exec.

import pandas as pd

INPUT = r"D:\XSStrike-master\xsstrike_ml\data\xsstrike_payloads_labeled.txt"
OUTPUT = r"D:\XSStrike-master\xsstrike_ml\data\xsstrike_payloads_dataset.csv"

rows = []

with open(INPUT, encoding="utf-8") as f:
    for line in f:
        parts = line.strip().split()

        if len(parts) != 3:
            continue

        payload, context, label = parts

        rows.append({
            "payload": payload,
            "context": context,
            "exec": int(label)
        })

df = pd.DataFrame(rows)

print("Dataset size:", len(df))
print(df["exec"].value_counts())
print(df["context"].value_counts())

df.to_csv(OUTPUT, index=False)

print("Saved:", OUTPUT)