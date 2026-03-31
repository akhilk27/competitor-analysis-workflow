# Competitor Intelligence Pipeline

An AI agentic workflow that researches your competitors end-to-end and delivers a branded PDF report — triggered by a single instruction to Claude.

---

## How It Works

Tell Claude:

> "Run the competitor analysis workflow"

Claude reads the workflow SOP, orchestrates four specialized tools in sequence, handles errors and retries automatically, and produces a branded PDF report. No manual commands. No copy-pasting outputs between steps.

This is built on the **WAT framework** — a pattern where AI handles orchestration and decision-making while deterministic Python scripts handle execution. The agent reads workflow instructions, calls the right tools in order, recovers from failures, and improves the system when it learns something new.

```
YOU                         AGENT (Claude)                    TOOLS
─────                       ──────────────                    ──────
"Run competitor              Reads workflow SOP          find_competitors.py
 analysis"          ──▶      Makes decisions         ──▶ scrape_competitors.py
                             Handles errors              analyze_competitors.py
                             Reports results             generate_report.py
```

---

## What the Agent Does

Given a business description and brand configuration, Claude autonomously:

1. **Discovers** competitors via targeted Google searches (Serper API)
2. **Scrapes** homepage, pricing, about, and features pages from each competitor (Firecrawl API)
3. **Analyzes** all content with Claude AI — per-competitor profiles, market gaps, whitespace opportunities, and prioritized recommendations
4. **Generates** a branded, consulting-style PDF report with your brand colors and fonts

Every step writes an intermediate JSON file. If any step fails, the agent re-runs only that step — no credits are burned re-fetching data already collected.

---

## WAT Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 1 — WORKFLOW  (workflows/competitor_analysis.md)         │
│  Plain-language SOP: objectives, inputs, tool sequence,         │
│  expected outputs, error handling, edge cases                   │
└─────────────────────────────┬───────────────────────────────────┘
                              │  Agent reads this
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 2 — AGENT  (Claude)                                      │
│  Reads the workflow, decides what to run, calls tools,          │
│  interprets results, retries on failure, reports back           │
└──────┬──────────────┬───────────────┬────────────────┬──────────┘
       │              │               │                │
       ▼              ▼               ▼                ▼
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────────┐
│  LAYER 3   │ │  LAYER 3   │ │  LAYER 3   │ │   LAYER 3      │
│   TOOL 1   │ │   TOOL 2   │ │   TOOL 3   │ │    TOOL 4      │
│            │ │            │ │            │ │                │
│  find_     │ │  scrape_   │ │  analyze_  │ │  generate_     │
│  competi-  │ │  competi-  │ │  competi-  │ │  report.py     │
│  tors.py   │ │  tors.py   │ │  tors.py   │ │                │
│            │ │            │ │            │ │                │
│  Serper    │ │  Firecrawl │ │  Claude    │ │  wkhtmltopdf   │
│  API       │ │  API       │ │  API       │ │  / WeasyPrint  │
└─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └──────┬─────────┘
      │              │               │                │
      ▼              ▼               ▼                ▼
competitors_    competitors_      analysis         competitor_
raw.json        scraped.json      .json            report.pdf
```

**Why this architecture?** When AI handles every step directly, accuracy compounds poorly — five steps at 90% accuracy each yields 59% end-to-end success. Offloading execution to deterministic scripts keeps the agent focused on orchestration, where it excels.

---

## Sample Output

The [`sample_output/`](sample_output/) folder contains a real pipeline run against 8 proptech competitors:

- [`competitors_raw.json`](sample_output/competitors_raw.json) — ranked competitor list from Step 1
- [`analysis.json`](sample_output/analysis.json) — Claude's structured analysis from Step 3
- [`competitor_report.pdf`](sample_output/competitor_report.pdf) — the final branded PDF

---

## Folder Structure

```
.
├── assets/
│   ├── brand/
│   │   ├── brand.json              # Business info + brand colors/fonts (configure this first)
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
│   └── competitor_analysis.md      # SOP the agent reads to orchestrate the pipeline
│
├── sample_output/                  # Real output from a full pipeline run
│   ├── competitors_raw.json
│   ├── analysis.json
│   └── competitor_report.pdf
│
├── .tmp/                           # Auto-created. Intermediate JSON files per run (gitignored).
├── .env                            # API keys (never committed)
├── CLAUDE.md                       # Agent instructions for Claude Code
└── README.md
```

---

## Prerequisites

### Python

Python **3.9 or higher**. [Anaconda](https://www.anaconda.com/download) is recommended on Windows.

### API Keys

Three services are required:

| Key | Service | Where to get it | Free tier |
|-----|---------|----------------|-----------|
| `ANTHROPIC_API_KEY` | Claude AI | [console.anthropic.com](https://console.anthropic.com) | Pay-per-token (add credits) |
| `SERPER_API_KEY` | Serper (Google Search) | [serper.dev](https://serper.dev) | 2,500 free searches/month |
| `FIRECRAWL_API_KEY` | Firecrawl (web scraper) | [firecrawl.dev](https://firecrawl.dev) | 500 free scrapes/month |

A full pipeline run uses approximately 3 Serper searches, 24 Firecrawl scrapes, and 50–80K Claude tokens ($1.50–$2.50).

### PDF Generation (Windows)

WeasyPrint requires GTK, which is unavailable on Windows. Install **wkhtmltopdf** — the pipeline falls back to it automatically:

1. Download from [wkhtmltopdf.org/downloads.html](https://wkhtmltopdf.org/downloads.html)
2. Add `C:\Program Files\wkhtmltopdf\bin` to your PATH

---

## Setup

### 1. Install dependencies

```bash
pip install anthropic requests python-dotenv jinja2 weasyprint
```

### 2. Add API keys to `.env`

```env
ANTHROPIC_API_KEY=sk-ant-...
SERPER_API_KEY=...
FIRECRAWL_API_KEY=fc-...
```

### 3. Configure your business in `brand.json`

Open `assets/brand/brand.json` and update the `business` section with your company details. The agent uses this description to build targeted competitor search queries and to frame the analysis.

```json
{
  "business": {
    "name": "Your Company Name",
    "description": "What you do, who you serve, and your key differentiators.",
    "industry": "your industry",
    "target_audience": "who you serve",
    "website": "https://yourwebsite.com"
  }
}
```

---

## Running the Workflow

### Via the Agent (primary)

Open Claude Code in this project directory and say:

```
Run the competitor analysis workflow
```

The agent handles everything from there — discovery, scraping, analysis, PDF generation, and a summary of results when complete.

To re-run only the PDF step (zero API cost, useful for template tweaks):

```
Regenerate the PDF using the existing analysis at .tmp/{run_id}/analysis.json
```

### Manually (fallback)

If you need to run steps directly without the agent:

```bash
# Step 1 — Discover competitors
python tools/find_competitors.py --brand-file assets/brand/brand.json

