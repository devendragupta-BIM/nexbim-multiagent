import logging
import os
from datetime import datetime
from typing import Any, Dict, List
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table,
    TableStyle, HRFlowable, KeepTogether
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

logger = logging.getLogger(__name__)

NEXBIM_BLUE   = colors.HexColor("#1B3A6B")
NEXBIM_ACCENT = colors.HexColor("#2E86AB")
NEXBIM_GREEN  = colors.HexColor("#27AE60")
NEXBIM_RED    = colors.HexColor("#E74C3C")
NEXBIM_ORANGE = colors.HexColor("#F39C12")
NEXBIM_LIGHT  = colors.HexColor("#F4F6F9")
NEXBIM_GRAY   = colors.HexColor("#7F8C8D")
WHITE = colors.white
BLACK = colors.black


def _severity_color(severity: str) -> colors.Color:
    return {
        "critical": NEXBIM_RED,
        "major":    NEXBIM_ORANGE,
        "minor":    NEXBIM_GREEN
    }.get(severity.lower(), NEXBIM_GRAY)


def _priority_color(priority: str) -> colors.Color:
    return {
        "immediate":  NEXBIM_RED,
        "this_week":  NEXBIM_ORANGE,
        "this_month": NEXBIM_GREEN
    }.get(priority.lower(), NEXBIM_GRAY)


def _section_header(title: str, W: float) -> Table:
    style = ParagraphStyle(
        "SH", fontSize=11, fontName="Helvetica-Bold",
        textColor=WHITE, alignment=TA_LEFT
    )
    t = Table([[Paragraph(title, style)]], colWidths=[W])
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NEXBIM_BLUE),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ]))
    return t


def _kpi_cell(label: str, value: str, color: colors.Color) -> Table:
    val_style = ParagraphStyle(
        "KV", fontSize=16, fontName="Helvetica-Bold",
        textColor=color, alignment=TA_CENTER
    )
    lbl_style = ParagraphStyle(
        "KL", fontSize=7, fontName="Helvetica",
        textColor=NEXBIM_GRAY, alignment=TA_CENTER
    )
    t = Table(
        [[Paragraph(value, val_style)],
         [Paragraph(label, lbl_style)]],
        colWidths=["100%"]
    )
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), WHITE),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
    ]))
    return t


