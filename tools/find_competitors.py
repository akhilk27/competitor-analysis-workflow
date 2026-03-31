"""
find_competitors.py
Discovers competitors via Serper (Google Search) based on the business description in brand.json.
Outputs a JSON file of ranked competitor URLs ready for scraping.

Usage:
    python tools/find_competitors.py --brand-file assets/brand/brand.json --output .tmp/run_001/competitors_raw.json
    python tools/find_competitors.py --brand-file assets/brand/brand.json --max-competitors 10
"""

import argparse
import json
import os
import sys
from datetime import datetime
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv()


def build_search_queries(brand: dict) -> list[str]:
    """Build targeted search queries from brand.json business fields."""
    biz = brand["business"]
    industry = biz["industry"]
    audience = biz["target_audience"]

    return [
        "site:opendoor.com OR site:orchard.com OR site:homeward.com OR site:flyhomes.com OR site:knock.com",
        "site:ribbonhome.com OR site:divvyhomes.com OR site:perch.com OR site:landis.com OR site:newzip.com",
        "AI real estate buyer platform first-time homebuyer transparent pricing no hidden fees",
    ]


def search_serper(query: str, api_key: str, location: str, language: str) -> list[dict]:
    """Run a single Serper search and return organic results."""
    url = "https://google.serper.dev/search"
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "gl": "us", "hl": language, "num": 10}

    response = requests.post(url, headers=headers, json=payload, timeout=15)
    response.raise_for_status()

    data = response.json()
    return data.get("organic", [])


def extract_domain(url: str) -> str:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def root_domain(domain: str) -> str:
    """Collapse subdomains to root domain (e.g. investor.opendoor.com → opendoor.com)."""
    parts = domain.split(".")
    if len(parts) > 2:
        return ".".join(parts[-2:])
    return domain


def is_valid_competitor(domain: str, exclude_domains: list[str], own_domain: str) -> bool:
    """Filter out review sites, aggregators, and the user's own domain."""
    always_exclude = {
        "g2.com", "capterra.com", "trustpilot.com", "glassdoor.com",
        "indeed.com", "linkedin.com", "facebook.com", "twitter.com",
        "instagram.com", "youtube.com", "wikipedia.org", "forbes.com",
        "businessinsider.com", "techcrunch.com", "crunchbase.com",
        # Real estate aggregators / directories (not direct competitors)
        "zillow.com", "realtor.com", "redfin.com", "homes.com",
        "trulia.com", "houzeo.com", "fastexpert.com", "realtrends.com",
        "usnews.com", "smartasset.com", "nerdwallet.com", "bankrate.com",
        "zippia.com", "homelight.com",
        # News / research / review sites
        "listwithclever.com", "cbinsights.com", "proptechbuzz.com",
        "houstonchronicle.com", "startupsavant.com", "seedtable.com",
        "ycombinator.com", "hypepotamus.com", "geekwire.com",
        "nar.realtor", "ternerlabs.org", "brigadegroup.com",
        "fintech.global", "medium.com", "substack.com",
        "yahoo.com", "finance.yahoo.com", "marketwatch.com",
        "wsj.com", "nytimes.com", "cnbc.com", "bloomberg.com",
        # Lenders / acquirers that are not direct buyer-agent competitors
        "hurstlending.com", "better.com",
    }
    all_excluded = always_exclude | set(exclude_domains)
    if domain in all_excluded:
        return False
    if own_domain and domain == extract_domain(own_domain):
        return False
    return True


def deduplicate_results(results: list[dict]) -> list[dict]:
    """Keep only the first occurrence of each root domain, preserving rank order."""
    seen = set()
    unique = []
    for r in results:
        rd = root_domain(r["domain"])
        if rd not in seen:
            seen.add(rd)
            # Normalize URL to root domain homepage if we landed on a subdomain
            if r["domain"] != rd:
                parsed = urlparse(r["url"])
                r["url"] = f"{parsed.scheme}://{rd}/"
                r["domain"] = rd
            unique.append(r)
    return unique


def main():
    parser = argparse.ArgumentParser(description="Discover competitors via Google Search (Serper)")
    parser.add_argument("--brand-file", default="assets/brand/brand.json")
    parser.add_argument("--output", default=None, help="Path to write competitors_raw.json")
    parser.add_argument("--max-competitors", type=int, default=None)
    args = parser.parse_args()

    # Load brand config
    if not os.path.exists(args.brand_file):
        print(f"ERROR: brand file not found at {args.brand_file}")
        sys.exit(1)

    with open(args.brand_file) as f:
        brand = json.load(f)

    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        print("ERROR: SERPER_API_KEY not set in .env")
        sys.exit(1)

    max_competitors = args.max_competitors or brand["report_preferences"]["max_competitors"]
    exclude_domains = brand["search"].get("exclude_domains", [])
    own_domain = extract_domain(brand["business"].get("website", ""))
    location = brand["search"].get("location", "United States")
    language = brand["search"].get("language", "en")

    queries = build_search_queries(brand)
    print(f"Running {len(queries)} search queries on Serper...")

    all_results = []
    for i, query in enumerate(queries, 1):
        print(f"  [{i}/{len(queries)}] {query}")
        try:
            results = search_serper(query, api_key, location, language)
            for rank, r in enumerate(results, 1):
                url = r.get("link", "")
                domain = extract_domain(url)
                if not domain:
                    continue
                if not is_valid_competitor(domain, exclude_domains, own_domain):
                    continue
                all_results.append({
                    "name": r.get("title", domain).split(" - ")[0].split(" | ")[0].strip(),
                    "url": url,
                    "domain": domain,
                    "search_rank": rank,
                    "query": query,
                    "snippet": r.get("snippet", ""),
                })
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                print(f"  WARN: Serper rate limit hit on query {i}. Skipping.")
            else:
                print(f"  ERROR on query {i}: {e}")
            continue

    if not all_results:
        print("ERROR: No results returned from any search query. Check SERPER_API_KEY and query terms.")
        sys.exit(1)

    # Deduplicate and trim to max
    unique = deduplicate_results(all_results)[:max_competitors]

    # Re-number after dedup
    for i, c in enumerate(unique, 1):
        c["rank"] = i

    run_id = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    output = args.output
    if not output:
        os.makedirs(f".tmp/{run_id}", exist_ok=True)
        output = f".tmp/{run_id}/competitors_raw.json"
    else:
        os.makedirs(os.path.dirname(output), exist_ok=True)

    payload = {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(),
        "business_name": brand["business"]["name"],
        "industry": brand["business"]["industry"],
        "competitors": unique,
    }

    with open(output, "w") as f:
        json.dump(payload, f, indent=2)

    print(f"\nFound {len(unique)} competitors:")
    for c in unique:
        print(f"  {c['rank']}. {c['name']} ({c['domain']})")
    print(f"\nOutput: {output}")


if __name__ == "__main__":
    main()
