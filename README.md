# Competitor Intelligence Pipeline

Automated competitor research that discovers rivals via Google Search, scrapes their websites, synthesizes insights with Claude AI, and produces a branded PDF report — end-to-end with a single command sequence.

---

## What It Does

Given a business description and brand configuration, the pipeline:

1. **Discovers** up to 8 competitor websites using targeted Google searches (via Serper)
2. **Scrapes** homepage, pricing, about, and features pages from each competitor (via Firecrawl)
3. **Analyzes** all scraped content with Claude to produce structured per-competitor profiles, a market landscape summary, whitespace opportunities, and prioritized recommendations
4. **Generates** a branded, consulting-style PDF report with your brand colors and fonts

Every step writes an intermediate JSON file, making each step independently restartable. If Step 3 fails, re-run only Step 3 — no credits are burned re-fetching data you already have.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        INPUT                                    │
│              assets/brand/brand.json + logo.png                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 1 — find_competitors.py                                   │
│  Serper API (Google Search)                                     │
│  Builds targeted queries from brand.json → filters aggregators  │
│  → deduplicates by root domain → ranked competitor list         │
│                                                                 │
│  OUTPUT: .tmp/{run_id}/competitors_raw.json                     │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 2 — scrape_competitors.py                                 │
│  Firecrawl API                                                  │
│  Scrapes homepage + pricing + about + features per competitor   │
│  → clean markdown content → handles bot-blocking gracefully     │
│                                                                 │
│  OUTPUT: .tmp/{run_id}/competitors_scraped.json                 │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 3 — analyze_competitors.py                                │
│  Anthropic Claude API (claude-opus-4-6 by default)             │
│  Sends all scraped content in one prompt → structured JSON      │
│  per-competitor profiles + market summary + recommendations     │
│                                                                 │
│  OUTPUT: .tmp/{run_id}/analysis.json                            │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  STEP 4 — generate_report.py                                    │
│  Jinja2 + wkhtmltopdf (WeasyPrint on non-Windows)              │
│  Renders HTML template with brand tokens + analysis data        │
│  → branded PDF with cover, exec summary, profiles, recs         │
│                                                                 │
│  OUTPUT: .tmp/{run_id}/competitor_report.pdf                    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
.
├── assets/
│   ├── brand/
│   │   ├── brand.json              # Business info + brand colors/fonts (edit this first)
│   │   └── logo.png                # Brand logo — embedded as base64 in the PDF
│   └── templates/
│       └── report_template.html    # Jinja2 HTML template for the PDF report
│
├── tools/
│   ├── find_competitors.py         # Step 1: Google Search via Serper → competitors_raw.json
│   ├── scrape_competitors.py       # Step 2: Firecrawl → competitors_scraped.json
│   ├── analyze_competitors.py      # Step 3: Claude API → analysis.json
│   └── generate_report.py          # Step 4: Jinja2 + wkhtmltopdf → competitor_report.pdf
│
├── workflows/
│   └── competitor_analysis.md      # Full pipeline SOP with error handling + edge cases
│
├── .tmp/                           # Auto-created. Intermediate JSON files per run.
│   └── {run_id}/                   # One directory per pipeline run (timestamped)
│       ├── competitors_raw.json
│       ├── competitors_scraped.json
│       ├── analysis.json
│       └── competitor_report.pdf
│
├── .env                            # API keys (never committed — in .gitignore)
├── .gitignore
├── CLAUDE.md                       # Instructions for Claude Code agent (WAT framework)
└── README.md
```

---

## Prerequisites

### Python

Python **3.9 or higher** is required. The tools use `Optional[X]` typing syntax from `typing` (not the `X | Y` shorthand which requires 3.10+). [Anaconda](https://www.anaconda.com/download) is recommended on Windows.

```bash
python --version   # must be 3.9+
```

### API Keys

You need accounts and keys from three services:

| Key | Service | Where to get it | Free tier |
|-----|---------|----------------|-----------|
| `ANTHROPIC_API_KEY` | Claude AI (analysis) | [console.anthropic.com](https://console.anthropic.com) | Pay-per-token (no free tier — add credits) |
| `SERPER_API_KEY` | Serper (Google Search) | [serper.dev](https://serper.dev) | 2,500 free searches/month |
| `FIRECRAWL_API_KEY` | Firecrawl (web scraper) | [firecrawl.dev](https://firecrawl.dev) | 500 free scrapes/month |

A full pipeline run consumes roughly:
- **Serper:** 3 searches
- **Firecrawl:** ~24 scrape requests (8 competitors × 3 pages average)
- **Anthropic:** ~50,000–80,000 tokens with claude-opus-4-6 (~$1.50–$2.50 per run)

### PDF Generation (Windows)

WeasyPrint requires the GTK runtime, which is not available on Windows. Install **wkhtmltopdf** instead — `generate_report.py` automatically falls back to it:

1. Download the installer from [wkhtmltopdf.org/downloads.html](https://wkhtmltopdf.org/downloads.html)
2. Install to the default path (`C:\Program Files\wkhtmltopdf\`)
3. Add `C:\Program Files\wkhtmltopdf\bin` to your user PATH

---

## Setup

### 1. Clone and enter the project

```bash
git clone <your-repo-url>
cd "First Agentic Workflow"
```

### 2. Install Python dependencies

```bash
pip install anthropic requests python-dotenv jinja2 weasyprint
```

> On Windows, `weasyprint` will install but fail at runtime (GTK missing). That is expected — the fallback to wkhtmltopdf is automatic. Install it separately (see Prerequisites above).

### 3. Create your `.env` file

Create a file named `.env` in the project root:

```env
ANTHROPIC_API_KEY=sk-ant-...
SERPER_API_KEY=...
FIRECRAWL_API_KEY=fc-...
```

### 4. Configure your business in `brand.json`

Open `assets/brand/brand.json` and fill in your business details:

```json
{
  "business": {
    "name": "Your Company Name",
    "description": "One paragraph describing what you do, who you serve, and your key differentiators.",
    "industry": "your industry",
    "target_audience": "who you serve",
    "website": "https://yourwebsite.com",
    "founded_year": 2024
  },
  "brand": {
    "primary_color": "#1A3C5E",
    "secondary_color": "#2E7D9F",
    "accent_color": "#F4A827",
    "heading_font": "Georgia, serif",
    "body_font": "Arial, sans-serif"
  },
  "report_preferences": {
    "max_competitors": 8
  },
  "search": {
    "exclude_domains": ["reddit.com", "quora.com"]
  }
}
```

---

## Running the Pipeline

### Full Run (all four steps)

Run each step sequentially, using the same `{run_id}` folder throughout. The run ID is created by Step 1.

```bash
# Step 1 — Discover competitors
python tools/find_competitors.py \
  --brand-file assets/brand/brand.json \
  --output .tmp/my_run/competitors_raw.json

