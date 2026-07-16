import csv
import os
import re
import time
from datetime import datetime

import yaml
from bs4 import BeautifulSoup, Comment
from curl_cffi import requests
from urllib.parse import urlencode

from lookup import (
    FUEL, AGE, SUB_DESIGN, TRANSMISSION, SUB_LOCATION, SELLER,
    EQ_DEFAULTS, STATIC_PARAMS, RANGE_DEFAULTS, SORT_BY, SORT_DIR,
)

BASE_URL    = "https://www.avto.net/Ads/results.asp"
DETAILS_URL = "https://www.avto.net/Ads/details.asp"
END_MARKER  = "Na tej strani so že prikazani vsi zadetki iskanja"
MAX_RETRIES = 3
RESULT_CAP  = 990  # avto.net silently caps at ~1000

HEADERS = {
    "User-Agent":      "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept":          "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "sl-SI,sl;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer":         "https://www.avto.net/",
}

# Detail-page Slovenian label → output field name (from th/td table pairs)
DETAIL_LABELS = {
    "Starost:":                    "age_category",
    "Prva registracija:":          "first_registration",
    "Leto proizvodnje:":           "production_year",
    "Prevoženi km:":               "km_detail",
    "Tehnični pregled:":           "tech_inspection",
    "Motor:":                      "engine_detail",
    "Gorivo:":                     "fuel_detail",
    "Menjalnik:":                  "transmission_detail",
    "Oblika:":                     "body_shape",
    "Št.vrat:":                    "doors",
    "Barva:":                      "color",
    "Notranjost:":                 "interior",
    "VIN / številka šasije:":      "vin",
    "Kraj ogleda:":                "location",
    "Kombinirana vožnja:":         "consumption_combined",
    "Izvenmestna vožnja:":         "consumption_highway",
    "Mestna vožnja:":              "consumption_city",
    "Emisijski razred:":           "emission_class",
    "Emisija CO2:":                "co2_emissions",
    "Interna številka:":           "internal_number",
    "Status zaloge:":              "stock_status",
    "Naročnik objave oglasa:":     "seller_name",
    "Oglaševalec:":                "seller_name",
}

_session = None


def get_session():
    global _session
    if _session is None:
        _session = requests.Session(impersonate="chrome120")
        _session.headers.update(HEADERS)
        _session.get("https://www.avto.net/", timeout=15)
    return _session


def load_config(path="config.yaml"):
    with open(path) as f:
        return yaml.safe_load(f)


def build_url(cfg, page=1):
    params = {}

    params.update(STATIC_PARAMS)
    params.update(EQ_DEFAULTS)
    params.update(RANGE_DEFAULTS)

    params["znamka"] = cfg.get("brand") or ""
    params["model"]  = cfg.get("model") or ""

    range_map = {
        "price_min": "cenaMin",
        "price_max": "cenaMax",
        "year_min":  "letnikMin",
        "year_max":  "letnikMax",
        "km_max":    "kmMax",
        "kw_min":    "kwMin",
        "kw_max":    "kwMax",
        "ccm_min":   "ccmMin",
        "ccm_max":   "ccmMax",
    }
    for cfg_key, param_key in range_map.items():
        val = cfg.get(cfg_key)
        if val is not None:
            params[param_key] = val

    params["bencin"] = FUEL[cfg.get("fuel", "vse")]
    params["oblika"] = SUB_DESIGN[cfg.get("body_type") or "vse"]

    age_val = AGE[cfg.get("age", "vse")]
    if age_val != 0:
        params["subSTAR"] = age_val

    trans_val = TRANSMISSION[cfg.get("transmission", "vse")]
    if trans_val is not None:
        params["subTRANS"] = trans_val

    seller_val = SELLER[cfg.get("seller", "vse")]
    if seller_val is not None:
        params["subSELLER"] = seller_val

    loc_key = cfg.get("location", "vse")
    if loc_key == "slovenija":
        params["lokacija"] = 100
    elif loc_key == "vse":
        params["lokacija"] = 0
    else:
        params["lokacija"] = 0
        params["subLOCATION"] = SUB_LOCATION[loc_key]

    params["presort"] = SORT_BY["datum"]
    params["tipsort"] = SORT_DIR["desc"]
    params["stran"]   = page

    return BASE_URL + "?" + urlencode(params)


def fetch_page(url, delay=2):
    time.sleep(delay)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = get_session().get(url, timeout=15)
            resp.raise_for_status()
            resp.encoding = "windows-1250"
            return BeautifulSoup(resp.text, "html.parser")
        except Exception as exc:
            if attempt == MAX_RETRIES:
                raise
            wait = delay * attempt
            print(f"  ! Attempt {attempt}/{MAX_RETRIES} failed: {exc} — retrying in {wait}s")
            time.sleep(wait)


def _parse_price(text):
    """'12.500 €' or '12500€' → 12500 (int), None on failure."""
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text.split("€")[0])
    return int(digits) if digits else None


def _parse_km(text):
    """'123.456 km' → 123456 (int), None on failure."""
    if not text:
        return None
    digits = re.sub(r"[^\d]", "", text.split("km")[0])
    return int(digits) if digits else None


