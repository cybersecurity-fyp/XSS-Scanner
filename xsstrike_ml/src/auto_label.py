# This script automatically labels XSS payloads by injecting them into different contexts and checking for execution using Selenium.
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import time

INPUT_FILE = r"D:\XSStrike-master\xsstrike_ml\data\xsstrike_payloads_unique.txt"
OUTPUT_FILE = r"D:\XSStrike-master\xsstrike_ml\data\xsstrike_payloads_labeled.txt"

contexts = [
    "html_tag",
    "html_attribute",
    "html_text",
    "script_block",
    "comment",
    "url_href",
    "url_navigation"
]

chrome_options = Options()
chrome_options.add_argument("--disable-web-security")
chrome_options.add_argument("--allow-running-insecure-content")
chrome_options.add_argument("--disable-popup-blocking")
chrome_options.add_argument("--headless=new")

driver = webdriver.Chrome(options=chrome_options)


# ---------- context injection ----------
def build_html(payload, ctx):

    if ctx == "html_tag":
        return f"<html><body>{payload}</body></html>"

    elif ctx == "html_attribute":
        return f'<html><body><div test="{payload}">X</div></body></html>'

    elif ctx == "html_text":
        return f"<html><body>TEXT {payload}</body></html>"

    elif ctx == "script_block":
        return f"<html><body><script>{payload}</script></body></html>"

    elif ctx == "comment":
        return f"<html><body><!-- {payload} --></body></html>"

    elif ctx == "url_href":
        return f'<html><body><a href="{payload}">click</a></body></html>'

    elif ctx == "url_navigation":
        return f'<html><body><script>location="{payload}"</script></body></html>'


# ---------- execution checker ----------
def check_execution(html):

    driver.get("data:text/html;charset=utf-8," + html)

    time.sleep(0.4)

    # simulate interactions
    try:
        body = driver.find_element("tag name", "body")
        actions = ActionChains(driver)

        actions.move_to_element(body).perform()
        actions.move_by_offset(5, 5).perform()
        body.click()

    except:
        pass

    # trigger details
    try:
        details = driver.find_elements("tag name", "details")
        for d in details:
            d.click()
    except:
        pass

    # click some elements
    try:
        elems = driver.find_elements("css selector", "*")
        for e in elems[:5]:
            try:
                e.click()
            except:
                pass
    except:
        pass

    time.sleep(0.4)

    # detect alert/confirm/prompt
    try:
        alert = driver.switch_to.alert
        alert.accept()
        return 1
    except:
        return 0


# ---------- main loop ----------
with open(INPUT_FILE, "r", encoding="utf-8") as f, \
     open(OUTPUT_FILE, "w", encoding="utf-8") as out:

    for line in f:
        payload = line.strip()

        if not payload:
            continue

        for ctx in contexts:

            html = build_html(payload, ctx)

            label = check_execution(html)

            out.write(f"{payload}\t{ctx}\t{label}\n")

            print(payload, ctx, label)

driver.quit()