# Step 2 — Scrape competitor websites (takes 3–10 minutes)
python tools/scrape_competitors.py \
  --input .tmp/my_run/competitors_raw.json \
  --output .tmp/my_run/competitors_scraped.json

# Step 3 — Analyze with Claude
python tools/analyze_competitors.py \
  --input .tmp/my_run/competitors_scraped.json \
  --brand-file assets/brand/brand.json \
  --output .tmp/my_run/analysis.json

# Step 4 — Generate PDF (--open opens it automatically)
python tools/generate_report.py \
  --input .tmp/my_run/analysis.json \
  --brand-file assets/brand/brand.json \
  --open
```

Or let Step 1 auto-create a timestamped run directory (recommended):

```bash
python tools/find_competitors.py --brand-file assets/brand/brand.json
# Note the run_id printed at the end, e.g. 2026-03-31T14-22-10

python tools/scrape_competitors.py --input .tmp/2026-03-31T14-22-10/competitors_raw.json
python tools/analyze_competitors.py --input .tmp/2026-03-31T14-22-10/competitors_scraped.json --brand-file assets/brand/brand.json
python tools/generate_report.py --input .tmp/2026-03-31T14-22-10/analysis.json --open
```

### PDF Only (re-render without API calls)

If you already have `analysis.json` from a prior run and just want to tweak the template or branding:

```bash
python tools/generate_report.py \
  --input .tmp/2026-03-31T14-22-10/analysis.json \
  --open
```

This step has zero API cost. Iterate freely on the template.

### Custom Output Path

```bash
python tools/generate_report.py \
  --input .tmp/2026-03-31T14-22-10/analysis.json \
  --output reports/Q1-2026-competitor-report.pdf \
  --open
```

### Change the Claude Model

The default model is `claude-opus-4-6`. To use a faster/cheaper model:

```bash
python tools/analyze_competitors.py \
  --input .tmp/my_run/competitors_scraped.json \
  --brand-file assets/brand/brand.json \
  --model claude-sonnet-4-6
