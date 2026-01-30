import csv
import random
import urllib.parse

OUT_FILE = "xsstrike_prefilter_dataset_generated.csv"

# =====================
# Base Payload Seeds
# =====================

MALICIOUS_BASE = [
    "<script>alert(1)</script>",
    "<svg onload=alert(1)>",
    "<img src=x onerror=alert(1)>",
    "javascript:alert(1)",
    "\"'><script>alert(1)</script>"
]

BENIGN_BASE = [
    "<div>Hello</div>",
    "<test x=y>",
    "<span data-src='img'>",
    "<select name=artist>",
    "<img src=cat.png>",
    "<a href='index.html'>",
    "<test onload=x>",
    "<details x=y>",
    "<svg x=y>"
]

EVENTS = ["onload", "onclick", "onmouseover", "onfocus"]
TAGS = ["img", "svg", "div", "test", "a"]

# =====================
# Mutation Functions
# =====================

def random_case(s):
    return "".join(c.upper() if random.random() > 0.5 else c.lower() for c in s)

def url_encode(s):
    return urllib.parse.quote(s)

def hex_encode(s):
    return "".join(f"&#x{ord(c):x};" if c.isalnum() else c for c in s)

def unicode_mix(s):
    return s.replace("alert", "al\u0065rt")

def broken_tag(s):
    return s.replace("<", "<<").replace(">", ">>")

def event_injection():
    tag = random.choice(TAGS)
    ev = random_case(random.choice(EVENTS))
    return f"<{tag} {ev}=alert(1)>"

def benign_noise():
    tag = random.choice(TAGS)
    return f"<{tag} attr=value>"

# =====================
# Dataset Generation
# =====================

rows = []

# --- Malicious ---
for p in MALICIOUS_BASE:
    rows.append((p, 1))
    rows.append((random_case(p), 1))
    rows.append((url_encode(p), 1))
    rows.append((hex_encode(p), 1))
    rows.append((unicode_mix(p), 1))
    rows.append((broken_tag(p), 1))

for _ in range(5000):
    rows.append((event_injection(), 1))

# --- Benign ---
for p in BENIGN_BASE:
    rows.append((p, 0))
    rows.append((random_case(p), 0))
    rows.append((broken_tag(p), 0))

for _ in range(8000):
    rows.append((benign_noise(), 0))

random.shuffle(rows)

# =====================
# Write CSV
# =====================

with open(OUT_FILE, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["payload", "label"])
    writer.writerows(rows)

print(f"[+] Dataset generated: {OUT_FILE}")
print(f"[+] Total samples: {len(rows)}")
