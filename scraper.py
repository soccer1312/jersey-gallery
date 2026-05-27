import json
import logging
import os
import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

BASE_URL = "https://huahetian.x.yupoo.com"
OUTPUT_FILE = "jerseys.json"

# Start from page 44 so it rechecks page 44 and then continues
START_PAGE_OVERRIDE = 44


def create_session():
    session = requests.Session()

    retries = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=1.2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": f"{BASE_URL}/categories",
        "Connection": "keep-alive",
    })
    return session


def safe_get(session, url, timeout=25, sleep_before=0):
    if sleep_before:
        time.sleep(sleep_before)
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return response


def load_existing():
    if not os.path.exists(OUTPUT_FILE):
        return {}

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        jerseys = data.get("jerseys", [])
        return {item["url"]: item for item in jerseys if item.get("url")}
    except Exception as e:
        logger.warning("Could not load existing data: %s", e)
        return {}


def save_results(jerseys_by_url, total_pages):
    jerseys = list(jerseys_by_url.values())
    jerseys.sort(key=lambda x: (x.get("page", 9999), x.get("title", "")))

    payload = {
        "total": len(jerseys),
        "total_pages": total_pages,
        "jerseys": jerseys
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    logger.info("Saved %s jerseys to %s", len(jerseys), OUTPUT_FILE)


def bootstrap_session(session):
    for url in [BASE_URL, f"{BASE_URL}/categories"]:
        try:
            safe_get(session, url, sleep_before=0.5)
            logger.info("Bootstrapped %s", url)
        except Exception as e:
            logger.warning("Bootstrap failed for %s: %s", url, e)


def get_total_pages(session):
    try:
        resp = safe_get(session, f"{BASE_URL}/categories")
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        m = re.search(r"in\s+total\s+(\d+)\s+pages", text, re.IGNORECASE)
        if m:
            total_pages = int(m.group(1))
            logger.info("Detected total pages: %s", total_pages)
            return total_pages
    except Exception as e:
        logger.warning("Could not detect total pages automatically: %s", e)

    logger.warning("Falling back to 68 pages")
    return 68


def category_page_urls(page):
    if page == 1:
        return [
            f"{BASE_URL}/categories",
            f"{BASE_URL}/categories?page=1",
        ]
    return [
        f"{BASE_URL}/categories?page={page}",
    ]


def normalize_album_url(url):
    full = urljoin(BASE_URL, url)
    parsed = urlparse(full)

    if "/albums/" not in parsed.path:
        return None

    clean = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    if parsed.query:
        clean += f"?{parsed.query}"

    return clean


def extract_album_links_from_html(html):
    soup = BeautifulSoup(html, "html.parser")
    albums = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/albums/" not in href:
            continue

        album_url = normalize_album_url(href)
        if not album_url or album_url in seen:
            continue

        title = (
            a.get("title")
            or a.get_text(" ", strip=True)
            or ""
        ).strip()

        seen.add(album_url)
        albums.append((album_url, title))

    return albums


def fetch_album_links_for_page(session, page):
    for page_url in category_page_urls(page):
        try:
            logger.info("Trying page URL: %s", page_url)
            resp = safe_get(session, page_url, sleep_before=1)
            albums = extract_album_links_from_html(resp.text)
            if albums:
                logger.info("Found %s albums on page %s via %s", len(albums), page, page_url)
                return albums
            logger.warning("No albums found on %s", page_url)
        except Exception as e:
            logger.warning("Failed page URL %s: %s", page_url, e)

    return []


def extract_title(soup, fallback_title=""):
    candidates = []

    for selector in [
        ("div", "showalbumheader__gallerytitle"),
        ("div", "text_overflow_album_title"),
    ]:
        tag_name, class_name = selector
        node = soup.find(tag_name, class_=class_name)
        if node:
            text = node.get_text(" ", strip=True)
            if text:
                candidates.append(text)

    for tag in soup.find_all(["title", "h1", "h2"]):
        text = tag.get_text(" ", strip=True)
        if text:
            candidates.append(text)

    for elem in soup.find_all(attrs={"title": True}):
        val = elem.get("title", "").strip()
        if val:
            candidates.append(val)

    cleaned = []
    for c in candidates:
        c = re.sub(r"\s+\|\s+.*$", "", c).strip()
        c = re.sub(r"\s{2,}", " ", c)
        if c and c.lower() not in {"home", "album", "contact"}:
            cleaned.append(c)

    for c in cleaned:
        if "yupoo" not in c.lower():
            return c

    return cleaned[0] if cleaned else (fallback_title or "Untitled Jersey")


def maybe_product_image_url(value):
    if not value or not isinstance(value, str):
        return None

    value = value.strip()
    if not value:
        return None

    if value.startswith("//"):
        value = "https:" + value
    elif value.startswith("/"):
        value = urljoin(BASE_URL, value)

    if not value.startswith(("http://", "https://")):
        return None

    lower = value.lower()

    if "photo.yupoo.com" not in lower:
        return None

    if "/huahetian/" not in lower:
        return None

    blocked = [
        "logo",
        "icon",
        "loading",
        "police",
        "/square.",
        "avatar",
        "default",
        "banner",
        "background",
    ]
    if any(b in lower for b in blocked):
        return None

    if re.search(r"/huahetian/[a-f0-9]{8}/[a-f0-9]{8}\.(jpg|jpeg|png|webp)$", lower):
        return value

    allowed_markers = [
        "/small.", "/medium.", "/big.", "/original.",
        ".jpg", ".jpeg", ".png", ".webp"
    ]
    if not any(marker in lower for marker in allowed_markers):
        return None

    return value


def is_real_hashed_image(url):
    return bool(
        re.search(
            r"/huahetian/[a-f0-9]{8}/[a-f0-9]{8}\.(jpg|jpeg|png|webp)$",
            url.lower()
        )
    )


def image_group_key(url):
    m = re.search(r"/huahetian/([a-f0-9]{8})/([^/?]+)", url.lower())
    if not m:
        return url.lower()
    return m.group(1)


def image_sort_key(url):
    lower = url.lower()

    if is_real_hashed_image(lower):
        return (0, lower)
    if "/original." in lower:
        return (1, lower)
    if "/big." in lower:
        return (2, lower)
    if "/medium." in lower:
        return (3, lower)
    if "/small." in lower:
        return (4, lower)

    return (5, lower)


def upgrade_image_candidates(url):
    variants = [url]

    swaps = [
        ("/small.", "/original."),
        ("/small.", "/big."),
        ("/small.", "/medium."),
        ("/medium.", "/original."),
        ("/medium.", "/big."),
        ("/big.", "/original."),
    ]

    for old, new in swaps:
        if old in url:
            variants.append(url.replace(old, new))

    seen = set()
    out = []
    for v in variants:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def extract_real_hashed_urls_from_html(html):
    found = []

    patterns = [
        r'https?:\/\/photo\.yupoo\.com\/huahetian\/[a-f0-9]{8}\/[a-f0-9]{8}\.(?:jpg|jpeg|png|webp)',
        r'\/\/photo\.yupoo\.com\/huahetian\/[a-f0-9]{8}\/[a-f0-9]{8}\.(?:jpg|jpeg|png|webp)',
    ]

    for pattern in patterns:
        for match in re.findall(pattern, html, flags=re.I):
            u = maybe_product_image_url(match)
            if u:
                found.append(u)

    return found


def extract_variant_urls_from_dom(soup):
    found = []

    for img in soup.find_all("img"):
        for attr in ["src", "data-src", "data-original", "data-origin", "data-big", "data-path"]:
            raw = img.get(attr)
            if not raw:
                continue

            for part in str(raw).split("||"):
                u = maybe_product_image_url(part.strip())
                if u:
                    found.append(u)

    return found


def extract_images(session, html, soup):
    direct_real_urls = extract_real_hashed_urls_from_html(html)
    variant_urls = extract_variant_urls_from_dom(soup)

    all_candidates = []
    all_candidates.extend(direct_real_urls)
    all_candidates.extend(variant_urls)

    expanded = []
    for u in all_candidates:
        expanded.append(u)

        if not is_real_hashed_image(u):
            lower = u.lower()
            if any(x in lower for x in ["/small.", "/medium.", "/big.", "/original."]):
                expanded.extend(upgrade_image_candidates(u))

    cleaned = []
    seen = set()
    for u in expanded:
        clean = maybe_product_image_url(u)
        if clean and clean not in seen:
            seen.add(clean)
            cleaned.append(clean)

    best_by_group = {}
    for u in cleaned:
        key = image_group_key(u)
        current = best_by_group.get(key)
        if current is None or image_sort_key(u) < image_sort_key(current):
            best_by_group[key] = u

    # No HEAD validation anymore — trust the hashed image links
    final = []
    for _, u in sorted(best_by_group.items(), key=lambda kv: image_sort_key(kv[1])):
        final.append(u)

    return final


def extract_description(soup):
    parts = []

    for selector in [
        ("div", "showalbumheader__gallerytitle"),
        ("div", "showalbumheader__gallerydesc"),
        ("div", "album__desc"),
        ("div", "desc"),
        ("p", "desc"),
        ("span", "desc"),
    ]:
        tag_name, class_name = selector
        nodes = soup.find_all(tag_name, class_=class_name)
        for node in nodes:
            text = node.get_text(" ", strip=True)
            if text and text not in parts:
                parts.append(text)

    return " | ".join(parts)


def scrape_album(session, album_url, fallback_title="", page=None):
    logger.info("Scraping album: %s", album_url)

    resp = safe_get(session, album_url, sleep_before=0.7)
    html = resp.text
    soup = BeautifulSoup(html, "html.parser")

    title = extract_title(soup, fallback_title=fallback_title)
    images = extract_images(session, html, soup)
    description = extract_description(soup)

    return {
        "title": title,
        "url": album_url,
        "images": images,
        "thumbnail": images[0] if images else "",
        "description": description,
        "page": page,
    }


def scrape_all():
    session = create_session()
    bootstrap_session(session)

    existing = load_existing()
    total_pages = get_total_pages(session)

    start_page = START_PAGE_OVERRIDE if START_PAGE_OVERRIDE else 1

    logger.info("Starting scrape from page %s across %s total pages", start_page, total_pages)

    for page in range(start_page, total_pages + 1):
        logger.info("Processing page %s/%s", page, total_pages)

        albums = fetch_album_links_for_page(session, page)
        if not albums:
            logger.warning("No albums found on page %s", page)
            continue

        for idx, (album_url, fallback_title) in enumerate(albums, start=1):
            if album_url in existing and existing[album_url].get("images"):
                logger.info("Skipping existing album %s/%s: %s", idx, len(albums), album_url)
                continue

            try:
                item = scrape_album(session, album_url, fallback_title=fallback_title, page=page)

                if item["images"]:
                    existing[album_url] = item
                    logger.info(
                        "Saved album %s/%s on page %s: %s (%s images)",
                        idx, len(albums), page, item["title"], len(item["images"])
                    )
                else:
                    logger.warning("Album had no valid product images: %s", album_url)

            except Exception as e:
                logger.error("Failed album %s: %s", album_url, e)

            save_results(existing, total_pages)
            time.sleep(0.6)

        time.sleep(1.5)

    save_results(existing, total_pages)
    logger.info("Done. Total jerseys scraped: %s", len(existing))


if __name__ == "__main__":
    scrape_all()