```

---

## Customization

### Brand Colors and Fonts

Edit `assets/brand/brand.json`. The following fields are injected directly into the report template as CSS values:

| Field | Effect |
|-------|--------|
| `primary_color` | Section headers, stat numbers, table header backgrounds |
| `secondary_color` | Secondary accent elements |
| `accent_color` | Cover stripe, section divider bar, recommendation badges |
| `heading_font` | All headings (`h1`–`h3`) — use any CSS font stack |
| `body_font` | Body text, metadata, table content |

After editing, re-run only Step 4 to see changes:

```bash
python tools/generate_report.py --input .tmp/{run_id}/analysis.json --open
```

### Report Title

The cover page title line is set in `brand.json`:

```json
"report_title_template": "Competitor Analysis Report &#8212; {month} {year}"
```

`{month}` and `{year}` are substituted at render time. Use `&#8212;` for an em dash — avoid raw Unicode characters, which wkhtmltopdf may misread on Windows.

### Report Layout

The entire PDF layout is in `assets/templates/report_template.html`. It is a Jinja2 template rendered with brand tokens and analysis data. Edit it freely — then re-run Step 4 to preview changes. No API calls are needed.

> **Note:** VS Code may show red squiggles in this file. These are false positives — the CSS validator does not understand Jinja2 `{{ variable }}` syntax and loses parse context. The generated HTML is valid. Suppress with `"css.validate": false` in `.vscode/settings.json`.

### Competitor Discovery Queries

`tools/find_competitors.py` contains a `build_search_queries()` function with hardcoded queries targeting known proptech domains. For a different industry, edit this function to reflect your competitive landscape — use `site:competitor.com` operators for precision, and add any aggregator/directory domains that appear in results to `brand.json → search.exclude_domains`.

---

## Troubleshooting

### WeasyPrint fails on Windows

```
cannot load library 'libgobject-2.0-0': error 0x7e
```

Expected. WeasyPrint requires the GTK runtime which is not available on Windows without WSL. The script automatically falls back to wkhtmltopdf. Install wkhtmltopdf (see Prerequisites) and ensure it is on your PATH.

### wkhtmltopdf not found

```
wkhtmltopdf not found in PATH
```

Add the wkhtmltopdf bin directory to your PATH. On Windows (PowerShell):

```powershell
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\Program Files\wkhtmltopdf\bin", "User")
```

Open a new terminal after running this. Verify with `wkhtmltopdf --version`.

### Garbled characters in PDF (e.g. `â€"` instead of `—`)

wkhtmltopdf has a known bug where it ignores `charset=UTF-8` declarations and decodes HTML bytes as Windows-1252. Raw Unicode characters in `brand.json` (em dashes, smart quotes, arrows) will appear garbled. Use HTML entities instead: `&#8212;` for —, `&#8594;` for →, `&#8217;` for '.

### Anthropic API: credit balance error

Step 3 will fail with a 400 error if your Anthropic account has no credits. Add credits at [console.anthropic.com](https://console.anthropic.com) — then re-run Step 3 only. Your `competitors_scraped.json` is preserved and does not need to be regenerated.

### Claude returns malformed JSON

Step 3 retries automatically up to 3 times with a 5-second delay. If it still fails after retries, try switching to a different model:

```bash
python tools/analyze_competitors.py --input ... --model claude-sonnet-4-6
```

### Context length error (too many competitors)

8 competitors × 4 pages × 3,000 chars = ~96K tokens, well within Claude's 200K context limit. If you increase `max_competitors` significantly (15+) and hit context errors, the script automatically switches to batch mode (4 competitors per call). You can also reduce `max_competitors` in `brand.json`.

### Serper returns zero results

The default queries in `find_competitors.py` use `site:` operators targeting known proptech companies. For other industries, edit `build_search_queries()` to use queries relevant to your competitive landscape.

### Python version errors (`X | Y` syntax)

This project targets **Python 3.9**. Do not use `X | Y` union type syntax (requires 3.10+). Use `Optional[X]` from the `typing` module instead. If you see `TypeError: unsupported operand type(s) for |`, check your Python version.

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Competitor discovery | [Serper](https://serper.dev) — Google Search API | Finds competitor URLs via targeted Google searches |
| Website scraping | [Firecrawl](https://firecrawl.dev) | Converts competitor websites to clean markdown |
| AI analysis | [Anthropic Claude](https://console.anthropic.com) (`claude-opus-4-6`) | Synthesizes scraped content into structured insights |
| Report rendering | [Jinja2](https://jinja.palletsprojects.com) | Injects brand tokens and analysis data into HTML template |
| PDF generation | [wkhtmltopdf](https://wkhtmltopdf.org) / [WeasyPrint](https://weasyprint.org) | Converts rendered HTML to PDF |
| Configuration | JSON (`brand.json`) | Stores business description, brand tokens, search settings |
| Secrets | `python-dotenv` (`.env` file) | Loads API keys without hardcoding them |

---

## License

MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
