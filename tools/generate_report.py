"""
generate_report.py
Renders the branded HTML/CSS template with analysis data using Jinja2,
then converts to PDF via WeasyPrint.

Usage:
    python tools/generate_report.py --input .tmp/run_001/analysis.json
    python tools/generate_report.py --input .tmp/run_001/analysis.json --open
    python tools/generate_report.py --input .tmp/run_001/analysis.json --output reports/my_report.pdf
"""

import argparse
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


def check_weasyprint():
    try:
        import weasyprint
        return True, weasyprint
    except ImportError:
        return False, None
    except Exception as e:
        # WeasyPrint may import but fail due to missing GTK on Windows
        return False, str(e)


def render_html(template_path: str, brand: dict, analysis: dict) -> str:
    """Render the Jinja2 HTML template with brand + analysis data."""
    try:
        from jinja2 import Environment, FileSystemLoader
    except ImportError:
        print("ERROR: jinja2 not installed. Run: pip install jinja2")
        sys.exit(1)

    template_dir = str(Path(template_path).parent)
    template_file = Path(template_path).name

    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_file)

    b = brand["brand"]
    biz = brand["business"]

    now = datetime.now()
    report_date = now.strftime("%B %d, %Y")
    month_year = now.strftime("%B %Y")

    # Build report title from template
    title_template = brand["report_preferences"].get("report_title_template", "Competitor Analysis — {month} {year}")
    report_title = title_template.replace("{month}", now.strftime("%B")).replace("{year}", str(now.year))

    competitors = analysis.get("competitors", [])
    recommendations = analysis.get("recommendations_for_your_business", [])
    market_summary = analysis.get("market_summary", {})

    # Logo — embed as base64 data URI so it works in both WeasyPrint and Chrome
    logo_path = b.get("logo", "assets/brand/logo.png")
    logo_exists = os.path.exists(logo_path)
    if logo_exists:
        import base64, mimetypes
        mime = mimetypes.guess_type(logo_path)[0] or "image/png"
        with open(logo_path, "rb") as lf:
            abs_logo = "data:{};base64,{}".format(mime, base64.b64encode(lf.read()).decode())
    else:
        abs_logo = ""
        print(f"  WARN: Logo not found at '{logo_path}'. Cover page will use text fallback.")

    context = {
        # Brand tokens
        "primary_color": b.get("primary_color", "#1A3C5E"),
        "secondary_color": b.get("secondary_color", "#2E7D9F"),
        "accent_color": b.get("accent_color", "#F4A827"),
        "background_color": b.get("background_color", "#FFFFFF"),
        "text_color": b.get("text_color", "#1F2937"),
        "muted_color": b.get("muted_color", "#6B7280"),
        "heading_font": b.get("heading_font", "Georgia, serif"),
        "body_font": b.get("body_font", "Arial, sans-serif"),
        # Logo
        "logo_path": abs_logo,
        "logo_exists": logo_exists,
        # Business
        "business_name": biz["name"],
        "industry": biz["industry"],
        # Report metadata
        "report_title": report_title,
        "report_date": report_date,
        "run_id": analysis.get("run_id", "N/A"),
        # Stats
        "competitor_count": len(competitors),
        "opportunity_count": len(market_summary.get("whitespace_opportunities", [])),
        "high_priority_count": sum(1 for r in recommendations if r.get("priority") == "high"),
        # Data
        "competitors": competitors,
        "market_summary": market_summary,
        "recommendations": recommendations,
    }

    return template.render(**context)


def generate_pdf_weasyprint(html: str, output_path: str, base_url: str):
    ok, weasyprint = check_weasyprint()
    if not ok:
        return False, weasyprint  # weasyprint holds the error string here

    try:
        from weasyprint import HTML
        HTML(string=html, base_url=base_url).write_pdf(output_path)
        return True, None
    except Exception as e:
        return False, str(e)


def generate_pdf_wkhtmltopdf(html_path: str, output_path: str) -> tuple:
    """Fallback: wkhtmltopdf for Windows without GTK."""
    try:
        result = subprocess.run(
            ["wkhtmltopdf", "--quiet", "--encoding", "utf-8", "--page-size", "A4",
             "--margin-top", "18mm", "--margin-right", "16mm",
             "--margin-bottom", "22mm", "--margin-left", "16mm",
             html_path, output_path],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode == 0:
            return True, None
        return False, result.stderr
    except FileNotFoundError:
        return False, "wkhtmltopdf not found in PATH"
    except subprocess.TimeoutExpired:
        return False, "wkhtmltopdf timed out"


def main():
    parser = argparse.ArgumentParser(description="Generate branded PDF from competitor analysis")
    parser.add_argument("--input", required=True, help="Path to analysis.json")
    parser.add_argument("--brand-file", default="assets/brand/brand.json")
    parser.add_argument("--template", default="assets/templates/report_template.html")
    parser.add_argument("--output", default=None, help="Path for output PDF")
    parser.add_argument("--open", action="store_true", help="Open PDF after generation")
    args = parser.parse_args()

    for path, label in [
        (args.input, "input"),
        (args.brand_file, "brand-file"),
        (args.template, "template"),
    ]:
        if not os.path.exists(path):
            print(f"ERROR: {label} file not found: {path}")
            sys.exit(1)

    import json
    with open(args.input) as f:
        analysis = json.load(f)
    with open(args.brand_file) as f:
        brand = json.load(f)

    output = args.output
    if not output:
        run_dir = os.path.dirname(args.input)
        output = os.path.join(run_dir, "competitor_report.pdf")

    os.makedirs(os.path.dirname(output) if os.path.dirname(output) else ".", exist_ok=True)

    print("Rendering HTML template...")
    html = render_html(args.template, brand, analysis)

    # Try WeasyPrint first
    base_url = str(Path(".").resolve())
    print("Generating PDF with WeasyPrint...")
    success, error = generate_pdf_weasyprint(html, output, base_url)

    if not success:
        print(f"  WeasyPrint failed: {error}")
        print("  Trying wkhtmltopdf fallback...")

        # Write rendered HTML to a temp file for wkhtmltopdf
        tmp_html = output.replace(".pdf", "_tmp.html")
        with open(tmp_html, "w", encoding="utf-8") as f:
            f.write(html)

        success, error = generate_pdf_wkhtmltopdf(tmp_html, output)
        os.remove(tmp_html)

        if not success:
            # Last resort: save the rendered HTML so the user can print to PDF from browser
            html_output = output.replace(".pdf", ".html")
            with open(html_output, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"\nPDF generation failed ({error}).")
            print(f"Saved rendered HTML instead: {html_output}")
            print("Open this file in Chrome and use Print -> Save as PDF.")
            sys.exit(1)

    size_kb = os.path.getsize(output) // 1024
    print(f"\nPDF generated: {output} ({size_kb} KB)")

    if args.open:
        import platform
        system = platform.system()
        if system == "Windows":
            os.startfile(output)
        elif system == "Darwin":
            subprocess.run(["open", output])
        else:
            subprocess.run(["xdg-open", output])


if __name__ == "__main__":
    main()
