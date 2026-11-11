# Builds the PDF from a ValidationResult. No LLM here: same data = same PDF.
from io import BytesIO
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, ListFlowable, ListItem)
from app.models import ValidationResult
from app.finance.score import WEIGHTS

# ---- Styles ----
base = getSampleStyleSheet()
BODY = ParagraphStyle("body", parent=base["BodyText"], fontSize=10, leading=14)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=8.5, leading=11)
WHITE = ParagraphStyle("white", parent=BODY, fontSize=16, leading=20, textColor=colors.white)
H1 = ParagraphStyle("h1", parent=base["Heading1"], fontSize=20, spaceAfter=4)
H2 = ParagraphStyle("h2", parent=base["Heading2"], fontSize=13, spaceBefore=14, spaceAfter=6)
VERDICT_COLOR = {"Go": "#1a7f37", "Pivot": "#b7791f", "No-Go": "#c0392b", "Insufficient data": "#555555"}

# ---- Small helpers ----
def p(text, style=BODY):
    # Paragraph reads XML-like tags, so we escape "&" and "<" that may appear in LLM text
    return Paragraph(escape(str(text)), style)

def link(url, label):
    # Clickable link, so every claim can be checked against its source
    return Paragraph(f'<link href="{escape(url, {chr(34): "&quot;"})}" color="blue">{escape(label)}</link>', SMALL)

def bullets(items):
    return ListFlowable([ListItem(p(i)) for i in items], bulletType="bullet", leftIndent=14)

def table(rows, widths):
    t = Table(rows, colWidths=widths, repeatRows=1)   # repeatRows: header repeats on a new page
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eef1f5")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t

def usd(v):
    return f"${v:,.0f}"

def footer(canvas, doc):
    # Drawn on every page
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawString(2 * cm, 1.2 * cm, "AI-generated from public web snippets and stated assumptions. Not financial advice.")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")

# ---- Main function ----
def build_pdf(r: ValidationResult) -> bytes:
    buf = BytesIO()   # build the PDF in memory, no temp files
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2*cm, rightMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm, title="Startup Idea Validation Report")
    W = A4[0] - 4 * cm   # usable page width
    s = []               # "story": the list of blocks, drawn top to bottom
    t = r.report_text

    # 1. Title and verdict banner
    s += [p("Startup Idea Validation Report", H1), p(f"{r.idea.product_type.replace('_', ' ').title()} | Region: {r.idea.region}", SMALL), Spacer(1, 10)]
    banner = Table([[Paragraph(f"{escape(r.score.verdict)} &nbsp; {r.score.total}/100", WHITE)]], colWidths=[W])
    banner.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(VERDICT_COLOR[r.score.verdict])),
                                ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    s += [banner, Spacer(1, 8)]
    if t:
        s.append(p(t.executive_summary))

    # 2. Score breakdown
    rows = [["Factor", "Points (0-100)", "Weight", "Data"]]
    for k, pts in r.score.breakdown.items():
        known = "No data (neutral 40 used)" if k in r.score.unknown_factors else "From analysis"
        rows.append([k.title(), pts, f"{WEIGHTS[k]}%", known])
    s += [p("Score breakdown", H2), table(rows, [W*0.25, W*0.2, W*0.15, W*0.4])]
    s.append(p("Weights and thresholds are our own choices, not industry standards.", SMALL))

    # 3. Idea snapshot
    i = r.idea
    snap = [["Field", "Details"], ["Problem", p(i.problem)], ["Target customer", p(i.target_customer)],
            ["Solution", p(i.solution)], ["Business model", p(i.business_model)]]
    s += [p("Idea snapshot", H2), table(snap, [W*0.25, W*0.75])]

    # 4. Demand
    s.append(p("Demand analysis", H2))
    if r.demand:
        s.append(p(f"Demand level: {r.demand.demand_level}", BODY))
        if t: s.append(p(t.demand_analysis))
        if r.demand.pain_points:
            s += [p("Pain points found:", SMALL), bullets(r.demand.pain_points)]
        for e in r.demand.evidence:
            s += [link(e.url, e.title), p(e.why_relevant, SMALL)]
        s.append(p(f"Limitations: {r.demand.limitations}", SMALL))
    else:
        s.append(p("Demand analysis failed. See errors."))

    # 5. Competitors
    s.append(p("Competition", H2))
    if r.competitors:
        s.append(p(f"Competition level: {r.competitors.competition_level}"))
        rows = [["Name", "What it does", "Pricing", "Gap / weakness", "Source"]]
        for c in r.competitors.competitors:
            rows.append([p(c.name, SMALL), p(c.what_it_does, SMALL), p(c.pricing, SMALL),
                         p(c.weakness_or_gap, SMALL), link(c.source_url, "link")])
        if len(rows) > 1:
            s.append(table(rows, [W*0.17, W*0.33, W*0.12, W*0.28, W*0.10]))
        s += [Spacer(1, 6), p(f"Market gap: {r.competitors.market_gap}"),
              p(f"Limitations: {r.competitors.limitations}", SMALL)]
        if t: s.append(p(t.competition_analysis))
    else:
        s.append(p("Competitor analysis failed. See errors."))

    # 6. Market and finance
    s.append(p("Market size and finance (USD)", H2))
    if r.finance:
        f = r.finance
        rows = [["Metric", "Value", "How it is calculated"],
                ["TAM", usd(f.tam), "customers x price x 12 months"],
                ["SAM", usd(f.sam), "TAM x reach %"],
                ["SOM", usd(f.som), "SAM x win % (year 1)"],
                ["LTV", usd(f.ltv), "price x gross margin / monthly churn"],
                ["LTV:CAC", f.ltv_cac_ratio if f.ltv_cac_ratio is not None else "n/a", "LTV / CAC (3 or more is healthy)"],
                ["CAC payback", f"{f.payback_months} months" if f.payback_months is not None else "n/a", "CAC / (price x gross margin)"],
                ["Break-even", f"{f.break_even_users} users" if f.break_even_users is not None else "Never", "fixed costs / (price - variable cost)"],
                ["Runway", f"{f.runway_months} months" if f.runway_months is not None else "n/a", "cash / monthly fixed costs"]]
        s.append(table(rows, [W*0.2, W*0.25, W*0.55]))
    else:
        s.append(p(r.assumptions.get("finance", "Finance was skipped.")))
    if r.market:
        note = f"Market search: {r.market.customers_note}"
        s.append(p(note, SMALL))
        if r.market.customers_source_url:
            s.append(link(r.market.customers_source_url, "Source of the market number"))
    if t: s.append(p(t.market_and_finance))

    # 7. Assumptions
    rows = [["Input", "Value and source"]] + [[k, p(v, SMALL)] for k, v in r.assumptions.items()]
    s += [p("Assumptions and inputs", H2), table(rows, [W*0.3, W*0.7])]

    # 8. Risks and next steps
    if t:
        s += [p("Key risks", H2), bullets(t.key_risks), p("30-day next steps", H2), bullets(t.next_steps)]

    # 9. Errors, if any agent failed
    if r.errors:
        s += [p("Notes on missing data", H2), bullets(r.errors)]

    doc.build(s, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()