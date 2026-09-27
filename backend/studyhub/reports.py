"""Printable reports (ReportLab PDF) and spreadsheet exports (openpyxl XLSX, CSV).

Rendering only: every function takes data the API has already computed and scoped to the signed-in user, so a report can
never contain anything the student could not see on screen. PDFs carry only a title in their metadata (no author, no
producer details beyond ReportLab's default), charts are drawn as vectors, and tables repeat their header row on every page.
"""
from __future__ import annotations

import csv
import io
import time
from typing import Iterable

from reportlab.graphics.charts.barcharts import HorizontalBarChart, VerticalBarChart
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing, Line, String
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle)

BLUE = colors.HexColor("#0194E2")
BLUE_DEEP = colors.HexColor("#0B5CAD")
NAVY = colors.HexColor("#0B1F3A")
MUTED = colors.HexColor("#5B6B82")
PALE = colors.HexColor("#EAF6FD")
LINE = colors.HexColor("#CFE6F5")
GOOD = colors.HexColor("#15803D")
WARN = colors.HexColor("#B45309")
BAD = colors.HexColor("#B91C1C")
SERIES = [colors.HexColor(c) for c in ("#0194E2", "#14B8A6", "#F59E0B", "#8B5CF6", "#EF4444", "#64748B")]

_ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=_ss["Heading1"], fontName="Helvetica-Bold", fontSize=17, leading=21, textColor=NAVY, spaceAfter=4)
H2 = ParagraphStyle("h2", parent=_ss["Heading2"], fontName="Helvetica-Bold", fontSize=12.5, leading=16, textColor=BLUE_DEEP, spaceBefore=10, spaceAfter=6)
BODY = ParagraphStyle("body", parent=_ss["BodyText"], fontName="Helvetica", fontSize=9.2, leading=12.6, textColor=NAVY, alignment=TA_LEFT)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=7.8, leading=10.2, textColor=MUTED)
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8, leading=10)
CELL_B = ParagraphStyle("cellb", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)


def _esc(x) -> str:
    return "" if x is None else str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _pct(x, digits=0) -> str:
    if x is None:
        return "–"
    return f"{round(x * 100, digits) if x <= 1.0001 else round(x, digits):g}%"


def _fmt(v) -> str:
    if v is None or v == "":
        return "–"
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".")
    if isinstance(v, str) and len(v) == 20 and v.endswith("Z") and "T" in v:
        return v[:10] + " " + v[11:16]
    return str(v)


# ---------------------------------------------------------------------------------------------- page frame

def _frame(title: str, subtitle: str):
    def draw(canvas, doc):
        w, h = doc.pagesize
        canvas.saveState()
        canvas.setFillColor(BLUE)
        canvas.rect(0, h - 22 * mm, w, 22 * mm, stroke=0, fill=1)
        canvas.setFillColor(BLUE_DEEP)
        canvas.rect(0, h - 22 * mm, 6 * mm, 22 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica-Bold", 15)
        canvas.drawString(14 * mm, h - 12 * mm, "NEXUS")
        canvas.setFont("Helvetica", 9)
        canvas.drawString(14 * mm, h - 17.5 * mm, "Study from your own materials")
        canvas.setFont("Helvetica-Bold", 11)
        canvas.drawRightString(w - 12 * mm, h - 11.5 * mm, title[:80])
        canvas.setFont("Helvetica", 8.5)
        canvas.drawRightString(w - 12 * mm, h - 17 * mm, subtitle[:110])
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.6)
        canvas.line(12 * mm, 12 * mm, w - 12 * mm, 12 * mm)
        canvas.setFillColor(MUTED)
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(12 * mm, 8 * mm, "Every figure comes from your own answers. Ability and confidence use a Bayesian IRT model (3PL, Normal prior).")
        canvas.drawRightString(w - 12 * mm, 8 * mm, f"Page {doc.page}")
        canvas.restoreState()
    return draw


def _doc(buf, title: str, *, wide: bool = False) -> SimpleDocTemplate:
    size = landscape(A4) if wide else A4
    return SimpleDocTemplate(buf, pagesize=size, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=28 * mm, bottomMargin=17 * mm,
                             title=title, author="", subject="", creator="Nexus", producer="Nexus")


# ---------------------------------------------------------------------------------------------- building blocks

