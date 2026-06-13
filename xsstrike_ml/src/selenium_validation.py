# for ml evalutaion, useful to find false positives and false negatives.
import csv
from urllib.parse import quote

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TARGET_URL = "http://testphp.vulnweb.com/search.php"

INPUT_FILE = "xsstrike_payloads.csv"
OUTPUT_FILE = "validation_results.csv"

chrome_options = Options()
chrome_options.add_argument("--headless=new")

driver = webdriver.Chrome(options=chrome_options)

results = []

with open(INPUT_FILE, newline="", encoding="utf-8") as f:

    reader = csv.DictReader(f)

    for row in reader:

        payload = row["Payload"]
        parameter = row["Parameter"]

        url = (
            f"{TARGET_URL}?"
            f"{parameter}={quote(payload)}"
        )

        executed = 0

        try:

            driver.get(url)

            WebDriverWait(driver, 3).until(
                EC.alert_is_present()
            )

            alert = driver.switch_to.alert
            alert.accept()

            executed = 1

        except:
            pass

        results.append([
            payload,
            executed
        ])

        print(payload[:50], executed)

driver.quit()

with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:

    writer = csv.writer(f)

    writer.writerow([
        "Payload",
        "Executed"
    ])

    writer.writerows(results)