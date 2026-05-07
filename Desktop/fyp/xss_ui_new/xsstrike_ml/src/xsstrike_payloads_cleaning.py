seen = set()

with open("D:\\XSStrike-master\\xsstrike_ml\\data\\xsstrike_payloads_for_postfilter.txt","r",encoding="utf-8") as f:
    for line in f:
        seen.add(line.strip())

with open("D:\\XSStrike-master\\xsstrike_ml\\data\\xsstrike_payloads_unique.txt","w",encoding="utf-8") as f:
    for p in seen:
        f.write(p+"\n")

print("Unique payloads:", len(seen))