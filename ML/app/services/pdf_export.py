"""
Phase 5 — PDF Report Export
Generates a polished HTML-to-PDF report using reportlab
Falls back to HTML if reportlab is not available
"""

import os
import json
from typing import Dict, Any, List
from datetime import datetime


def _unique_insights(insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    unique = []
    for item in insights:
        key = (
            str(item.get("title", "")).strip(),
            str(item.get("category", "")).strip(),
            str(item.get("file_path", "")).strip(),
            str(item.get("severity", "")).strip(),
        )
        if key not in seen:
            seen.add(key)
            unique.append(item)
    return unique


def generate_pdf(report: Dict[str, Any], output_path: str) -> str:
    """
    Generate a PDF report. Returns the path to the generated file.
    Uses reportlab if available, otherwise generates styled HTML.
    """
    try:
        from reportlab.lib.pagesizes import A4  # type: ignore
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
        from reportlab.lib.units import cm  # type: ignore
        from reportlab.lib import colors  # type: ignore
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,  # type: ignore
                                         Table, TableStyle, HRFlowable)
        from reportlab.lib.enums import TA_CENTER, TA_LEFT  # type: ignore

        _generate_with_reportlab(report, output_path)
    except ImportError:
        # Fallback: HTML
        output_path = output_path.replace(".pdf", ".html")
        _generate_html_report(report, output_path)
    return output_path


