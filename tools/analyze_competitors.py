"""
analyze_competitors.py
Sends all scraped competitor content to Claude API for structured competitive analysis.
Produces a structured JSON with per-competitor insights and market-level recommendations.

Usage:
    python tools/analyze_competitors.py --input .tmp/run_001/competitors_scraped.json --brand-file assets/brand/brand.json
    python tools/analyze_competitors.py --input .tmp/run_001/competitors_scraped.json --output .tmp/run_001/analysis.json
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime

import anthropic
from dotenv import load_dotenv

load_dotenv()

ANALYSIS_SCHEMA = """
Return a JSON object with this exact structure:
{
  "competitors": [
    {
      "name": "string",
      "url": "string",
      "positioning": "string — one sentence describing their market position",
      "target_audience": "string — who they primarily serve",
      "pricing_model": "string — pricing structure and range if visible",
      "key_strengths": ["string", ...],
      "key_weaknesses": ["string", ...],
      "feature_highlights": ["string", ...],
      "marketing_angle": "string — their primary marketing message / value prop",
      "social_proof_signals": ["string", ...]
    }
  ],
  "market_summary": {
    "common_strengths": "string — paragraph on what most competitors do well",
    "common_weaknesses": "string — paragraph on shared gaps across competitors",
    "pricing_range": "string — summary of pricing spectrum observed",
    "whitespace_opportunities": ["string", ...]
  },
  "recommendations_for_your_business": [
    {
      "priority": "high | medium | low",
      "area": "string — e.g. Pricing, Onboarding, Content Strategy",
      "finding": "string — the specific gap or opportunity observed",
      "suggested_action": "string — concrete action to take"
    }
  ]
}
"""

SYSTEM_PROMPT = """You are a senior competitive intelligence analyst. You analyze competitor websites
and produce structured, actionable insights for businesses. Be specific and evidence-based —
cite what you actually observed in the scraped content, not general assumptions.
If data is missing for a competitor (e.g., pricing not found), note that explicitly rather than guessing.
Return only valid JSON matching the schema exactly — no markdown, no explanation, just JSON."""


def build_analysis_prompt(brand: dict, competitors: list[dict]) -> str:
    biz = brand["business"]

    comp_sections = []
    for comp in competitors:
        pages = comp.get("pages", {})
        if not pages:
            comp_sections.append(
                f"## {comp['name']} ({comp['url']})\n[No content scraped — site blocked or unavailable]\n"
            )
            continue

        section = f"## {comp['name']} ({comp['url']})\n"
        for page_type, content in pages.items():
            # Truncate very long pages to avoid burning excessive tokens
            truncated = content[:3000] if len(content) > 3000 else content
            section += f"\n### {page_type.title()} Page\n{truncated}\n"
        comp_sections.append(section)

    competitor_content = "\n\n".join(comp_sections)

    return f"""You are analyzing the competitive landscape for the following business:

**Business Name:** {biz['name']}
**Description:** {biz['description']}
**Industry:** {biz['industry']}
**Target Audience:** {biz['target_audience']}

Analyze each of the following {len(competitors)} competitors based on their scraped website content.
Then provide market-level insights and specific recommendations for {biz['name']}.

Focus your recommendations on:
1. Gaps in the market that competitors are missing
2. Weaknesses in competitor offerings that {biz['name']} could exploit
3. Pricing or positioning strategies worth testing
4. Content or trust-building signals that are working for competitors

---

{competitor_content}

---

{ANALYSIS_SCHEMA}"""


def analyze_in_batches(client: anthropic.Anthropic, brand: dict, competitors: list[dict], model: str) -> dict:
    """Fall back to batch analysis when competitor list is large."""
    batch_size = 4
    batches = [competitors[i:i+batch_size] for i in range(0, len(competitors), batch_size)]
    batch_results = []

    print(f"  Analyzing in {len(batches)} batches of up to {batch_size} competitors...")

    for i, batch in enumerate(batches, 1):
        print(f"  Batch {i}/{len(batches)}...")
        prompt = build_analysis_prompt(brand, batch)
        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        try:
            batch_result = json.loads(response.content[0].text)
            batch_results.append(batch_result)
        except json.JSONDecodeError as e:
            print(f"  WARN: Batch {i} JSON parse failed: {e}")
            continue
        time.sleep(2)

    # Merge batch results
    all_competitors = []
    for r in batch_results:
        all_competitors.extend(r.get("competitors", []))

    # Synthesize market summary across batches
    print("  Synthesizing cross-batch insights...")
    synthesis_prompt = f"""Given these batch analyses of competitors for {brand['business']['name']},
