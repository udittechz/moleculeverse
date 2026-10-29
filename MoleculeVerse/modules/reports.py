"""Exports: PDF report (ReportLab), CSV, JSON. Operates on the dict from chemistry.analyze_smiles."""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Any, Optional
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import config

DISCLAIMER = (
    "All values in this report are calculated descriptors or computational predictions produced with "
    "RDKit from the molecular graph. They are not experimental measurements, and they do not by "
    "themselves establish stability, synthesizability, biological activity, toxicity, drug suitability or safety."
)


def _fmt(value: Any, unit: str = "") -> str:
    if value is None:
        return "Not available"
    text = f"{value}"
    return f"{text} {unit}".strip()


def _image(png: bytes, max_w: float, max_h: float) -> RLImage:
    from PIL import Image

    w, h = Image.open(io.BytesIO(png)).size
    scale = min(max_w / w, max_h / h)
    return RLImage(io.BytesIO(png), width=w * scale, height=h * scale)


def build_pdf_report(
    record: dict[str, Any],
    png_2d: Optional[bytes] = None,
    image_3d: Optional[bytes] = None,
    student: Optional[dict[str, str]] = None,
    generated_at: Optional[datetime] = None,
) -> bytes:
    """Build the PDF report. ``image_3d`` is omitted cleanly when None. ``student`` only if the user opted in."""
    when = (generated_at or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M UTC")
    base = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=base["Title"], textColor=colors.HexColor("#176B4D"), fontSize=20)
    h2 = ParagraphStyle("h2", parent=base["Heading2"], textColor=colors.HexColor("#0C211C"), spaceBefore=10)
    body = ParagraphStyle("b", parent=base["BodyText"], fontSize=9, leading=12)
    cell = ParagraphStyle("c", parent=body, fontSize=8, leading=10, wordWrap="CJK")
    small = ParagraphStyle("s", parent=body, fontSize=8, textColor=colors.HexColor("#444444"))

    def P(text: Any, style=cell) -> Paragraph:
        return Paragraph(escape(str(text)), style)

    story: list[Any] = [
        Paragraph(f"{escape(config.APP_NAME)}: Molecular Report", title),
        Paragraph(escape(f"{config.APP_SUBTITLE} | {config.INSTITUTION}"), body),
        Paragraph(f"Report date: {when}", body),
        Spacer(1, 8),
    ]
    if student and (student.get("name") or student.get("registration")):
        story.append(Paragraph("Prepared by (included at the student's request)", h2))
        if student.get("name"):
            story.append(Paragraph("Name: " + escape(student["name"]), body))
        if student.get("registration"):
            story.append(Paragraph("Registration number: " + escape(student["registration"]), body))

    status = "Valid (RDKit parsed and sanitized)" if record.get("valid") else "Invalid: " + str(record.get("message", ""))
    ident = [
        ["Molecule name", record.get("name") or "Not supplied"],
        ["Submitted SMILES", record.get("input_smiles", "")],
        ["Validation status", status],
        ["Canonical SMILES", record.get("canonical_smiles") or "Not available"],
        ["Isomeric SMILES", record.get("isomeric_smiles") or "Not available"],
        ["Molecular formula", record.get("formula") or "Not available"],
    ]
    t = Table([[P(a, ParagraphStyle("k", parent=cell, fontName="Helvetica-Bold")), P(b)] for a, b in ident], colWidths=[4 * cm, 12.5 * cm])
    t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9DB5AB")),
                           ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#E6F2EC")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story += [Paragraph("Identification", h2), t]

    if png_2d:
        story += [Paragraph("2D structure", h2), _image(png_2d, 9 * cm, 7 * cm)]
    if image_3d:
        story += [Paragraph("3D visualization (computational conformer)", h2), _image(image_3d, 9 * cm, 7 * cm)]

    props = record.get("properties") or []
    if props:
        story.append(Paragraph("Calculated descriptors", h2))
        for category in dict.fromkeys(p["category"] for p in props):
            rows = [[P("Property", ParagraphStyle("hh", parent=cell, fontName="Helvetica-Bold")),
                     P("Value", ParagraphStyle("hh", parent=cell, fontName="Helvetica-Bold")),
                     P("What it measures", ParagraphStyle("hh", parent=cell, fontName="Helvetica-Bold"))]]
            rows += [[P(p["label"]), P(_fmt(p["value"], p["unit"])), P(p["explanation"])] for p in props if p["category"] == category]
            tb = Table(rows, colWidths=[4.6 * cm, 4.4 * cm, 7.5 * cm], repeatRows=1)
            tb.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9DB5AB")),
                                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#CDE8DB")), ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            story += [Paragraph(escape(category), base["Heading3"]), tb]
    comp = record.get("composition") or []
    if comp:
        story.append(Paragraph("Element composition", h2))
        rows = [["Element", "Atoms", "Mass %"]] + [[c["element"], c["count"], c["mass_percent"]] for c in comp]
        tb = Table(rows, colWidths=[4 * cm, 3 * cm, 3 * cm])
        tb.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#9DB5AB")),
                                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#CDE8DB"))]))
        story.append(tb)
    fp = record.get("fingerprint")
    if fp:
        story.append(Paragraph(escape(f"Fingerprint: {fp['type']}; {fp['bits_set']} of {fp['length']} bits set."), small))
    story += [Spacer(1, 10), Paragraph("Important note", h2), Paragraph(escape(DISCLAIMER), body)]

    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=1.8 * cm,
                            title=f"{config.APP_NAME} report", author=config.APP_NAME)
    doc.build(story)
    return buf.getvalue()


def properties_to_csv(record: dict[str, Any]) -> str:
    """CSV of identity fields and all calculated properties."""
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["Category", "Property", "Value", "Unit", "Description"])
    w.writerow(["Identification", "Molecule name", record.get("name", ""), "", ""])
    w.writerow(["Identification", "Submitted SMILES", record.get("input_smiles", ""), "", ""])
    w.writerow(["Identification", "Validation status", "valid" if record.get("valid") else "invalid", "", record.get("message", "")])
    for p in record.get("properties") or []:
        w.writerow([p["category"], p["label"], "" if p["value"] is None else p["value"], p["unit"], p["explanation"]])
    for c in record.get("composition") or []:
        w.writerow(["Element composition", c["element"], c["count"], "atoms", f"{c['mass_percent']} % by mass"])
    return out.getvalue()


def record_to_json(record: dict[str, Any], generated_at: Optional[datetime] = None) -> str:
    """JSON export (never includes student information)."""
    payload = {
        "generator": f"{config.APP_NAME} - {config.APP_SUBTITLE}",
        "generated_at": (generated_at or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "note": DISCLAIMER,
        "molecule": {k: record.get(k) for k in ("name", "input_smiles", "valid", "message", "canonical_smiles",
                                                  "isomeric_smiles", "formula", "inchikey", "warnings")},
        "properties": record.get("values", {}),
        "property_details": record.get("properties", []),
        "composition": record.get("composition", []),
        "fingerprint": record.get("fingerprint", {}),
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)
