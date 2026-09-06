"""
Step 6/7 support: Executive PDF + CSV report exporter.

Includes CAPEX, OPEX, LCOE, LOLP, TOPSIS ranking, the four
impact/benefit pairs, and SDG tags from the project deck.
"""
import io
import csv
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from .config import IMPACT_BENEFITS, SDG_TAGS, RESEARCH_REFERENCES
from .scenario_engine import comparison_topsis


NAVY = colors.HexColor("#1c3f6e")


def build_pdf_report(result: dict) -> bytes:
    ranked = result.get("topsis_ranking") or comparison_topsis(result)
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.5 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("TitleBlue", parent=styles["Title"], textColor=NAVY)
    heading_style = ParagraphStyle("HeadingBlue", parent=styles["Heading2"], textColor=NAVY)

    story = []
    story.append(Paragraph("Blue Grid — Scenario Executive Report", title_style))
    story.append(Paragraph(
        "Lakshadweep Multi-Energy Optimization Challenge · CODEQUADRANTS · Ocean Hackathon",
        styles["Normal"],
    ))
    story.append(Paragraph(f"Island: {result['island'].title()}", styles["Normal"]))
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("Capacity Inputs", heading_style))
    inputs = result["inputs"]
    input_table = Table(
        [["Technology", "Capacity"]]
        + [
            ["Solar PV", f"{inputs['solar_kw']:,.0f} kW"],
            ["Wind", f"{inputs['wind_kw']:,.0f} kW"],
            ["OTEC", f"{inputs['otec_kw']:,.0f} kW"],
            ["Battery (BESS)", f"{inputs['bess_kwh']:,.0f} kWh"],
        ],
        colWidths=[8 * cm, 6 * cm],
    )
    input_table.setStyle(_table_style())
    story.append(input_table)
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("Key Results (8,760-hour simulation)", heading_style))
    results_table = Table(
        [["Metric", "Value"]]
        + [
            ["Loss of Load Probability (LOLP)", f"{result['lolp_pct']:.3f}%"],
            ["Shortfall Hours / Year", f"{result['shortfall_hours']}"],
            ["CAPEX", f"Rs {result['capex']:,.0f}"],
            ["Annual OPEX", f"Rs {result['annual_opex']:,.0f}"],
            ["LCOE (year-1, energy served)", f"Rs {result['lcoe']:.2f} / kWh"],
            ["LCOE (20-year, degraded)", f"Rs {result['lcoe_lifetime']:.2f} / kWh"],
            ["CO2 Avoided", f"{result['co2_avoided_tons_per_year']:,.1f} tons/year"],
            ["Diesel displaced", f"{result['diesel_displaced_kwh']:,.0f} kWh/year"],
            ["Subsidy pressure avoided", f"Rs {result.get('diesel_subsidy_avoided_inr_per_year', 0):,.0f} / year"],
        ],
        colWidths=[8 * cm, 6 * cm],
    )
    results_table.setStyle(_table_style())
    story.append(results_table)
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("TOPSIS Ranking (current mix vs planner baselines)", heading_style))
    topsis_rows = [["Rank", "Scenario", "Score", "LCOE", "LOLP %"]]
    for row in ranked:
        topsis_rows.append([
            str(row["rank"]),
            row["label"],
            f"{row['topsis_score']:.3f}",
            f"{row['lcoe']:.2f}",
            f"{row['lolp']:.3f}",
        ])
    topsis_table = Table(topsis_rows, colWidths=[2 * cm, 4 * cm, 3 * cm, 3 * cm, 2 * cm])
    topsis_table.setStyle(_table_style())
    story.append(topsis_table)
    story.append(Spacer(1, 0.4 * cm))

    story.append(Paragraph("Impact & Benefits", heading_style))
    for item in IMPACT_BENEFITS:
        story.append(Paragraph(
            f"<b>{item['action']}</b> → {item['domain']}: {item['detail']}",
            styles["Normal"],
        ))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Sustainable Development Goals Addressed", heading_style))
    for tag in SDG_TAGS:
        story.append(Paragraph(f"• {tag}", styles["Normal"]))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Verified research references", heading_style))
    for ref in RESEARCH_REFERENCES:
        url = f" — {ref['url']}" if ref.get("url") else ""
        story.append(Paragraph(f"• {ref['text']}{url}", styles["Normal"]))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


def _table_style():
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef3fa")]),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
        ]
    )


def build_csv_report(result: dict) -> str:
    ranked = result.get("topsis_ranking") or comparison_topsis(result)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["metric", "value"])
    writer.writerow(["island", result["island"]])
    for k, v in result["inputs"].items():
        writer.writerow([k, v])
    for key in [
        "lolp_pct", "shortfall_hours", "capex", "annual_opex",
        "lcoe", "lcoe_lifetime", "co2_avoided_tons_per_year",
        "diesel_displaced_kwh", "diesel_subsidy_avoided_inr_per_year",
    ]:
        writer.writerow([key, result.get(key, "")])
    writer.writerow([])
    writer.writerow(["topsis_rank", "label", "topsis_score", "lcoe", "lolp", "capex", "co2_avoided"])
    for row in ranked:
        writer.writerow([
            row["rank"], row["label"], row["topsis_score"],
            row["lcoe"], row["lolp"], row["capex"], row["co2_avoided"],
        ])
    writer.writerow([])
    writer.writerow(["impact_action", "domain", "detail"])
    for item in IMPACT_BENEFITS:
        writer.writerow([item["action"], item["domain"], item["detail"]])
    writer.writerow([])
    writer.writerow(["sdg"])
    for tag in SDG_TAGS:
        writer.writerow([tag])
    writer.writerow([])
    writer.writerow(["reference", "url"])
    for ref in RESEARCH_REFERENCES:
        writer.writerow([ref["text"], ref.get("url") or ""])
    return output.getvalue()