def kpi_row(items: list[tuple[str, str, str | None]], width: float) -> Table:
    """items: (label, value, note). A row of bordered tiles."""
    cells = []
    for label, value, note in items:
        cells.append([Paragraph(f"<font size=7.5 color='#5B6B82'>{_esc(label).upper()}</font>", BODY),
                      Paragraph(f"<font size=16><b>{_esc(value)}</b></font>", BODY),
                      Paragraph(f"<font size=7.5 color='#5B6B82'>{_esc(note or '')}</font>", BODY)])
    n = max(1, len(cells))
    t = Table([[c for c in cells]], colWidths=[width / n] * n)
    t.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 0.6, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.6, LINE),
                           ("BACKGROUND", (0, 0), (-1, -1), PALE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("LEFTPADDING", (0, 0), (-1, -1), 7)]))
    return t


def data_table(columns: list[tuple[str, str]], rows: list[dict], width: float, *, widths: list[float] | None = None, max_rows: int = 400) -> Table:
    head = [Paragraph(_esc(label), CELL_B) for _, label in columns]
    body = [[Paragraph(_esc(_fmt(r.get(k))), CELL) for k, _ in columns] for r in rows[:max_rows]]
    if not body:
        body = [[Paragraph("No rows yet.", CELL)] + [""] * (len(columns) - 1)]
    if widths is None:
        weights = [3.2 if k in ("question", "topic", "title", "path") else 2 if k in ("subject", "model", "finished_at", "created_at", "started_at") else 1.2 for k, _ in columns]
        total = sum(weights)
        widths = [width * w / total for w in weights]
    t = Table([head] + body, colWidths=widths, repeatRows=1)
    style = [("BACKGROUND", (0, 0), (-1, 0), BLUE), ("BOX", (0, 0), (-1, -1), 0.6, LINE), ("INNERGRID", (0, 0), (-1, -1), 0.3, LINE),
             ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    for i in range(1, len(body) + 1):
        if i % 2 == 0:
            style.append(("BACKGROUND", (0, i), (-1, i), PALE))
    t.setStyle(TableStyle(style))
    return t


def line_chart(points: list[tuple[float, float]], width: float, height: float = 58 * mm, *, y_label: str = "", y_min=None, y_max=None,
               x_labels: list[str] | None = None) -> Drawing:
    d = Drawing(width, height)
    if len(points) < 2:
        d.add(String(width / 2, height / 2, "Not enough data for a trend yet", fontName="Helvetica", fontSize=8, fillColor=MUTED, textAnchor="middle"))
        return d
    lp = LinePlot()
    lp.x, lp.y, lp.width, lp.height = 34, 22, width - 50, height - 34
    lp.data = [points]
    lp.lines[0].strokeColor = BLUE
    lp.lines[0].strokeWidth = 1.8
    from reportlab.graphics.widgets.markers import makeMarker
    lp.lines[0].symbol = makeMarker("FilledCircle", size=3.2, fillColor=BLUE, strokeColor=colors.white)
    ys = [p[1] for p in points]
    lp.yValueAxis.valueMin = min(ys) - 0.1 if y_min is None else y_min
    lp.yValueAxis.valueMax = max(ys) + 0.1 if y_max is None else y_max
    lp.xValueAxis.valueMin, lp.xValueAxis.valueMax = points[0][0], points[-1][0]
    lp.xValueAxis.labels.fontSize = lp.yValueAxis.labels.fontSize = 7
    lp.xValueAxis.labels.fontName = lp.yValueAxis.labels.fontName = "Helvetica"
    lp.xValueAxis.labels.fillColor = lp.yValueAxis.labels.fillColor = MUTED
    lp.yValueAxis.gridStrokeColor = LINE
    lp.yValueAxis.visibleGrid = True
    lp.xValueAxis.strokeColor = lp.yValueAxis.strokeColor = LINE
    if x_labels:
        lp.xValueAxis.valueSteps = [p[0] for p in points]
        lp.xValueAxis.labelTextFormat = lambda v: x_labels[min(len(x_labels) - 1, max(0, int(round(v)) - int(points[0][0])))]
    d.add(lp)
    if y_label:
        d.add(String(2, height - 8, y_label, fontName="Helvetica", fontSize=7, fillColor=MUTED))
    return d


def hbar_chart(labels: list[str], values: list[float], width: float, *, target: float | None = None, max_value: float = 100) -> Drawing:
    n = max(1, len(labels))
    height = 14 + n * 13
    d = Drawing(width, height)
    if not labels:
        return d
    bc = HorizontalBarChart()
    left = min(150, width * 0.38)
    bc.x, bc.y, bc.width, bc.height = left, 8, width - left - 12, height - 14
    bc.data = [values[::-1]]
    bc.categoryAxis.categoryNames = [lbl[:34] for lbl in labels[::-1]]
    bc.categoryAxis.labels.fontSize = 7
    bc.categoryAxis.labels.fillColor = NAVY
    bc.categoryAxis.strokeColor = LINE
    bc.valueAxis.valueMin, bc.valueAxis.valueMax = 0, max_value
    bc.valueAxis.labels.fontSize = 6.5
    bc.valueAxis.labels.fillColor = MUTED
    bc.valueAxis.strokeColor = LINE
    bc.valueAxis.visibleGrid = True
    bc.valueAxis.gridStrokeColor = LINE
    bc.bars.strokeColor = None
    bc.barWidth = 7
    for i, v in enumerate(values[::-1]):
        bc.bars[(0, i)].fillColor = GOOD if target is not None and v >= target else WARN if target is not None and v >= target * 0.6 else (BAD if target is not None else BLUE)
    d.add(bc)
    if target is not None:
        x = bc.x + bc.width * target / max_value
        d.add(Line(x, bc.y, x, bc.y + bc.height, strokeColor=NAVY, strokeWidth=0.8, strokeDashArray=[2, 2]))
        d.add(String(x + 2, bc.y + bc.height + 1, f"target {round(target)}", fontName="Helvetica", fontSize=6.5, fillColor=NAVY))
    return d


def vbar_chart(labels: list[str], series: list[list[float]], names: list[str], width: float, height: float = 55 * mm) -> Drawing:
    d = Drawing(width, height)
    if not labels or not any(any(s) for s in series):
        d.add(String(width / 2, height / 2, "No activity in this period", fontName="Helvetica", fontSize=8, fillColor=MUTED, textAnchor="middle"))
        return d
    bc = VerticalBarChart()
    bc.x, bc.y, bc.width, bc.height = 30, 22, width - 40, height - 40
    bc.data = series
    bc.categoryAxis.categoryNames = labels
    bc.categoryAxis.labels.fontSize = 6
    bc.categoryAxis.labels.angle = 45 if len(labels) > 12 else 0
    bc.categoryAxis.labels.boxAnchor = "ne" if len(labels) > 12 else "n"
    bc.categoryAxis.labels.fillColor = MUTED
    bc.valueAxis.labels.fontSize = 6.5
    bc.valueAxis.labels.fillColor = MUTED
    bc.valueAxis.valueMin = 0
    bc.valueAxis.visibleGrid = True
    bc.valueAxis.gridStrokeColor = LINE
    bc.categoryAxis.strokeColor = bc.valueAxis.strokeColor = LINE
    bc.bars.strokeColor = None
    bc.groupSpacing = 2
    for i in range(len(series)):
        bc.bars[i].fillColor = SERIES[i % len(SERIES)]
    d.add(bc)
    x = 30
    for i, nm in enumerate(names):
        d.add(Line(x, height - 8, x + 10, height - 8, strokeColor=SERIES[i % len(SERIES)], strokeWidth=5))
        d.add(String(x + 13, height - 10.5, nm, fontName="Helvetica", fontSize=7, fillColor=NAVY))
        x += 20 + 5 * len(nm)
    return d


def pie_chart(parts: list[tuple[str, float]], size: float = 48 * mm) -> Drawing:
    parts = [(k, v) for k, v in parts if v]
    d = Drawing(size * 2.2, size)
    if not parts:
        d.add(String(size, size / 2, "No data yet", fontName="Helvetica", fontSize=8, fillColor=MUTED, textAnchor="middle"))
        return d
    p = Pie()
    p.x, p.y, p.width, p.height = 6, 6, size - 12, size - 12
    p.data = [v for _, v in parts]
    p.labels = None
    p.slices.strokeColor = colors.white
    p.slices.strokeWidth = 1
    palette = {"on_track": GOOD, "minor": colors.HexColor("#84CC16"), "moderate": WARN, "critical": BAD, "unassessed": colors.HexColor("#CBD5E1")}
    for i, (k, _) in enumerate(parts):
        p.slices[i].fillColor = palette.get(k, SERIES[i % len(SERIES)])
    d.add(p)
    y = size - 12
    total = sum(v for _, v in parts)
    for i, (k, v) in enumerate(parts):
        d.add(Line(size + 4, y + 3, size + 12, y + 3, strokeColor=palette.get(k, SERIES[i % len(SERIES)]), strokeWidth=6))
        d.add(String(size + 16, y, f"{k.replace('_', ' ')}  {int(v)} ({round(100 * v / total)}%)", fontName="Helvetica", fontSize=7.5, fillColor=NAVY))
        y -= 12
    return d


def _build(title: str, subtitle: str, story: list, *, wide: bool = False) -> bytes:
    buf = io.BytesIO()
    doc = _doc(buf, title, wide=wide)
    frame = _frame(title, subtitle)
    doc.build(story, onFirstPage=frame, onLaterPages=frame)
    return buf.getvalue()


# ---------------------------------------------------------------------------------------------- reports

LABELS = {"confident": "Strong", "building": "Getting there", "shaky": "Needs work", "few": "Few answers", "untried": "Not tried"}


def subject_report(data: dict, *, agents: dict | None = None, twin: dict | None = None) -> bytes:
    """The subject report: summary, ability trend, per-topic confidence, quiz history, recommendations, agent findings."""
    width = A4[0] - 24 * mm
    o = data.get("overall")
    story = [Paragraph(f"{_esc(data['subject'])}: learning report", H1),
             Paragraph(f"Generated {_esc(_fmt(data['generated_at']))} UTC", SMALL), Spacer(1, 6)]
    story.append(kpi_row([
        ("Ability θ", f"{o['theta']:+.2f}" if o else "–", f"± {o['se']:.2f}" if o else "no answers yet"),
        ("Confidence", _pct(o["confidence"]) if o else "–", "chance ability is above the proficient line"),
        ("Answered", str(o["answered"]) if o else "0", f"{o['correct']} correct" if o else ""),
        ("Quizzes", str(len(data.get("attempts", []))), f"{data.get('wrong_questions', 0)} questions still wrong"),
    ], width))
    story.append(Paragraph("Ability over time", H2))
    trend = data.get("ability_trend", [])
    story.append(line_chart([(i + 1, t["theta"]) for i, t in enumerate(trend)], width, y_label="θ (logits)", x_labels=[f"#{t['attempt_id']}" for t in trend]))
    topics = [t for t in data.get("topics", []) if t.get("confidence") is not None]
    if topics:
        story.append(Paragraph("Confidence by topic", H2))
        target = round(100 * (twin or {}).get("target", 0.7)) if twin else 70
        story.append(hbar_chart([t["name"] for t in topics[:28]], [round(100 * t["confidence"]) for t in topics[:28]], width, target=target))
    story.append(Paragraph("Topics", H2))
    rows = [{"name": t["name"], "answered": t["answered"], "correct": t["correct"], "confidence": _pct(t["confidence"]) if t.get("confidence") is not None else None,
             "theta": t.get("theta"), "level": LABELS.get(t["label"], t["label"]), "avg_seconds": t.get("avg_seconds")} for t in data.get("topics", [])]
    story.append(data_table([("name", "Topic"), ("answered", "Answered"), ("correct", "Correct"), ("confidence", "Confidence"), ("theta", "θ"),
                             ("level", "Level"), ("avg_seconds", "Avg s")], rows, width, widths=[width * 0.36] + [width * 0.64 / 6] * 6))
    if data.get("recommendations"):
        story.append(Paragraph("Recommendations", H2))
        for r in data["recommendations"]:
            story.append(Paragraph(f"• {_esc(r)}", BODY))
    if agents and agents.get("steps"):
        story.append(Paragraph("What the agents found", H2))
        story.append(data_table([("name", "Agent"), ("summary", "Finding")], [{"name": s["name"], "summary": s["summary"]} for s in agents["steps"]], width,
                                widths=[width * 0.16, width * 0.84]))
        roots = next((s["details"].get("root_causes") for s in agents["steps"] if s["agent"] == "evaluator"), None)
        if roots:
            story.append(Spacer(1, 6))
            story.append(data_table([("topic", "Root cause"), ("missed", "Misses explained"), ("explains", "Explains")],
                                    [{"topic": r["topic"], "missed": r["missed"], "explains": ", ".join(r["explains"])} for r in roots], width,
                                    widths=[width * 0.3, width * 0.15, width * 0.55]))
    if data.get("attempts"):
        story.append(Paragraph("Quiz history", H2))
        story.append(data_table([("id", "Quiz"), ("finished_at", "Finished"), ("mode", "Mode"), ("kind", "Kind"), ("correct", "Correct"), ("answered", "Answered"),
                                 ("ended_reason", "Ended early")], data["attempts"], width))
    if data.get("backtracking"):
        story.append(Paragraph("Backtracking (questions asked from foundations after a miss)", H2))
        story.append(data_table([("topic", "Foundation topic"), ("asked", "Asked"), ("correct", "Correct")], data["backtracking"], width))
    story.append(Spacer(1, 8))
    story.append(Paragraph(_esc(data.get("method", "")), SMALL))
    return _build(f"{data['subject']} report", "Subject learning report", story)


def analytics_report(ov: dict, attempts: list[dict], topics: list[dict]) -> bytes:
    """The cross-subject analytics report (landscape): KPIs, activity, subjects, weakest topics, recent quizzes."""
    width = landscape(A4)[0] - 24 * mm
    k = ov["kpis"]
    story = [Paragraph("Learning analytics", H1), Paragraph(f"Last {ov['days']} days · generated {_esc(_fmt(ov['generated_at']))} UTC", SMALL), Spacer(1, 6)]
    story.append(kpi_row([
        ("Subjects", str(k["subjects"]), f"{k['materials']} materials, {k['topics']} topics"),
        ("Answers", str(k["answered"]), f"accuracy {_fmt(k['accuracy'])}%" if k["accuracy"] is not None else "no answers yet"),
        ("Quizzes", str(k["quizzes"]), f"{k['active_days']} active days in window"),
        ("Mean ability θ", f"{k['mean_theta']:+.2f}" if k["mean_theta"] is not None else "–", "across subjects"),
        ("Readiness", f"{_fmt(k['readiness'])}%" if k["readiness"] is not None else "–", "average of subjects"),
        ("Learning debt", f"{_fmt(k['debt_hours'])} h", "study time owed below target"),
    ], width))
    story.append(Paragraph("Daily activity", H2))
    tl = ov["timeline"][-31:]
    story.append(vbar_chart([t["date"][5:] for t in tl], [[t["answered"] for t in tl], [t["correct"] for t in tl], [t["asked"] for t in tl]],
                            ["answered", "correct", "questions asked"], width))
    if ov["subjects"]:
        story.append(Paragraph("Subjects", H2))
        story.append(data_table([("name", "Subject"), ("materials", "Materials"), ("topics", "Topics"), ("quizzes", "Quizzes"), ("answered", "Answered"),
                                 ("accuracy", "Accuracy %"), ("theta", "θ"), ("confidence", "Confidence %"), ("readiness", "Readiness %"), ("risk", "Risk"),
                                 ("risk_level", "Risk level"), ("debt_hours", "Debt h")], ov["subjects"], width))
    status = ov.get("topic_status") or {}
    weak = sorted([t for t in topics if t["confidence"] is not None], key=lambda t: t["confidence"])[:15]
    story.append(PageBreak())
    story.append(Paragraph("Topic status and weakest topics", H2))
    pie = pie_chart([(s, status.get(s, 0)) for s in ("on_track", "minor", "moderate", "critical", "unassessed")])
    bars = hbar_chart([f"{t['topic']} ({t['subject']})" for t in weak], [t["confidence"] for t in weak], width - pie.width - 10, target=70)
    story.append(Table([[pie, bars]], colWidths=[pie.width + 10, width - pie.width - 10], style=[("VALIGN", (0, 0), (-1, -1), "TOP")]))
    diff = ov["difficulty"]
    story.append(Paragraph("Accuracy by question difficulty and response time", H2))
    story.append(Table([[data_table([("level", "Difficulty"), ("answered", "Answered"), ("correct", "Correct"), ("accuracy", "Accuracy %")], diff, width / 2 - 6),
                         data_table([("bucket", "Response time"), ("count", "Answers"), ("accuracy", "Accuracy %")], ov["response_time"], width / 2 - 6)]],
                       colWidths=[width / 2, width / 2], style=[("VALIGN", (0, 0), (-1, -1), "TOP")]))
    if attempts:
        story.append(Paragraph("Recent quizzes", H2))
        from .analytics import COLUMNS
        story.append(data_table(COLUMNS["attempts"], attempts[:40], width))
    return _build("Learning analytics", f"Last {ov['days']} days", story, wide=True)


def table_pdf(title: str, columns: list[tuple[str, str]], rows: list[dict]) -> bytes:
    width = landscape(A4)[0] - 24 * mm
    story = [Paragraph(_esc(title), H1), Paragraph(f"{len(rows)} rows · exported {time.strftime('%Y-%m-%d %H:%M')} UTC", SMALL), Spacer(1, 6),
             data_table(columns, rows, width, max_rows=2000)]
    return _build(title, "Data export", story, wide=True)


def attempt_report(subject: str, result: dict) -> bytes:
    """One quiz: score, focus events, diagnosis and every answer with the explanation."""
    width = A4[0] - 24 * mm
    a = result["attempt"]
    pct = round(100 * a["correct"] / a["answered"]) if a["answered"] else 0
    fe = result.get("focus_events", {})
    story = [Paragraph(f"Quiz #{a['id']} · {_esc(subject)}", H1), Paragraph(f"{a['mode'].title()} · finished {_esc(_fmt(a['finished_at']))} UTC", SMALL), Spacer(1, 6),
             kpi_row([("Score", f"{pct}%", f"{a['correct']} of {a['answered']} correct"), ("Skipped", str(result.get("skipped", 0)), None),
                      ("Focus events", str(sum(fe.values())), ", ".join(f"{k.replace('_', ' ')} {v}" for k, v in fe.items() if v) or "none"),
                      ("Ended", "early" if result.get("ended_reason") else "normally", _esc(result.get("ended_reason") or ""))], width)]
    dg = result.get("diagnosis")
    if dg:
        story.append(Paragraph("Diagnosis", H2))
        story.append(Paragraph(f"Ability θ {dg['theta']:+.2f}, confidence {_pct(dg['confidence'])}. " + _esc(dg.get("note") or ""), BODY))
    story.append(Paragraph("Answers", H2))
    for i, x in enumerate(result.get("answers", []), start=1):
        mark = "<font color='#15803D'><b>Correct</b></font>" if x["correct"] else "<font color='#B91C1C'><b>Wrong</b></font>"
        opts = "<br/>".join(("<b>" if j == x["answer_index"] else "") + f"{chr(65 + j)}. {_esc(o)}" + ("</b>" if j == x["answer_index"] else "")
                            + ("  ← your answer" if j == x["chosen_index"] and not x["correct"] else "") for j, o in enumerate(x["options"]))
        block = [Paragraph(f"{i}. {_esc(x['question'])}  {mark}", BODY), Paragraph(f"<font color='#5B6B82'>{_esc(x['topic'])}</font>", SMALL),
                 Paragraph(opts, CELL)]
        if x.get("explanation"):
            block.append(Paragraph(f"<i>{_esc(x['explanation'])}</i>", SMALL))
        block.append(Spacer(1, 6))
        story.append(KeepTogether(block))
    return _build(f"Quiz #{a['id']}", subject, story)


# ---------------------------------------------------------------------------------------------- spreadsheets

def table_csv(columns: list[tuple[str, str]], rows: Iterable[dict]) -> str:
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow([label for _, label in columns])
    for r in rows:
        w.writerow(["" if r.get(k) is None else r.get(k) for k, _ in columns])
    return "﻿" + out.getvalue()                  # BOM: Excel opens UTF-8 correctly


def workbook(sheets: list[tuple[str, list[tuple[str, str]], list[dict]]]) -> bytes:
    """An .xlsx with one formatted sheet per (name, columns, rows): bold blue header, frozen header row, filters, sized columns."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    wb.remove(wb.active)
    thin = Side(style="thin", color="CFE6F5")
    for name, columns, rows in sheets:
        ws = wb.create_sheet(name[:31])
        ws.append([label for _, label in columns])
        for c in ws[1]:
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="0194E2")
            c.alignment = Alignment(vertical="center")
            c.border = Border(bottom=thin)
        for r in rows:
            ws.append([r.get(k) for k, _ in columns])
        for i, (k, label) in enumerate(columns, start=1):
            longest = max([len(str(label))] + [len(str(r.get(k) or "")) for r in rows[:500]])
            ws.column_dimensions[get_column_letter(i)].width = min(60, max(9, longest + 2))
        ws.freeze_panes = "A2"
        if rows:
            ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{len(rows) + 1}"
    wb.properties.creator = "Nexus"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
