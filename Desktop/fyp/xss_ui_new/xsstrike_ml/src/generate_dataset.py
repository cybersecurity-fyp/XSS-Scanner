import csv
import random
import urllib.parse

OUT_FILE = "D:\\XSStrike-master\\xsstrike_ml\\data\\xsstrike_prefilter_dataset_generated.csv"

# =====================
# Seeds
# =====================

MALICIOUS = [
    "<script>alert(1)</script>",
    "<svg onload=alert(1)>",
    "<img src=x onerror=alert(1)>",
    "javascript:alert(1)",
    "<iframe srcdoc='<script>alert(1)</script>'>",
    "eval(atob('YWxlcnQoMSk='))",
]

BENIGN = [
    "<div>Hello</div>",
    "<span>test</span>",
    "<img src=cat.png>",
    "<script>console.log('hello')</script>",
    "<a href='javascript:void(0)'>link</a>",
    "<div onclick='trackClick()'>",
    "<script>var alert = 5;</script>",
    "<img src=x onerror='handleError()'>",
    "q=alert",
    "search=<script>",
]

GRAY = [
    "<script>alert</script>",
    "<img src=x onerror=alert>",
    "javascript:alert",
    "alert",
]

EVENTS = ["onload", "onclick", "onerror"]
TAGS = ["img", "svg", "div"]

# =====================
# Helpers
# =====================

def random_case(s):
    return "".join(c.upper() if random.random() > 0.5 else c.lower() for c in s)

def encode(s):
    return urllib.parse.quote(s)

def double_encode(s):
    return urllib.parse.quote(urllib.parse.quote(s))

def variants(payload):
    v = [payload, random_case(payload), encode(payload)]
    if random.random() < 0.5:
        v.append(double_encode(payload))
    return v

# =====================
# Generators
# =====================

def gen_malicious():
    return f"<{random.choice(TAGS)} {random.choice(EVENTS)}=alert(1)>"

def gen_benign():
    funcs = ["init()", "track()", "logEvent()"]
    return f"<{random.choice(TAGS)} {random.choice(EVENTS)}={random.choice(funcs)}>"

# =====================
# Build dataset
# =====================

rows = []

def add(payload, label):
    for v in variants(payload):
        rows.append((v, label))

# MALICIOUS
for p in MALICIOUS:
    add(p, 1)

for _ in range(4000):
    add(gen_malicious(), 1)

# BENIGN
for p in BENIGN:
    add(p, 0)

for _ in range(4000):
    add(gen_benign(), 0)

# GRAY (controlled noise)
for p in GRAY:
    add(p, random.choice([0, 1]))

# =====================
# Deduplicate + balance
# =====================

rows = list(set(rows))

mal = [r for r in rows if r[1] == 1]
ben = [r for r in rows if r[1] == 0]

size = min(len(mal), len(ben))

mal = random.sample(mal, size)
ben = random.sample(ben, size)

rows = mal + ben
random.shuffle(rows)

# =====================
# Save
# =====================

with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["payload", "label"])
    writer.writerows(rows)

print(f"[+] Final samples: {len(rows)}")