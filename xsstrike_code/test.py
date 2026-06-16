import sys
import os

sys.path.append(os.path.abspath(".."))

from xsstrike_ml.ml_prefilter import is_malicious

print(is_malicious("hello world"))
print(is_malicious("search=test"))
print(is_malicious("<b>hello</b>"))
print(is_malicious("onboarding process"))
print(is_malicious("<script>alert(1)</script>"))
print(is_malicious("onmouseover=alert(1)"))