def _generate_with_reportlab(report: Dict[str, Any], path: str):
    from reportlab.lib.pagesizes import A4  # type: ignore
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle  # type: ignore
    from reportlab.lib.units import cm  # type: ignore
    from reportlab.lib import colors  # type: ignore
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,  # type: ignore
                                     Table, TableStyle, HRFlowable)
    from reportlab.lib.enums import TA_CENTER  # type: ignore

    PURPLE = colors.HexColor("#6c63ff")
    DARK   = colors.HexColor("#0d1117")
    GRAY   = colors.HexColor("#7c8fa6")
    GREEN  = colors.HexColor("#22d3a0")
    RED    = colors.HexColor("#ff4d6a")

    doc = SimpleDocTemplate(path, pagesize=A4,
                             leftMargin=2*cm, rightMargin=2*cm,
                             topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle("title", parent=styles["Title"],
                                  fontSize=24, textColor=PURPLE, spaceAfter=6)
    h2_style    = ParagraphStyle("h2", parent=styles["Heading2"],
                                  fontSize=14, textColor=DARK, spaceBefore=12, spaceAfter=4)
    body_style  = ParagraphStyle("body", parent=styles["Normal"],
                                  fontSize=10, textColor=GRAY, spaceAfter=4)

    # Header
    story.append(Paragraph("DevTrace Analysis Report", title_style))
    story.append(Paragraph(f"Repository: <b>{report.get('repo_name','')}</b>", body_style))
    story.append(Paragraph(f"Analyzed: {report.get('analyzed_at','')[:19].replace('T',' ')}", body_style))
    story.append(Paragraph(f"Commit: {report.get('commit_sha','N/A')}", body_style))
    story.append(HRFlowable(width="100%", color=PURPLE, spaceAfter=12))

    # Core metrics table
    story.append(Paragraph("Core Metrics", h2_style))
    metrics_data = [
        ["Metric", "Value", "Status"],
        ["Quality Score", str(_v(report, "quality_score")), _v(report, "quality_score", "status")],
        ["Security Risks", str(_v(report, "security_risks")), _v(report, "security_risks", "status")],
        ["Maintainability", str(_v(report, "maintainability")), "Stable"],
        ["Tech Debt", str(_v(report, "estimated_tech_debt_hours")), ""],
        ["Total Files", str(report.get("total_files_analyzed", 0)), ""],
        ["Lines of Code", f"{report.get('total_lines_of_code', 0):,}", ""],
        ["Vulnerable Deps", str(report.get("vulnerable_dependencies", 0)), ""],
    ]
    t = Table(metrics_data, colWidths=[6*cm, 4*cm, 4*cm])
    t.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), PURPLE),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#e0e0e0")),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("RIGHTPADDING",(0,0), (-1,-1), 8),
        ("TOPPADDING",  (0,0), (-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
    ]))
    story.append(t)
    story.append(Spacer(1, 0.5*cm))

    story.append(Paragraph("Executive Summary", h2_style))
    story.append(Paragraph(report.get("executive_summary", "No executive summary available."), body_style))
    roadmap = report.get("recommended_roadmap", [])
    if roadmap:
        story.append(Paragraph("Recommended Roadmap", body_style))
        for item in roadmap:
            story.append(Paragraph(f"• {item}", body_style))
    story.append(Spacer(1, 0.4*cm))

    # AI suggestion highlights
    all_insights = _unique_insights(report.get("actionable_insights", []))
    ai_suggestions = [i for i in all_insights if i.get("ai_fix_available")]
    if ai_suggestions:
        story.append(Paragraph("Top AI Suggestions", h2_style))
        ai_title_style = ParagraphStyle("aititle", parent=styles["Heading3"], fontSize=11, textColor=PURPLE, spaceAfter=2)
        ai_body_style = ParagraphStyle("aibody", parent=styles["BodyText"], fontSize=9, textColor=GRAY, leftIndent=12, spaceAfter=6)
        for ins in ai_suggestions[:5]:
            story.append(Paragraph(f"• {ins.get('title','No title')}", ai_title_style))
            fix_text = ins.get('suggested_fix') or ins.get('description', '')
            story.append(Paragraph(fix_text, ai_body_style))
        story.append(Spacer(1, 0.5*cm))

    # Top insights
    story.append(Paragraph("Top Actionable Insights", h2_style))
    insights = all_insights[:10]
    if insights:
        ins_data = [["Severity", "Category", "Title", "File"]]
        for ins in insights:
            ins_data.append([
                ins.get("severity",""),
                ins.get("category",""),
                ins.get("title","")[:50],
                ins.get("file_path","")[:30],
            ])
        ti = Table(ins_data, colWidths=[2.5*cm, 3*cm, 7*cm, 4*cm])
        sev_colors = {"HIGH": RED, "MEDIUM": colors.HexColor("#fbbf24"), "LOW": colors.HexColor("#38bdf8")}
        style_cmds = [
            ("BACKGROUND",  (0,0), (-1,0), PURPLE),
            ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
            ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE",    (0,0), (-1,-1), 8),
            ("GRID",        (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0e0")),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING",  (0,0), (-1,-1), 4),
            ("BOTTOMPADDING",(0,0),(-1,-1), 4),
        ]
        for i, ins in enumerate(insights, 1):
            c = sev_colors.get(ins.get("severity",""), GRAY)
            style_cmds.append(("TEXTCOLOR", (0,i), (0,i), c))
            style_cmds.append(("FONTNAME",  (0,i), (0,i), "Helvetica-Bold"))
        ti.setStyle(TableStyle(style_cmds))
        story.append(ti)

    story.append(Spacer(1, 0.5*cm))

    # Architecture summary
    arch = report.get("architecture", {})
    if arch:
        story.append(Paragraph("Architecture", h2_style))
        story.append(Paragraph(arch.get("summary",""), body_style))
        arch_data = [
            ["Domain-Driven Score", f"{arch.get('domain_driven_score',0)}%"],
            ["Circular Dependencies", str(len(arch.get("circular_dependencies",[])))],
            ["Total Modules", str(arch.get("total_modules",0))],
            ["Coupling Score", f"{arch.get('coupling_score',0)}%"],
            ["Cohesion Score", f"{arch.get('cohesion_score',0)}%"],
        ]
        ta = Table(arch_data, colWidths=[7*cm, 4*cm])
        ta.setStyle(TableStyle([
            ("FONTSIZE", (0,0), (-1,-1), 9),
            ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#e0e0e0")),
            ("LEFTPADDING", (0,0), (-1,-1), 8),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(ta)

    lang = report.get("language_breakdown", {})
    if lang:
        story.append(Paragraph("Language Breakdown", h2_style))
        lang_items = [["Language", "Percent"]]
        for name, pct in sorted(lang.items(), key=lambda item: item[1], reverse=True):
            lang_items.append([name, f"{pct:.1f}%"])
        lang_table = Table(lang_items, colWidths=[7*cm, 4*cm])
        lang_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), PURPLE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.2, colors.HexColor("#e0e0e0")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(lang_table)
        story.append(Spacer(1, 0.3*cm))

    halstead = report.get("halstead_metrics", {})
    if halstead:
        story.append(Paragraph("Halstead Metrics", h2_style))
        hald_items = [["Metric", "Value"]]
        for key, value in sorted(halstead.items()):
            hald_items.append([key.replace("_"," ").title(), str(value)])
        hald_table = Table(hald_items, colWidths=[7*cm, 4*cm])
        hald_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), PURPLE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.2, colors.HexColor("#e0e0e0")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(hald_table)
        story.append(Spacer(1, 0.3*cm))

    coverage = report.get("test_coverage", {})
    if coverage:
        story.append(Paragraph("Test Coverage", h2_style))
        cov_items = [["Metric", "Value"]]
        for key in ["overall", "lines_tested", "lines_untested", "tests", "frameworks"]:
            if key in coverage:
                cov_items.append([key.replace("_"," ").title(), str(coverage.get(key))])
        cov_table = Table(cov_items, colWidths=[7*cm, 4*cm])
        cov_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), PURPLE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.2, colors.HexColor("#e0e0e0")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(cov_table)
        story.append(Spacer(1, 0.3*cm))

    ml_summary = report.get("ml_summary", {})
    if ml_summary or report.get("models_used"):
        story.append(Paragraph("ML Engine Summary", h2_style))
        for key, value in ml_summary.items():
            story.append(Paragraph(f"{key.replace('_',' ').title()}: {value}", body_style))
        if report.get("models_used"):
            story.append(Paragraph(f"Models Used: {', '.join(report.get('models_used', []))}", body_style))
        story.append(Spacer(1, 0.3*cm))

    js_issues = report.get("js_issues", [])
    if js_issues:
        story.append(Paragraph("JavaScript / TypeScript Issues", h2_style))
        js_items = [["Severity", "Title", "File"]]
        for issue in js_issues[:8]:
            js_items.append([issue.get("severity",""), issue.get("title", issue.get("description",""))[:50], issue.get("file_path","")[:30]])
        js_table = Table(js_items, colWidths=[3*cm, 7*cm, 5*cm])
        js_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), PURPLE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.2, colors.HexColor("#e0e0e0")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(js_table)
        story.append(Spacer(1, 0.3*cm))

    module_graph = report.get("module_graph", {})
    if module_graph:
        story.append(Paragraph("Module Graph Summary", h2_style))
        story.append(Paragraph(f"Nodes: {len(module_graph.get('nodes', []))} · Edges: {len(module_graph.get('edges', []))}", body_style))
        story.append(Spacer(1, 0.3*cm))

    author_stats = report.get("author_stats", [])
    if author_stats:
        story.append(Paragraph("Author Stats", h2_style))
        author_items = [["Author", "Contributions"]]
        for author in author_stats[:8]:
            author_items.append([author.get("name", author.get("author",""))[:30], str(author.get("commits", author.get("contributions","")))])
        author_table = Table(author_items, colWidths=[7*cm, 4*cm])
        author_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), PURPLE),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("GRID", (0,0), (-1,-1), 0.2, colors.HexColor("#e0e0e0")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
            ("LEFTPADDING", (0,0), (-1,-1), 6),
            ("TOPPADDING", (0,0), (-1,-1), 4),
            ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        story.append(author_table)
        story.append(Spacer(1, 0.3*cm))

    incremental = report.get("incremental_stats", {})
    if incremental:
        story.append(Paragraph("Incremental Analysis", h2_style))
        for key, value in incremental.items():
            story.append(Paragraph(f"{key.replace('_',' ').title()}: {value}", body_style))

    # Footer
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width="100%", color=PURPLE))
    story.append(Paragraph("Generated by DevTrace — AI Code Intelligence Platform", 
                             ParagraphStyle("footer", parent=styles["Normal"],
                                             fontSize=8, textColor=GRAY, alignment=TA_CENTER)))
    doc.build(story)


