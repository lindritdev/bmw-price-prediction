from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import csv
import time
import re

MAX_ENTRIES = 2500

# --- Utility Functions ---
def clean_kilometer(km_raw):
    return re.sub(r"\D", "", km_raw)


def clean_ps(ps_raw):
    match = re.search(r"(\d+)\s*PS", ps_raw)
    return match.group(1) if match else ""


def clean_price(price_raw):
    # z.B. "CHF 32'600.-" -> "32600.00"
    digits = re.sub(r"[^\d]", "", price_raw)
    return f"{digits}.00" if digits else ""


def map_getriebe(raw):
    mapping = {
        "Automat": "Automatikgetriebe",
        "Stufenlos": "Automatikgetriebe",
        "Halbautomatisches Getriebe": "Automatikgetriebe",
        "Schaltgetriebe manuell": "Schaltgetriebe"
    }
    return mapping.get(raw, raw)

# --- Scraper ---
def scrape_car_listings(base_url, output_file):
    all_rows = []
    page = 1

    while len(all_rows) < MAX_ENTRIES:
        options = Options()
        options.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        )
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)
        options.add_argument('--disable-blink-features=AutomationControlled')

        driver = webdriver.Chrome(options=options)
        wait = WebDriverWait(driver, 10)

        try:
            page_param = page - 1
            url = f"{base_url}?pagination%5Bpage%5D={page_param}"
            driver.get(url)

            # Accept cookie banner
            try:
                btn = wait.until(EC.element_to_be_clickable((By.ID, "onetrust-accept-btn-handler")))
                btn.click()
            except:
                pass

            # Trigger lazy-loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            articles = driver.find_elements(By.CSS_SELECTOR, "article.css-79elbk")
            if not articles:
                break

            for art in articles:
                # Scroll listing into view
                driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", art)
                time.sleep(0.5)

                # Brand & Model
                link = art.find_element(By.CSS_SELECTOR, "a[data-testid^='listing-card-']")
                aria = link.get_attribute("aria-label") or ""
                parts = aria.split()
                brand = parts[0] if parts else ""
                model = " ".join(parts[1:]) if len(parts) > 1 else ""

                # Price
                try:
                    price_raw = art.find_element(By.CSS_SELECTOR, "p.chakra-text.css-cxnd42").text
                except:
                    price_raw = ""
                price = clean_price(price_raw)

                # Details: Year/Status, km, PS, transmission
                wrappers = art.find_elements(By.CSS_SELECTOR, "div.css-70qvj9")
                jahr = wrappers[0].text if len(wrappers) > 0 else ""
                km_raw = wrappers[2].text if len(wrappers) > 2 else ""
                ps_raw = wrappers[3].text if len(wrappers) > 3 else ""
                getriebe_raw = wrappers[4].text if len(wrappers) > 4 else ""

                # Clean and map
                kilometer = clean_kilometer(km_raw)
                ps = clean_ps(ps_raw)
                getriebe = map_getriebe(getriebe_raw)

                all_rows.append([brand, model, price, jahr, kilometer, ps, getriebe])
                if len(all_rows) >= MAX_ENTRIES:
                    break

        finally:
            driver.quit()

        page += 1

    # Write CSV
    with open(output_file, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["Brand", "Model", "Preis", "Jahr", "Kilometer", "PS", "Getriebe"])
        writer.writerows(all_rows[:MAX_ENTRIES])

if __name__ == "__main__":
    base_url = "https://www.autoscout24.ch/de/s/mk-bmw"
    output = "car_listings.csv"
    scrape_car_listings(base_url, output)
    print(f"Ergebnisse in {output} (max {MAX_ENTRIES}) gespeichert.")