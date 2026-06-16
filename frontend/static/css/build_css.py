import os

COMPONENTS_DIR = os.path.join(os.path.dirname(__file__), "components")
OUT_FILE = os.path.join(os.path.dirname(__file__), "style.css")

# Load core tokens and reset first
CORE_FILES = ["tokens.css", "reset_and_base.css"]

def build():
    if not os.path.exists(COMPONENTS_DIR):
        print("Components directory not found!")
        return
        
    all_files = sorted([f for f in os.listdir(COMPONENTS_DIR) if f.endswith(".css")])
    for c in CORE_FILES:
        if c in all_files:
            all_files.remove(c)
            
    build_order = CORE_FILES + all_files
    
    with open(OUT_FILE, 'w', encoding='utf-8') as out:
        for fname in build_order:
            path = os.path.join(COMPONENTS_DIR, fname)
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    out.write(f.read() + "\n\n")
                    
    print(f"✅ Successfully compiled {len(build_order)} CSS components into style.css")

if __name__ == "__main__":
    build()
