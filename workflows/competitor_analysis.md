# Workflow: Competitor Analysis & Report Generation

## Objective
Run a full competitor research pipeline for NovaNest Realty — discover competitors via Google Search,
scrape their websites, analyze findings with Claude, and produce a branded PDF report.

## Required Inputs
| Input | Where to find it | Notes |
|-------|-----------------|-------|
| `assets/brand/brand.json` | Repo root | Must be populated before running |
| `assets/brand/logo.png` | Repo root | Optional — text fallback used if missing |
| `.env` keys: `ANTHROPIC_API_KEY`, `SERPER_API_KEY`, `FIRECRAWL_API_KEY` | `.env` file | All three must be set |

## Tools Used
| Tool | Purpose |
|------|---------|
| `tools/find_competitors.py` | Google Search via Serper → ranked competitor list |
| `tools/scrape_competitors.py` | Firecrawl → website content for each competitor |
| `tools/analyze_competitors.py` | Claude API → structured insights + recommendations |
| `tools/generate_report.py` | WeasyPrint → branded PDF |

## Pre-Flight Checks

Before running any tool, verify:

1. `assets/brand/brand.json` exists and the `business.description` field is filled in (not placeholder text).
2. `.env` contains non-empty values for `ANTHROPIC_API_KEY`, `SERPER_API_KEY`, and `FIRECRAWL_API_KEY`.
3. Python dependencies are installed. If not, run:
   ```
   pip install anthropic requests python-dotenv jinja2 weasyprint
   ```
   Note: WeasyPrint requires GTK on Windows. If `pip install weasyprint` fails, proceed — `generate_report.py`
   will automatically fall back to wkhtmltopdf or save an HTML file for browser-based printing.

## Steps

### Step 1 — Generate Run ID and Create Working Directory
Create a timestamped run directory to keep all intermediate files together:
```
RUN_ID = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
mkdir -p .tmp/{RUN_ID}
```
Use this RUN_ID consistently across all tool calls in this session.

### Step 2 — Discover Competitors
```
python tools/find_competitors.py \
  --brand-file assets/brand/brand.json \
  --output .tmp/{RUN_ID}/competitors_raw.json
```

**Expected output:** `.tmp/{RUN_ID}/competitors_raw.json` with up to 8 ranked competitor entries.

**If this fails:**
- `SERPER_API_KEY not set` → Add key to `.env`
- Zero results → The search queries may be too generic. Edit `tools/find_competitors.py` → `build_search_queries()` to add more specific query terms for real estate/proptech

**Review:** Print the competitor list and confirm it looks reasonable. If obvious non-competitors appear (news sites, Wikipedia), add their domains to `brand.json` → `search.exclude_domains`.

### Step 3 — Scrape Competitor Websites
```
python tools/scrape_competitors.py \
  --input .tmp/{RUN_ID}/competitors_raw.json \
  --output .tmp/{RUN_ID}/competitors_scraped.json
```

**Expected output:** `.tmp/{RUN_ID}/competitors_scraped.json` with scraped markdown content per competitor.

**This step takes the longest** — Firecrawl makes one request per page per competitor with polite delays.
Expect 3–10 minutes for 8 competitors at 4 pages each.

**If this fails:**
- `FIRECRAWL_API_KEY not set` → Add key to `.env`
- Most competitors show `scrape_errors` → Check Firecrawl dashboard for API status
- A few competitors fail → This is normal (bot detection). The analysis step handles missing data gracefully.

**Do not re-run Step 2** if Step 3 fails — reuse the existing `competitors_raw.json`.

### Step 4 — Analyze with Claude
```
python tools/analyze_competitors.py \
  --input .tmp/{RUN_ID}/competitors_scraped.json \
  --brand-file assets/brand/brand.json \
  --output .tmp/{RUN_ID}/analysis.json
```

**Expected output:** `.tmp/{RUN_ID}/analysis.json` with structured per-competitor profiles,
market summary, and ranked recommendations.

**If this fails:**
- `ANTHROPIC_API_KEY not set` → Add key to `.env`
- Rate limit error → The script retries automatically with backoff. Wait and re-run if it still fails.
- JSON parse error → The model returned malformed JSON. Re-run once; if it persists, check the model
  specified with `--model` (default: `claude-opus-4-6`)
- Context too large → Reduce `max_competitors` in `brand.json` or use `--model claude-sonnet-4-6`

**Do not re-run Steps 2 or 3** if Step 4 fails.

