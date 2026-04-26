from ml_prefilter import is_malicious

tests = [
    "<script>alert(1)</script>",      # malicious
    "<img src=x onerror=alert(1)>",   # malicious
    "<select name=artist>",           # benign
    "<div data-src='hello'>",         # benign
]

for t in tests:
    print(f"{t}  =>  {is_malicious(t)}")