def generate_report(
    project_summary: Dict[str, Any],
    resolutions: List[Dict[str, Any]],
    output_path: str = "NexBIM_Coordination_Report.pdf"
) -> str:

    os.makedirs(
        os.path.dirname(output_path) if os.path.dirname(output_path) else ".",
        exist_ok=True
    )

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1.5 * cm,
        leftMargin=1.5 * cm,
        topMargin=1.5 * cm,
        bottomMargin=1.5 * cm
    )

    W = A4[0] - 3.0 * cm
    story = []
    generated_on = datetime.now().strftime("%d %B %Y, %I:%M %p")

    th = ParagraphStyle("TH", fontSize=8, fontName="Helvetica-Bold",
                        textColor=WHITE, alignment=TA_CENTER)
    td = ParagraphStyle("TD", fontSize=8, fontName="Helvetica",
                        textColor=BLACK)
    td_center = ParagraphStyle("TDC", fontSize=8, fontName="Helvetica",
                               textColor=BLACK, alignment=TA_CENTER)

    # ── COVER ──────────────────────────────────────────────────────────
    cover = Table(
        [[Paragraph("NexBIM", ParagraphStyle(
            "CT", fontSize=26, fontName="Helvetica-Bold",
            textColor=WHITE, alignment=TA_CENTER
        ))],
         [Paragraph("Multi-Agent BIM Coordination Report", ParagraphStyle(
             "CS", fontSize=11, fontName="Helvetica",
             textColor=colors.HexColor("#BDC3C7"), alignment=TA_CENTER
         ))]],
        colWidths=[W]
    )
    cover.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), NEXBIM_BLUE),
        ("BACKGROUND",    (0, 1), (-1, 1), NEXBIM_ACCENT),
        ("TOPPADDING",    (0, 0), (-1, 0), 22),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("TOPPADDING",    (0, 1), (-1, 1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
    ]))
    story.append(cover)
    story.append(Spacer(1, 0.3 * cm))

    # ── METADATA ───────────────────────────────────────────────────────
    lbl = ParagraphStyle("ML", fontSize=8, fontName="Helvetica-Bold",
                         textColor=NEXBIM_BLUE)
    val = ParagraphStyle("MV", fontSize=8, fontName="Helvetica",
                         textColor=BLACK)
    meta = Table([
        [Paragraph("Project Name", lbl),
         Paragraph(project_summary.get("project_name", "—"), val),
         Paragraph("Generated On", lbl),
         Paragraph(generated_on, val)],
        [Paragraph("Project ID", lbl),
         Paragraph(project_summary.get("project_id", "—"), val),
         Paragraph("System Version", lbl),
         Paragraph("NexBIM v1.0", val)],
        [Paragraph("Disciplines", lbl),
         Paragraph(", ".join(project_summary.get("disciplines", [])), val),
         Paragraph("Pipeline Stage", lbl),
         Paragraph(project_summary.get("pipeline_stage", "—").title(), val)],
    ], colWidths=[W*0.18, W*0.32, W*0.18, W*0.32])
    meta.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), NEXBIM_LIGHT),
        ("GRID",          (0, 0), (-1, -1), 0.3, colors.HexColor("#D5D8DC")),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 6),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story.append(meta)
    story.append(Spacer(1, 0.35 * cm))

    # ── KPI ROW 1 ──────────────────────────────────────────────────────
    story.append(_section_header("Executive Summary", W))
    story.append(Spacer(1, 0.2 * cm))

    elements      = project_summary.get("total_elements", 0)
    total_clashes = project_summary.get("total_clashes", 0)
    resolved      = project_summary.get("resolved_clashes", 0)
    open_count    = project_summary.get("open_clashes", 0)
    health        = project_summary.get("health_score", 0)
    cost          = project_summary.get("total_cost_impact", 0)
    days          = project_summary.get("schedule_impact_days", 0)
    comp_count    = project_summary.get("compliance_issues", 0)
    lod_count     = project_summary.get("lod_violations", 0)

    def kpi_row(cells):
        t = Table([cells], colWidths=[W/4]*4)
        t.setStyle(TableStyle([
            ("GRID",          (0, 0), (-1, -1), 0.3,
             colors.HexColor("#D5D8DC")),
            ("TOPPADDING",    (0, 0), (-1, -1), 0),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
            ("LEFTPADDING",   (0, 0), (-1, -1), 0),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
        ]))
        return t

    story.append(kpi_row([
        _kpi_cell("Total Elements",  str(elements),      NEXBIM_BLUE),
        _kpi_cell("Total Clashes",   str(total_clashes), NEXBIM_RED),
        _kpi_cell("Resolved",        str(resolved),      NEXBIM_GREEN),
        _kpi_cell("Open Clashes",    str(open_count),
                  NEXBIM_RED if open_count > 0 else NEXBIM_GREEN),
    ]))
    story.append(kpi_row([
        _kpi_cell("Health Score",
                  f"{health}/100",
                  NEXBIM_GREEN if health >= 75 else
                  NEXBIM_ORANGE if health >= 50 else NEXBIM_RED),
        _kpi_cell("Cost Impact",       f"Rs.{cost:,.0f}", NEXBIM_ORANGE),
        _kpi_cell("Compliance Issues", str(comp_count),
                  NEXBIM_GREEN if comp_count == 0 else NEXBIM_ORANGE),
        _kpi_cell("LOD Violations",    str(lod_count),
                  NEXBIM_GREEN if lod_count == 0 else NEXBIM_RED),
    ]))
    story.append(Spacer(1, 0.4 * cm))

    # ── CLASH SUMMARY ──────────────────────────────────────────────────
    story.append(_section_header("Clash Detection Summary", W))
    story.append(Spacer(1, 0.2 * cm))

    clash_rows = []
    for r in resolutions:
        sev = r.get("severity", "minor")
        clash_rows.append([
            Paragraph(r.get("clash_id", "—"), td_center),
            Paragraph(sev.upper(), ParagraphStyle(
                "SEV", fontSize=8, fontName="Helvetica-Bold",
                textColor=_severity_color(sev), alignment=TA_CENTER
            )),
            Paragraph(r.get("resolution", {}).get(
                "responsible_discipline", "—").upper(), td_center),
            Paragraph(r.get("element_1", "—"), td),
            Paragraph(r.get("element_2", "—"), td),
            Paragraph("RESOLVED", ParagraphStyle(
                "RES", fontSize=8, fontName="Helvetica-Bold",
                textColor=NEXBIM_GREEN, alignment=TA_CENTER
            )),
        ])

    clash_table = Table(
        [[Paragraph("Clash ID", th), Paragraph("Severity", th),
          Paragraph("Discipline", th), Paragraph("Element 1", th),
          Paragraph("Element 2", th), Paragraph("Status", th)]]
        + clash_rows,
        colWidths=[W*0.17, W*0.1, W*0.12, W*0.2, W*0.2, W*0.13],
        repeatRows=1
    )
    cs = [
        ("BACKGROUND", (0, 0), (-1, 0), NEXBIM_ACCENT),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5D8DC")),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    for i in range(len(clash_rows)):
        if i % 2 == 0:
            cs.append(("BACKGROUND", (0, i+1), (-1, i+1), NEXBIM_LIGHT))
    clash_table.setStyle(TableStyle(cs))
    story.append(clash_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── AI RESOLUTIONS ─────────────────────────────────────────────────
    story.append(_section_header("AI-Generated Clash Resolutions", W))
    story.append(Spacer(1, 0.3 * cm))

    lbl2 = ParagraphStyle("RL", fontSize=8, fontName="Helvetica-Bold",
                          textColor=NEXBIM_BLUE)
    val2 = ParagraphStyle("RV", fontSize=8, fontName="Helvetica",
                          textColor=BLACK)

    for r in resolutions:
        res = r.get("resolution", {})
        sev = r.get("severity", "minor")
        priority = res.get("priority", "this_week")

        hdr = Table([[
            Paragraph(r.get("clash_id", "—"), ParagraphStyle(
                "HID", fontSize=10, fontName="Helvetica-Bold",
                textColor=NEXBIM_BLUE
            )),
            Paragraph(sev.upper(), ParagraphStyle(
                "HSEV", fontSize=9, fontName="Helvetica-Bold",
                textColor=WHITE, alignment=TA_CENTER
            )),
            Paragraph(priority.replace("_", " ").upper(), ParagraphStyle(
                "HPRI", fontSize=9, fontName="Helvetica-Bold",
                textColor=WHITE, alignment=TA_CENTER
            )),
        ]], colWidths=[W*0.5, W*0.25, W*0.25])
        hdr.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (0, 0), NEXBIM_LIGHT),
            ("BACKGROUND",    (1, 0), (1, 0), _severity_color(sev)),
            ("BACKGROUND",    (2, 0), (2, 0), _priority_color(priority)),
            ("TOPPADDING",    (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
            ("LEFTPADDING",   (0, 0), (-1, -1), 8),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 8),
            ("GRID",          (0, 0), (-1, -1), 0.3,
             colors.HexColor("#D5D8DC")),
            ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ]))

        rows = [
            ("Elements in Conflict",
             f"{r.get('element_1','—')}  vs  {r.get('element_2','—')}"),
            ("Resolution",       res.get("resolution_summary", "—")),
            ("Action Required",  res.get("action_required", "—")),
            ("Alternative",      res.get("alternative_solution", "—")),
            ("Discipline",       res.get("responsible_discipline","—").upper()),
            ("Standard",         res.get("reference_standard", "—")),
            ("Cost Impact",      f"Rs.{res.get('estimated_cost_impact_inr',0):,}"),
            ("Schedule Impact",  f"{res.get('estimated_schedule_impact_days',0)} working days"),
            ("Technical Notes",  res.get("notes", "—")),
        ]
        detail = Table(
            [[Paragraph(k, lbl2), Paragraph(v, val2)] for k, v in rows],
            colWidths=[W*0.25, W*0.75]
        )
        ds = [
            ("GRID",          (0, 0), (-1, -1), 0.3,
             colors.HexColor("#D5D8DC")),
            ("TOPPADDING",    (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING",   (0, 0), (-1, -1), 7),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ]
        for i in range(len(rows)):
            if i % 2 == 0:
                ds.append(("BACKGROUND", (0, i), (-1, i), NEXBIM_LIGHT))
            else:
                ds.append(("BACKGROUND", (0, i), (-1, i), WHITE))
        detail.setStyle(TableStyle(ds))
        story.append(KeepTogether([hdr, detail, Spacer(1, 0.3 * cm)]))

    # ── COMPLIANCE SECTION ─────────────────────────────────────────────
    story.append(_section_header(
        f"Compliance Check — {comp_count} Issues Found", W
    ))
    story.append(Spacer(1, 0.2 * cm))

    comp_list = project_summary.get("compliance_issues_list", [])
    if not comp_list:
        story.append(Paragraph(
            "No compliance issues detected.",
            ParagraphStyle("OK", fontSize=9, fontName="Helvetica",
                          textColor=NEXBIM_GREEN)
        ))
    else:
        comp_rows = []
        for issue in comp_list:
            sev = issue.get("severity", "major")
            comp_rows.append([
                Paragraph(issue.get("standard", "—"), td),
                Paragraph(issue.get("clause", "—"), td_center),
                Paragraph(sev.upper(), ParagraphStyle(
                    "CS2", fontSize=8, fontName="Helvetica-Bold",
                    textColor=_severity_color(sev), alignment=TA_CENTER
                )),
                Paragraph(issue.get("description", "—"), td),
                Paragraph(issue.get("recommendation", "—"), td),
            ])
        comp_table = Table(
            [[Paragraph("Standard", th), Paragraph("Clause", th),
              Paragraph("Severity", th), Paragraph("Description", th),
              Paragraph("Recommendation", th)]]
            + comp_rows,
            colWidths=[W*0.18, W*0.12, W*0.1, W*0.28, W*0.32],
            repeatRows=1
        )
        cst = [
            ("BACKGROUND", (0, 0), (-1, 0), NEXBIM_ACCENT),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5D8DC")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        for i in range(len(comp_rows)):
            if i % 2 == 0:
                cst.append(
                    ("BACKGROUND", (0, i+1), (-1, i+1), NEXBIM_LIGHT)
                )
        comp_table.setStyle(TableStyle(cst))
        story.append(comp_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── LOD SECTION ────────────────────────────────────────────────────
    story.append(_section_header(
        f"Level of Development (LOD) Check — {lod_count} Violations", W
    ))
    story.append(Spacer(1, 0.2 * cm))

    lod_list = project_summary.get("lod_violations_list", [])
    if not lod_list:
        story.append(Paragraph(
            "No LOD violations detected.",
            ParagraphStyle("OK2", fontSize=9, fontName="Helvetica",
                          textColor=NEXBIM_GREEN)
        ))
    else:
        lod_rows = []
        for v in lod_list:
            sev = v.get("severity", "major")
            missing = ", ".join(v.get("missing_attributes", []))
            lod_rows.append([
                Paragraph(v.get("element_name", "—"), td),
                Paragraph(v.get("element_type", "—"), td),
                Paragraph(str(v.get("required_lod", "—")), td_center),
                Paragraph(str(v.get("actual_lod", "—")), td_center),
                Paragraph(f"{v.get('completeness', 0)}%", td_center),
                Paragraph(sev.upper(), ParagraphStyle(
                    "LS2", fontSize=8, fontName="Helvetica-Bold",
                    textColor=_severity_color(sev), alignment=TA_CENTER
                )),
                Paragraph(missing, td),
            ])
        lod_table = Table(
            [[Paragraph("Element", th), Paragraph("Type", th),
              Paragraph("Req LOD", th), Paragraph("Act LOD", th),
              Paragraph("Complete", th), Paragraph("Severity", th),
              Paragraph("Missing Attributes", th)]]
            + lod_rows,
            colWidths=[W*0.12, W*0.14, W*0.08, W*0.08,
                       W*0.08, W*0.1, W*0.4],
            repeatRows=1
        )
        lst = [
            ("BACKGROUND", (0, 0), (-1, 0), NEXBIM_ACCENT),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5D8DC")),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]
        for i in range(len(lod_rows)):
            if i % 2 == 0:
                lst.append(
                    ("BACKGROUND", (0, i+1), (-1, i+1), NEXBIM_LIGHT)
                )
        lod_table.setStyle(TableStyle(lst))
        story.append(lod_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── AGENT LOG ──────────────────────────────────────────────────────
    story.append(_section_header("Agent Execution Log", W))
    story.append(Spacer(1, 0.2 * cm))

    agent_logs = project_summary.get("agent_logs", [])
    log_rows = []
    for log in agent_logs:
        ts = log.get("timestamp", "")
        if "T" in ts:
            ts = ts.split("T")[1][:8]
        status = log.get("status", "—").upper()
        log_rows.append([
            Paragraph(ts, td_center),
            Paragraph(log.get("agent", "—"), td),
            Paragraph(log.get("action", "—"), td),
            Paragraph(log.get("result", "—"), td),
            Paragraph(status, ParagraphStyle(
                "LS", fontSize=7.5, fontName="Helvetica-Bold",
                textColor=NEXBIM_GREEN if status == "SUCCESS"
                else NEXBIM_RED, alignment=TA_CENTER
            )),
        ])

    log_table = Table(
        [[Paragraph("Time", th), Paragraph("Agent", th),
          Paragraph("Action", th), Paragraph("Result", th),
          Paragraph("Status", th)]]
        + log_rows,
        colWidths=[W*0.09, W*0.15, W*0.17, W*0.47, W*0.12],
        repeatRows=1
    )
    ls = [
        ("BACKGROUND", (0, 0), (-1, 0), NEXBIM_BLUE),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D5D8DC")),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    for i in range(len(log_rows)):
        if i % 2 == 0:
            ls.append(("BACKGROUND", (0, i+1), (-1, i+1), NEXBIM_LIGHT))
    log_table.setStyle(TableStyle(ls))
    story.append(log_table)
    story.append(Spacer(1, 0.4 * cm))

    # ── FOOTER ─────────────────────────────────────────────────────────
    story.append(HRFlowable(
        width=W, thickness=0.5, color=NEXBIM_ACCENT, spaceAfter=5
    ))
    story.append(Paragraph(
        f"Generated by NexBIM Multi-Agent System v1.0  |  "
        f"Powered by Groq LLaMA 3.3 70B  |  {generated_on}  |  "
        f"Confidential — For Internal Use Only",
        ParagraphStyle("FT", fontSize=7, fontName="Helvetica",
                      textColor=NEXBIM_GRAY, alignment=TA_CENTER)
    ))

    doc.build(story)
    logger.info(f"Report generated: {output_path}")
    return output_path