def _generate_html_report(report: Dict[str, Any], path: str):
    """Fallback styled HTML report."""
    quality = _v(report, "quality_score")
    security = _v(report, "security_risks")
    maint = _v(report, "maintainability")
    debt = _v(report, "estimated_tech_debt_hours")
    insights = _unique_insights(report.get("actionable_insights", []))[:20]
    arch = report.get("architecture", {})
    trend = report.get("code_health_trend", {})
    heatmap = sorted(report.get("complexity_heatmap", []), key=lambda x: x.get("score", 0), reverse=True)[:10]
    lang = report.get("language_breakdown", {})
    halstead = report.get("halstead_metrics", {})
    coverage = report.get("test_coverage", {})
    ml_summary = report.get("ml_summary", {})
    models_used = report.get("models_used", [])
    js_issues = report.get("js_issues", [])[:10]
    author_stats = report.get("author_stats", [])[:8]

    ins_rows = ""
    for i in insights:
        sev = i.get("severity", "")
        colors_map = {"HIGH": "#ff4d6a", "MEDIUM": "#fbbf24", "LOW": "#38bdf8"}
        c = colors_map.get(sev, "#888")
        ins_rows += f"""
        <tr>
          <td style=\"color:{c};font-weight:700\">{sev}</td>
          <td style=\"color:#94a3b8\">{i.get('category','')}</td>
          <td>{i.get('title','')}</td>
          <td style=\"color:#6b8099;font-size:11px\">{i.get('file_path','')}</td>
        </tr>"""

    heat_rows = ""
    for item in heatmap:
        heat_rows += f"""
        <tr>
          <td>{item.get('module','')}</td>
          <td>{item.get('score','')}</td>
          <td>{item.get('issues','')}</td>
        </tr>"""

    lang_rows = ""
    for name, pct in sorted(lang.items(), key=lambda item: item[1], reverse=True):
        lang_rows += f"<tr><td>{name}</td><td>{pct:.1f}%</td></tr>"

    hald_rows = ""
    for key, value in sorted(halstead.items()):
        hald_rows += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"

    cov_rows = ""
    for key in ["overall", "lines_tested", "lines_untested", "tests", "frameworks"]:
        if key in coverage:
            cov_rows += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{coverage.get(key)}</td></tr>"

    js_rows = ""
    for issue in js_issues:
        js_rows += f"""
        <tr>
          <td>{issue.get('severity','')}</td>
          <td>{issue.get('title', issue.get('description',''))}</td>
          <td>{issue.get('file_path','')}</td>
        </tr>"""

    author_rows = ""
    for author in author_stats:
        author_rows += f"<tr><td>{author.get('name', author.get('author',''))}</td><td>{author.get('commits', author.get('contributions',''))}</td></tr>"

    roadmap_html = ""
    for item in report.get("recommended_roadmap", []):
        roadmap_html += f"<li>{item}</li>"

    ml_html = ""
    for key, value in ml_summary.items():
        ml_html += f"<p><strong>{key.replace('_', ' ').title()}:</strong> {value}</p>"
    if models_used:
        ml_html += f"<p><strong>Models Used:</strong> {', '.join(models_used)}</p>"

    html = f"""<!DOCTYPE html>
<html><head><meta charset=\"UTF-8\"/>
<title>DevTrace Report — {report.get('repo_name','')}</title>
<style>
  body{{font-family:'Segoe UI',sans-serif;background:#f8fafc;color:#0f172a;margin:0;padding:0}}
  .page{{max-width:840px;margin:0 auto;background:#ffffff;box-shadow:0 30px 90px rgba(15,23,42,.12)}}
  .header{{background:linear-gradient(135deg,#6c63ff,#8b5cf6);color:#fff;padding:40px 48px;border-bottom:1px solid rgba(255,255,255,.18)}}
  .header h1{{font-size:34px;margin:0 0 10px;letter-spacing:-.03em}}
  .header p{{margin:4px 0 0;font-size:13px;opacity:.88}}
  .section{{padding:32px 48px}}
  h2{{color:#1e293b;font-size:18px;border-bottom:2px solid #eef2ff;padding-bottom:10px;margin-top:0}}
  .summary-grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-bottom:24px}}
  .card{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:14px;padding:18px}}
  .card-label{{font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}}
  .card-value{{font-size:24px;font-weight:700;color:#0f172a}}
  .table-wrap{{overflow-x:auto}}table{{width:100%;border-collapse:collapse;margin-bottom:24px;font-size:13px}}
  th,td{{padding:12px 14px;text-align:left;border-bottom:1px solid #e2e8f0}}
  th{{background:#6c63ff;color:#fff;font-size:12px;letter-spacing:.06em}}
  tr:nth-child(even){{background:#f8fafc}}
  tr:hover td{{background:#eef2ff}}
  ul{{margin:12px 0 24px 18px;color:#334155}}li{{margin-bottom:8px}}
  .small{{color:#475569;font-size:13px}}
  .footer{{padding:24px 48px 32px;color:#64748b;font-size:12px;text-align:center;border-top:1px solid #e2e8f0}}
</style></head><body>
<div class="page">
<div class="header">
  <h1>DevTrace Analysis Report</h1>
  <p><strong>{report.get('repo_name','')}</strong></p>
  <p>Analyzed: {str(report.get('analyzed_at',''))[:19].replace('T',' ')} UTC · Commit: {report.get('commit_sha','N/A')}</p>
  <p>{report.get('total_files_analyzed',0)} files · {report.get('total_lines_of_code',0):,} LOC · Source: {report.get('repo_source','remote').upper()}</p>
</div>
<div class="section">
  <h2>Executive Summary</h2>
  <p class="small">{report.get('executive_summary','No executive summary available.')}</p>
  {f'<h3>Recommended Roadmap</h3><ul>{roadmap_html}</ul>' if roadmap_html else ''}

  <h2>Core Metrics</h2>
  <div class="summary-grid">
    <div class="card"><div class="card-label">Quality Score</div><div class="card-value">{quality}</div></div>
    <div class="card"><div class="card-label">Security Risks</div><div class="card-value">{security}</div></div>
    <div class="card"><div class="card-label">Maintainability</div><div class="card-value">{maint}</div></div>
    <div class="card"><div class="card-label">Tech Debt</div><div class="card-value">{debt}</div></div>
    <div class="card"><div class="card-label">Vulnerable Deps</div><div class="card-value">{report.get('vulnerable_dependencies',0)}</div></div>
    <div class="card"><div class="card-label">Critical Issues</div><div class="card-value">{report.get('critical_issues_count',0)}</div></div>
  </div>

  <h2>Code Health Trend</h2>
  <div class="table-wrap"><table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>
    <tr><td>Cyclomatic Complexity</td><td>{trend.get('cyclomatic_complexity','')}</td></tr>
    <tr><td>Duplication Rate</td><td>{trend.get('duplication_rate','')}%</td></tr>
    <tr><td>Documentation Coverage</td><td>{trend.get('documentation_coverage','')}%</td></tr>
  </tbody></table></div>
  {f'<h3>Recent Commit Health</h3><div class="table-wrap"><table><thead><tr><th>Commit</th><th>Date</th><th>Note</th></tr></thead><tbody>' + ''.join([f"<tr><td>{c.get('commit','')}</td><td>{c.get('date','')}</td><td>{c.get('note','')}</td></tr>" for c in trend.get('commit_history',[])[:5]]) + '</tbody></table></div>' if trend.get('commit_history') else ''}

  <h2>Complexity Heatmap</h2>
  <div class="table-wrap"><table><thead><tr><th>Module</th><th>Score</th><th>Issues</th></tr></thead><tbody>{heat_rows}</tbody></table></div>

  <h2>Architecture</h2>
  <p class="small">{arch.get('summary','')}</p>
  <div class="table-wrap"><table><tbody>
    <tr><td>Domain-Driven Score</td><td>{arch.get('domain_driven_score',0)}%</td></tr>
    <tr><td>Circular Dependencies</td><td>{len(arch.get('circular_dependencies',[]))}</td></tr>
    <tr><td>Total Modules</td><td>{arch.get('total_modules',0)}</td></tr>
    <tr><td>Coupling Score</td><td>{arch.get('coupling_score',0)}%</td></tr>
    <tr><td>Cohesion Score</td><td>{arch.get('cohesion_score',0)}%</td></tr>
    <tr><td>Layer Violations</td><td>{len(arch.get('layer_violations',[]))}</td></tr>
    <tr><td>Orphan Modules</td><td>{len(arch.get('orphan_modules',[]))}</td></tr>
  </tbody></table></div>

  {f'<h2>Language Breakdown</h2><div class="table-wrap"><table><thead><tr><th>Language</th><th>Percent</th></tr></thead><tbody>{lang_rows}</tbody></table></div>' if lang_rows else ''}

  {f'<h2>Halstead Metrics</h2><div class="table-wrap"><table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>{hald_rows}</tbody></table></div>' if hald_rows else ''}

  {f'<h2>Test Coverage</h2><div class="table-wrap"><table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>{cov_rows}</tbody></table></div>' if cov_rows else ''}

  {f'<h2>ML Engine Summary</h2>{ml_html}' if ml_html else ''}

  {f'<h2>JavaScript / TypeScript Issues</h2><div class="table-wrap"><table><thead><tr><th>Severity</th><th>Issue</th><th>File</th></tr></thead><tbody>{js_rows}</tbody></table></div>' if js_rows else ''}

  {f'<h2>Top Actionable Insights</h2><div class="table-wrap"><table><thead><tr><th>Severity</th><th>Category</th><th>Issue</th><th>File</th></tr></thead><tbody>{ins_rows}</tbody></table></div>' if ins_rows else ''}

  {f'<h2>Module Graph Summary</h2><p class="small">Nodes: {len(report.get('module_graph',{{}}).get('nodes',[]))} · Edges: {len(report.get('module_graph',{{}}).get('edges',[]))}</p>' if report.get('module_graph') else ''}

  {f'<h2>Author Stats</h2><div class="table-wrap"><table><thead><tr><th>Author</th><th>Contributions</th></tr></thead><tbody>{author_rows}</tbody></table></div>' if author_rows else ''}

  {f'<h2>Incremental Analysis</h2>' + ''.join([f"<p class='small'><strong>{k.replace('_',' ').title()}:</strong> {v}</p>" for k, v in report.get('incremental_stats', {}).items()]) if report.get('incremental_stats') else ''}
</div>
<div class="footer">Generated by DevTrace — AI Code Intelligence Platform</div>
</div>
</body></html>"""
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)


def _v(report, key, sub="value"):
    v = report.get(key, {})
    if isinstance(v, dict):
        return v.get(sub, "—")
    return str(v)