### Step 5 — Generate PDF Report
```
python tools/generate_report.py \
  --input .tmp/{RUN_ID}/analysis.json \
  --brand-file assets/brand/brand.json \
  --open
```

**Expected output:** `.tmp/{RUN_ID}/competitor_report.pdf` opened automatically.

**If WeasyPrint fails on Windows:**
- Install wkhtmltopdf from https://wkhtmltopdf.org/downloads.html (add to PATH)
- Or: the script saves `competitor_report.html` — open in Chrome, Print → Save as PDF

**If the PDF looks wrong:**
- Colors/fonts off → Update `assets/brand/brand.json` brand section
- Layout broken → Edit `assets/templates/report_template.html` and re-run Step 5 only
  (Step 5 is cheap to re-run — no API calls)

### Step 6 — Report Completion
After the PDF is confirmed, tell the user:
- Path to the PDF: `.tmp/{RUN_ID}/competitor_report.pdf`
- Key stats: X competitors analyzed, Y whitespace opportunities, Z high-priority recommendations
- Any competitors that failed to scrape (note in report)
- Suggest next step: update `brand.json` with business website, customize brand colors

## Expected Output
A PDF file at `.tmp/{RUN_ID}/competitor_report.pdf` containing:
- Cover page with NovaNest Realty logo and brand colors
- Executive summary with stats
- Market landscape / whitespace opportunities
- Per-competitor profile cards (positioning, pricing, strengths, weaknesses, features)
- Prioritized recommendations for NovaNest
- Methodology appendix

## Edge Cases & Error Handling

| Situation | Action |
|-----------|--------|
| Serper returns no results | Widen queries in `find_competitors.py → build_search_queries()` |
| Firecrawl blocked for all competitors | Check API key and Firecrawl dashboard; try running off-hours |
| Claude API unavailable | Wait and retry; intermediate JSON files preserve all prior work |
| Logo missing | Tool continues with text fallback; prompt user to add `assets/brand/logo.png` |
| WeasyPrint install fails on Windows | Use wkhtmltopdf fallback or browser print-to-PDF from saved HTML |
| PDF is blank or corrupt | Delete the PDF and re-run Step 5; check WeasyPrint error output |

## Notes
- **Each step is independently restartable.** If Step 4 fails, re-run only Step 4 — prior JSON files are reused.
- **Competitor data is cached in `.tmp/`.** Running the full pipeline again creates a new RUN_ID directory, preserving prior runs for comparison.
- **PDF generation has no API cost.** Iterate on the template freely without burning credits.
- **To customize brand appearance:** Edit `assets/brand/brand.json` (colors, fonts) and `assets/templates/report_template.html` (layout). Re-run Step 5 to see changes.
- **WeasyPrint on Windows:** Requires GTK runtime. If unavailable, `generate_report.py` auto-falls back to wkhtmltopdf or HTML output.
- **Python version:** Use Anaconda Python at `/c/Users/akhil/anaconda3/python.exe` — system `python` is not on PATH.
- **Type annotations:** Tools use Python 3.9 (Anaconda). Avoid `X | Y` union syntax (Python 3.10+); use `Optional[X]` from `typing` instead.
- **Windows console encoding:** Use ASCII `[OK]`/`[--]` instead of Unicode `✓`/`✗` in print statements.
- **Competitor search queries:** Generic industry queries return aggregators/directories. Use `site:` operator targeting known proptech company domains. See `find_competitors.py → build_search_queries()`. Add parked/acquired domains to `brand.json → search.exclude_domains`.
- **Known proptech competitors for NovaNest (real estate, first-time buyers):** opendoor.com, orchard.com, homeward.com, flyhomes.com, knock.com, ribbonhome.com, newzip.com, landis.com.
- **Firecrawl scrape success rate for this vertical:** 8/8 (100%) on first run — no bot-blocking issues observed with proptech sites.
- **Anthropic API billing:** Requires active credit balance at console.anthropic.com. If Step 4 fails with 400 credit error, add credits and re-run Step 4 only — scraped data is preserved in `.tmp/`.
- **Batch analysis threshold:** Set to 12 competitors. Up to 12 competitors run in a single Claude call (`max_tokens=8192`). Batch mode (>12) had silent empty-response failures — avoid unless necessary.
- **PDF on Windows:** WeasyPrint requires GTK (unavailable). wkhtmltopdf is installed at `C:\Program Files\wkhtmltopdf\bin\` and added to user PATH — `generate_report.py` uses it automatically as the fallback. Native PDF generation works without any browser step.