def parse_listing(card):
    result = {}

    link = card.select_one("a.stretched-link")
    if link:
        m = re.search(r"id=(\d+)", link["href"])
        result["id"]  = m.group(1) if m else None
        result["url"] = f"{DETAILS_URL}?id={result['id']}" if result["id"] else None

    title_el = card.select_one("div.GO-Results-Naziv span")
    result["title"] = title_el.get_text(strip=True) if title_el else None

    data = {}
    table = card.select_one("table.table")
    if table:
        for row in table.select("tr"):
            tds = row.select("td")
            if len(tds) >= 2:
                data[tds[0].get_text(strip=True)] = tds[1].get_text(strip=True)

    result["year"]         = data.get("1.registracija")
    result["km"]           = _parse_km(data.get("Prevoženih"))
    result["fuel"]         = data.get("Gorivo")
    result["transmission"] = data.get("Menjalnik")
    result["engine"]       = data.get("Motor")

    sale_el    = card.select_one("div.GO-Results-Price-TXT-AkcijaCena")
    regular_el = card.select_one("div.GO-Results-Price-TXT-Regular")
    price_el   = sale_el or regular_el
    result["price"]   = _parse_price(price_el.get_text(strip=True) if price_el else None)
    result["on_sale"] = sale_el is not None

    photo_el = card.select_one("div.GO-Results-Photo img")
    result["photo_url"] = photo_el["src"] if photo_el else None

    result["scraped_at"] = datetime.now().isoformat(timespec="seconds")

    return result


def parse_detail(soup):
    """Extract rich attributes from a listing detail page."""
    result = {}

    # Find the DATA section via HTML comment, fall back to scanning all th/td rows
    data_table = None
    for comment in soup.find_all(text=lambda t: isinstance(t, Comment) and "DATA" in t):
        data_table = comment.find_next("table")
        break

    rows = data_table.find_all("tr") if data_table else soup.find_all("tr")
    for row in rows:
        th = row.find("th")
        td = row.find("td")
        if not (th and td):
            continue
        label = th.get_text(strip=True)
        value = td.get_text(strip=True).replace("\xa0", " ")
        field = DETAIL_LABELS.get(label)
        if field:
            result[field] = value

    # Coerce production_year and doors to int
    for int_field in ("production_year", "doors"):
        raw = result.get(int_field)
        if raw:
            try:
                result[int_field] = int(re.search(r"\d+", str(raw)).group())
            except (AttributeError, ValueError):
                pass

    # High-res photo (id="BigPhoto")
    big_photo = soup.find(id="BigPhoto")
    if big_photo and big_photo.get("src"):
        result["photo_url_hd"] = big_photo["src"]

    return result


def parse_page(soup):
    return [parse_listing(card) for card in soup.select("div.GO-Results-Row")]


def is_last_page(soup):
    return END_MARKER in soup.get_text()


def scrape(cfg):
    all_listings = []
    max_pages     = cfg.get("max_pages", 40)
    delay         = cfg.get("delay_seconds", 2)
    fetch_details = cfg.get("fetch_details", False)

    for page in range(1, max_pages + 1):
        url  = build_url(cfg, page=page)
        print(f"Page {page}: {url}")
        soup = fetch_page(url, delay=delay)

        listings = parse_page(soup)
        all_listings.extend(listings)
        print(f"  → {len(listings)} listings (total: {len(all_listings)})")

        if is_last_page(soup) or len(listings) == 0:
            print("  → last page reached")
            break

    if len(all_listings) >= RESULT_CAP:
        print(
            f"\nWARNING: {len(all_listings)} listings collected — avto.net silently caps results "
            f"at ~1000. Narrow your filters (price range, year range, etc.) to avoid missing listings.\n"
        )

    if fetch_details:
        print(f"\nFetching detail pages for {len(all_listings)} listings...")
        for i, listing in enumerate(all_listings, 1):
            if not listing.get("url"):
                continue
            print(f"  [{i}/{len(all_listings)}] id={listing['id']}")
            try:
                detail_soup = fetch_page(listing["url"], delay=delay)
                listing.update(parse_detail(detail_soup))
            except Exception as exc:
                print(f"  ! Detail fetch failed for id={listing['id']}: {exc}")

    return all_listings


BASE_FIELDS = [
    "id", "title", "year", "km", "fuel", "transmission", "engine",
    "price", "on_sale", "url", "photo_url", "scraped_at",
]

DETAIL_FIELDS = [
    "age_category", "first_registration", "production_year", "tech_inspection",
    "engine_detail", "fuel_detail", "transmission_detail", "body_shape",
    "doors", "color", "interior", "vin", "location",
    "consumption_combined", "consumption_highway", "consumption_city",
    "emission_class", "co2_emissions", "internal_number", "stock_status",
    "seller_name", "photo_url_hd",
]


def save_csv(listings, output_dir, fetch_details=False):
    os.makedirs(output_dir, exist_ok=True)
    filename = datetime.now().strftime("%Y%m%d_%H%M%S") + ".csv"
    path = os.path.join(output_dir, filename)
    fields = BASE_FIELDS + (DETAIL_FIELDS if fetch_details else [])
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(listings)
    return path


if __name__ == "__main__":
    cfg     = load_config()
    results = scrape(cfg)
    path    = save_csv(results, cfg.get("output_dir", "data/"), cfg.get("fetch_details", False))
    print(f"\nDone. {len(results)} listings saved to {path}")
