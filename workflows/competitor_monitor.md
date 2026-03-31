# Workflow: Competitor Market Monitor

## Objective
Re-run the competitor analysis pipeline to get a fresh report and surface what has changed
since the last run. Designed for manual triggering — just say "run a market check" or
"update my competitor report" to kick this off.

## When to Run
- When you want a fresh view of the competitive landscape
- After a major industry event (new entrant, competitor funding, regulatory change)
- Before strategic planning sessions
- Quarterly at minimum for a fast-moving market like proptech

## Required Inputs
Same as `competitor_analysis.md`. All API keys must be set in `.env`.

## Tools Used
Same pipeline as `competitor_analysis.md`:
1. `tools/find_competitors.py`
2. `tools/scrape_competitors.py`
3. `tools/analyze_competitors.py`
4. `tools/generate_report.py`

## Steps

### Step 1 — Check Last Run
Look in `.tmp/` for the most recent run directory (highest timestamp folder name).
Note the date of the last run and mention it to the user.

```
ls .tmp/  →  find most recent timestamped folder
```

If the last run was less than 7 days ago, mention this to the user:
> "Your last competitor report was generated on [date]. Running again will use Firecrawl credits
> for a full re-scrape. Do you want to proceed, or skip scraping and only re-run the analysis
> on existing data?"

If user says re-use existing data, use `--input` pointing to the prior run's `competitors_scraped.json`
and skip Steps 2–3. Jump directly to Step 4.

### Step 2 — Run Full Pipeline
If proceeding with a fresh run, execute the full `competitor_analysis.md` workflow from Step 1.

Create a new RUN_ID (new timestamp) so the new run is stored separately from prior runs.

### Step 3 — Compare with Previous Run
After the new `analysis.json` is generated, compare it with the prior run's `analysis.json`:

Look for changes in:
- **New competitors** — domains in the new run not present in the prior run
- **Removed competitors** — domains from the prior run no longer appearing in search results
- **Pricing changes** — if `pricing_model` text changed significantly for any competitor
- **New recommendations** — recommendations in the new run that weren't in the prior run

Summarize changes to the user in a brief update:
> "Since your last report ([prior date]):
> - [X] new competitors found: [names]
> - [Y] competitors no longer appearing: [names]
> - Notable change: [Competitor] appears to have updated their pricing
> - [Z] new recommendations added"

If nothing significant changed, say so: "Market appears stable — no major changes vs. last run."

### Step 4 — Generate New PDF
```
python tools/generate_report.py \
  --input .tmp/{NEW_RUN_ID}/analysis.json \
  --brand-file assets/brand/brand.json \
  --open
```

### Step 5 — Report
Tell the user:
- Path to the new PDF
- Summary of what changed vs. prior run
- Suggestion: archive prior reports or delete old `.tmp/` folders to save space

## Expected Output
- New `analysis.json` in `.tmp/{NEW_RUN_ID}/`
- New `competitor_report.pdf` in `.tmp/{NEW_RUN_ID}/`
- Verbal summary of market changes

## Edge Cases & Error Handling

| Situation | Action |
|-----------|--------|
| No prior run exists | Treat as first run — skip comparison, run full pipeline |
| Prior `analysis.json` is malformed | Skip comparison, run fresh |
| API keys expired/exhausted | Report which key failed and stop — do not partially run |
| Competitor list looks completely different | Flag to user — may indicate a search drift issue; consider reviewing `find_competitors.py → build_search_queries()` |

## Notes
- This workflow is intentionally manual (no schedule). Trigger it yourself when you need an update.
- Prior run data is preserved — you can always go back and open an older PDF from `.tmp/`.
- To skip Firecrawl credits on a re-run, reuse the prior `competitors_scraped.json` and only re-run
  Steps 3–4 of `competitor_analysis.md`. This re-analyzes existing data without new scraping.
- If you want to add/remove competitors from future runs, update `brand.json →
  search.exclude_domains` or adjust `report_preferences.max_competitors`.
