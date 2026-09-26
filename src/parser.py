import csv
import re
import time
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from .quality_check import validate_product

def retry_request(url, errors_logger, max_tries=3, base_delay=1, timeout=15):
    for attempt in range(1, max_tries + 1):
        try:
            response = requests.get(
                url,
                timeout=timeout,
                headers={"User-Agent": "Mozilla/5.0 (compatible; EducationalScraper/1.0)"}
            )
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            errors_logger.error(
                "Connection error | attempt=%s/%s | URL=%s | error=%s",
                attempt, max_tries, url, exc
            )
            if attempt == max_tries:
                return None
            time.sleep(base_delay * (2 ** (attempt - 1)))

def price_to_number(price_text):
    if not price_text:
        return None
    value = re.sub(r"[^0-9,\.]", "", price_text).replace(",", ".")
    try:
        number = float(value)
        return int(number) if number.is_integer() else number
    except ValueError:
        return None

def parse_page(html):
    soup = BeautifulSoup(html, "html.parser")
    result = []

    products = soup.find_all("li", class_=lambda x: x and "product" in x)
    for product in products:
        title = product.find(["h2", "h3"], class_=lambda x: x and "product" in " ".join(x if isinstance(x, list) else [x]))
        if title is None:
            title = product.find(["h2", "h3"])

        price = product.find(class_=lambda x: x and "price" in " ".join(x if isinstance(x, list) else [x]))

        name = title.get_text(" ", strip=True) if title else ""
        price_value = price_to_number(price.get_text(" ", strip=True) if price else None)

        description = ""
        description_node = product.find(class_=lambda x: x and ("excerpt" in " ".join(x if isinstance(x, list) else [x]) or "description" in " ".join(x if isinstance(x, list) else [x])))
        if description_node:
            description = description_node.get_text(" ", strip=True)

        result.append({
            "name": name,
            "price": price_value,
            "description": description,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    return result

def collect_products(config, errors_logger, quality_logger):
    all_products = []
    base_url = config["url"].rstrip("/")
    pages = config.get("pages", 1)

    for page in range(1, pages + 1):
        url = base_url if page == 1 else f"{base_url}/page/{page}/"
        response = retry_request(
            url,
            errors_logger,
            max_tries=config["retry"]["max_tries"],
            base_delay=config["retry"]["base_delay"],
            timeout=config["timeout"]
        )
        if response is None:
            continue

        for item in parse_page(response.text):
            if len(all_products) >= config["product_count"]:
                break
            if validate_product(item, quality_logger, "data/quarantine"):
                all_products.append(item)

    return all_products

def save_incremental(items, csv_path):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    existing_names = set()

    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                existing_names.add(row.get("name", "").strip())

    new_items = [item for item in items if item["name"].strip() not in existing_names]

    write_header = not csv_path.exists() or csv_path.stat().st_size == 0
    with csv_path.open("a", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["name", "price", "description", "timestamp"]
        )
        if write_header:
            writer.writeheader()
        writer.writerows(new_items)

    return len(new_items)
