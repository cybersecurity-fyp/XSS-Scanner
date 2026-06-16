import os

css_path = "c:/Users/shery/Desktop/fyp/xss_ui_new/frontend/static/css/style.css"
out_dir = "c:/Users/shery/Desktop/fyp/xss_ui_new/frontend/static/css/components"
os.makedirs(out_dir, exist_ok=True)

with open(css_path, 'r', encoding='utf-8') as f:
    text = f.read()

parts = text.split("/* ═══════════════════════════════════════════════════════\n")

tokens_text = parts[0] + "/* ═══════════════════════════════════════════════════════\n" + parts[1]

file_map = {
    "tokens.css": tokens_text,
}

for part in parts[2:]:
    lines = part.split("\n")
    title = lines[0].strip().replace(" ", "_").replace("&", "and").replace("/", "").lower()
    if not title:
        continue
    filename = f"{title}.css"
    file_map[filename] = "/* ═══════════════════════════════════════════════════════\n" + part

for k, v in file_map.items():
    with open(os.path.join(out_dir, k), 'w', encoding='utf-8') as f:
        f.write(v.strip() + "\n")

print(f"Created {len(file_map)} files in components directory")
