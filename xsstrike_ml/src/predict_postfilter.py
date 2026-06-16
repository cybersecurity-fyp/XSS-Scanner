import joblib
import pandas as pd

model = joblib.load(
    #"D:\\XSStrike-master\\xsstrike_ml\\models\\xss_postfilter_model.pkl"
    "D:\\XSStrike-master\\xsstrike_ml\\models\\postfilter_model.pkl"

)

tests = [

# html_tag
("<img src=x onerror=alert(1)>","html_tag"),
("<svg onload=alert(1)>","html_tag"),

# html_attribute
('" onmouseover=alert(1) x="',"html_attribute"),
('" autofocus onfocus=alert(1) x="',"html_attribute"),

# html_text
("<script>alert(1)</script>","html_text"),
("<img src=x onerror=alert(1)>","html_text"),

# script_block
('";alert(1);//',"script_block"),
("';confirm(1);//","script_block"),

# url_href
("javascript:alert(1)","url_href"),
("javascript:confirm(1)","url_href"),

# comment
# SAFE comment (should be LOW)
("<script>alert(1)</script>", "comment"),
("hello world", "comment"),

# EXEC comment breakout (should be HIGH)
("--><script>alert(1)</script>", "comment"),
("--><img src=x onerror=alert(1)>", "comment"),
# url_navigation
("javascript:alert(1)","url_navigation"),
("data:text/html,<script>alert(1)</script>","url_navigation"),

]

for payload, context in tests:
    combined = "CONTEXT_" + str(context) + " " + str(payload)

    data = [combined]

    proba = model.predict_proba(data)[0][1]
    pred = model.predict(data)[0]

    print("\nPayload:", payload)
    print("Context:", context)
    print("Prediction:", "EXEC" if pred == 1 else "SAFE")
    print("Confidence:", round(proba, 3))