# Step 2 — Scrape (note the run_id from Step 1 output)
python tools/scrape_competitors.py --input .tmp/{run_id}/competitors_raw.json

# Step 3 — Analyze
python tools/analyze_competitors.py --input .tmp/{run_id}/competitors_scraped.json --brand-file assets/brand/brand.json

# Step 4 — Generate PDF
python tools/generate_report.py --input .tmp/{run_id}/analysis.json --open
```

Each step is independently restartable — if Step 3 fails, re-run only Step 3.

---

## Customization

### Brand Colors and Fonts

Edit `assets/brand/brand.json`. Changes take effect the next time the PDF is generated (Step 4 only — no API calls needed):

| Field | Effect |
|-------|--------|
| `primary_color` | Section headers, stat numbers, table backgrounds |
| `accent_color` | Cover stripe, dividers, recommendation badges |
| `heading_font` | All headings — any CSS font stack |
| `body_font` | Body text, tables, metadata |

### Report Title

```json
"report_title_template": "Competitor Analysis Report &#8212; {month} {year}"
```

Use `&#8212;` for em dashes — avoid raw Unicode characters, which wkhtmltopdf misreads on Windows.

### Report Layout

The entire PDF layout lives in `assets/templates/report_template.html` — a Jinja2 template rendered with brand tokens and analysis data. Edit it and re-run Step 4 to preview. No API calls needed.

> **VS Code note:** The CSS validator shows false-positive errors on Jinja2 `{{ variable }}` syntax. Suppress with `"css.validate": false` in `.vscode/settings.json`.

### Competitor Discovery

`tools/find_competitors.py` contains a `build_search_queries()` function with queries targeting known proptech domains. For a different industry, update these queries and add any aggregator/directory domains that appear in results to `brand.json → search.exclude_domains`.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `cannot load library 'libgobject-2.0-0'` | WeasyPrint needs GTK (unavailable on Windows) | Expected — install wkhtmltopdf, it's used automatically |
| `wkhtmltopdf not found in PATH` | Binary not on PATH | Add `C:\Program Files\wkhtmltopdf\bin` to user PATH, open a new terminal |
| Garbled `â€"` in PDF | wkhtmltopdf decodes HTML as Windows-1252 | Use HTML entities (`&#8212;`) in `brand.json` — never raw Unicode |
| Step 3 fails with 400 credit error | No Anthropic credits | Add credits at console.anthropic.com, re-run Step 3 only |
| Claude returns malformed JSON | Model response issue | Agent retries automatically (3x); try `--model claude-sonnet-4-6` if it persists |
| Serper returns zero results | Queries too specific | Edit `build_search_queries()` in `find_competitors.py` |

---

## Tech Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Agent framework | [Claude Code](https://claude.ai/code) + CLAUDE.md | Orchestrates the pipeline via natural language instructions |
| Competitor discovery | [Serper](https://serper.dev) | Google Search API |
| Website scraping | [Firecrawl](https://firecrawl.dev) | Converts competitor sites to clean markdown |
| AI analysis | [Anthropic Claude](https://console.anthropic.com) (`claude-opus-4-6`) | Synthesizes scraped content into structured insights |
| Report rendering | [Jinja2](https://jinja.palletsprojects.com) | Injects brand tokens and data into HTML template |
| PDF generation | [wkhtmltopdf](https://wkhtmltopdf.org) / [WeasyPrint](https://weasyprint.org) | HTML to PDF |

---

## License

MIT License — see [LICENSE](LICENSE) for details.