produce a unified market_summary and recommendations_for_your_business.

Batch analyses:
{json.dumps([{"market_summary": r.get("market_summary"), "recommendations": r.get("recommendations_for_your_business")} for r in batch_results], indent=2)}

Return only JSON with keys: "market_summary" and "recommendations_for_your_business" matching the original schema."""

    synthesis_response = client.messages.create(
        model=model,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": synthesis_prompt}],
    )
    synthesis = json.loads(synthesis_response.content[0].text)

    return {
        "competitors": all_competitors,
        "market_summary": synthesis.get("market_summary", {}),
        "recommendations_for_your_business": synthesis.get("recommendations_for_your_business", []),
    }


def main():
    parser = argparse.ArgumentParser(description="Analyze competitors using Claude API")
    parser.add_argument("--input", required=True, help="Path to competitors_scraped.json")
    parser.add_argument("--brand-file", default="assets/brand/brand.json")
    parser.add_argument("--output", default=None, help="Path to write analysis.json")
    parser.add_argument("--model", default="claude-opus-4-6", help="Claude model to use")
    args = parser.parse_args()

    for path, label in [(args.input, "input"), (args.brand_file, "brand-file")]:
        if not os.path.exists(path):
            print(f"ERROR: {label} file not found: {path}")
            sys.exit(1)

    with open(args.input) as f:
        scraped = json.load(f)

    with open(args.brand_file) as f:
        brand = json.load(f)

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in .env")
        sys.exit(1)

    competitors = scraped["competitors"]
    run_id = scraped["run_id"]

    # Filter to competitors that have at least some scraped content
    analyzable = [c for c in competitors if c.get("pages")]
    skipped = [c["name"] for c in competitors if not c.get("pages")]
    if skipped:
        print(f"Skipping {len(skipped)} competitors with no scraped content: {', '.join(skipped)}")

    if not analyzable:
        print("ERROR: No competitors have scraped content to analyze.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"Analyzing {len(analyzable)} competitors with {args.model}...")

    analysis = {}
    # Use batching only for very large sets (12+) — single call handles up to ~12 competitors cleanly
    if len(analyzable) > 12:
        analysis = analyze_in_batches(client, brand, analyzable, args.model)
    else:
        prompt = build_analysis_prompt(brand, analyzable)
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.messages.create(
                    model=args.model,
                    max_tokens=8192,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": prompt}],
                )
                raw = response.content[0].text.strip()
                # Strip markdown code fences if present
                if raw.startswith("```"):
                    raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
                analysis = json.loads(raw)
                break
            except json.JSONDecodeError as e:
                print(f"  WARN: JSON parse failed on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    print("ERROR: Could not parse Claude response as JSON after retries.")
                    sys.exit(1)
                time.sleep(5)
            except anthropic.RateLimitError:
                wait = 30 * (attempt + 1)
                print(f"  Rate limited. Waiting {wait}s...")
                time.sleep(wait)

    output = args.output
    if not output:
        run_dir = os.path.dirname(args.input)
        output = os.path.join(run_dir, "analysis.json")

    payload = {
        "run_id": run_id,
        "generated_at": datetime.now().isoformat(),
        "business_name": brand["business"]["name"],
        "model_used": args.model,
        "competitors_analyzed": len(analyzable),
        "competitors_skipped": skipped,
        **analysis,
    }

    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w") as f:
        json.dump(payload, f, indent=2)

    recs = analysis.get("recommendations_for_your_business", [])
    high = sum(1 for r in recs if r.get("priority") == "high")
    opps = len(analysis.get("market_summary", {}).get("whitespace_opportunities", []))

    print(f"\nAnalysis complete:")
    print(f"  Competitors profiled: {len(analyzable)}")
    print(f"  Whitespace opportunities: {opps}")
    print(f"  Recommendations: {len(recs)} ({high} high priority)")
    print(f"Output: {output}")


if __name__ == "__main__":
    main()
