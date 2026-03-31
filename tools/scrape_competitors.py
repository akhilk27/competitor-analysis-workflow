"""
scrape_competitors.py
Uses Firecrawl to scrape homepage, pricing, about, and features pages for each competitor.
Stores clean markdown content per competitor for downstream analysis.

Usage:
    python tools/scrape_competitors.py --input .tmp/run_001/competitors_raw.json
    python tools/scrape_competitors.py --input .tmp/run_001/competitors_raw.json --pages homepage,pricing
    python tools/scrape_competitors.py --input .tmp/run_001/competitors_raw.json --output .tmp/run_001/competitors_scraped.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse

import requests
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

FIRECRAWL_SCRAPE_URL = "https://api.firecrawl.dev/v1/scrape"

PAGE_PATH_CANDIDATES = {
    "pricing": ["/pricing", "/plans", "/pricing-plans", "/subscribe", "/packages"],
    "about": ["/about", "/about-us", "/our-story", "/company", "/who-we-are"],
    "features": ["/features", "/product", "/how-it-works", "/services", "/solutions"],
}


def scrape_url(url: str, api_key: str, retries: int = 2) -> tuple:
    """Scrape a URL with Firecrawl. Returns (markdown_content, error_message)."""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"url": url, "formats": ["markdown"], "onlyMainContent": True}

    for attempt in range(retries + 1):
        try:
            response = requests.post(FIRECRAWL_SCRAPE_URL, headers=headers, json=payload, timeout=30)
            if response.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"    Rate limited. Waiting {wait}s...")
                time.sleep(wait)
                continue
            response.raise_for_status()
            data = response.json()
            if data.get("success") and data.get("data", {}).get("markdown"):
                return data["data"]["markdown"], None
            return None, "Firecrawl returned no markdown content"
        except requests.exceptions.Timeout:
            return None, "Request timed out"
        except requests.exceptions.HTTPError as e:
            return None, f"HTTP {e.response.status_code}: {e.response.text[:200]}"
        except Exception as e:
            return None, str(e)

    return None, f"Failed after {retries + 1} attempts"


def find_page_url(base_url: str, page_type: str, api_key: str) -> tuple:
    """Try candidate paths for a page type; return the first that scrapes successfully."""
    candidates = PAGE_PATH_CANDIDATES.get(page_type, [])
    base = base_url.rstrip("/")

    for path in candidates:
        url = base + path
        content, error = scrape_url(url, api_key)
        if content and len(content.strip()) > 200:
            return content, url
        time.sleep(0.5)

    return None, None


def main():
    parser = argparse.ArgumentParser(description="Scrape competitor websites via Firecrawl")
    parser.add_argument("--input", required=True, help="Path to competitors_raw.json")
    parser.add_argument("--output", default=None, help="Path to write competitors_scraped.json")
    parser.add_argument(
        "--pages",
        default="homepage,pricing,about,features",
        help="Comma-separated page types to scrape",
    )
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)

    with open(args.input) as f:
        raw = json.load(f)

    api_key = os.getenv("FIRECRAWL_API_KEY")
    if not api_key:
        print("ERROR: FIRECRAWL_API_KEY not set in .env")
        sys.exit(1)

    page_types = [p.strip() for p in args.pages.split(",")]
    competitors = raw["competitors"]
    run_id = raw["run_id"]

    output = args.output
    if not output:
        run_dir = os.path.dirname(args.input)
        output = os.path.join(run_dir, "competitors_scraped.json")

    scraped_competitors = []
    total = len(competitors)

    for i, comp in enumerate(competitors, 1):
        name = comp["name"]
        url = comp["url"]
        print(f"\n[{i}/{total}] Scraping {name} ({url})")

        pages = {}
        errors = []

        for page_type in page_types:
            if page_type == "homepage":
                content, error = scrape_url(url, api_key)
                if content:
                    pages["homepage"] = content
                    print(f"  [OK]homepage ({len(content)} chars)")
                else:
                    errors.append(f"homepage: {error}")
                    print(f"  [--]homepage: {error}")
            else:
                content, found_url = find_page_url(url, page_type, api_key)
                if content:
                    pages[page_type] = content
                    print(f"  [OK]{page_type} ({len(content)} chars) at {found_url}")
                else:
                    errors.append(f"{page_type} page not found")
                    print(f"  [--]{page_type}: not found")

            time.sleep(1)  # Be polite between requests

        scraped_competitors.append({
            **comp,
            "pages": pages,
            "pages_found": list(pages.keys()),
            "scrape_errors": errors,
            "scraped_at": datetime.now().isoformat(),
        })

    # Summary
    fully_scraped = sum(1 for c in scraped_competitors if not c["scrape_errors"])
    partially_scraped = sum(1 for c in scraped_competitors if c["scrape_errors"] and c["pages"])
    failed = sum(1 for c in scraped_competitors if not c["pages"])

    if failed == total:
        print("\nERROR: All competitors failed to scrape. Check FIRECRAWL_API_KEY and try again.")
        sys.exit(1)

    payload = {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(),
        "business_name": raw["business_name"],
        "scrape_summary": {
            "total": total,
            "fully_scraped": fully_scraped,
            "partially_scraped": partially_scraped,
            "failed": failed,
        },
        "competitors": scraped_competitors,
    }

    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\nScraping complete: {fully_scraped} full, {partially_scraped} partial, {failed} failed")
    print(f"Output: {output}")


if __name__ == "__main__":
    main()
