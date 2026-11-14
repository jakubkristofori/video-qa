from __future__ import annotations

import json
from html import escape
from pathlib import Path
from xml.etree import ElementTree as ET

from .models import FAIL, SKIP, WARN, Report

_COLORS = {"pass": "#1a7f37", "fail": "#cf222e", "warn": "#9a6700", "skip": "#6e7781"}


def write_json(report: Report, path: Path) -> None:
    path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")


def write_junit(report: Report, path: Path) -> None:
    """JUnit XML – GitHub Actions i další CI z něj umí zobrazit výsledky."""
    suite = ET.Element("testsuite", name=report.episode, tests=str(len(report.results)),
                       failures=str(len(report.failed)))
    for r in report.results:
        case = ET.SubElement(suite, "testcase", classname=report.episode, name=r.name)
        if r.status == FAIL:
            ET.SubElement(case, "failure", message=r.message).text = json.dumps(r.details, ensure_ascii=False)
        elif r.status == SKIP:
            ET.SubElement(case, "skipped", message=r.message)
    ET.ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)


def write_html(report: Report, path: Path) -> None:
    rows = "\n".join(
        f"<tr><td>{escape(r.name)}</td>"
        f"<td style='color:{_COLORS.get(r.status, '#000')};font-weight:600'>{r.status.upper()}</td>"
        f"<td>{escape(r.message)}</td></tr>"
        for r in report.results
    )
    verdict = "PASSED" if report.ok else "FAILED"
    color = _COLORS["pass" if report.ok else "fail"]
    path.write_text(f"""<!doctype html><meta charset="utf-8"><title>QA {escape(report.episode)}</title>
<style>body{{font:15px system-ui;margin:2rem auto;max-width:860px}}
table{{border-collapse:collapse;width:100%}}td,th{{border-bottom:1px solid #ddd;padding:6px 10px;text-align:left}}</style>
<h1>QA report: {escape(report.episode)} <span style="color:{color}">{verdict}</span></h1>
<table><tr><th>Kontrola</th><th>Stav</th><th>Detail</th></tr>
{rows}
</table>""", encoding="utf-8")


def console_summary(report: Report) -> str:
    lines = [f"QA: {report.episode}"]
    for r in report.results:
        mark = {"pass": "✓", "fail": "✗", "warn": "!", "skip": "-"}[r.status]
        lines.append(f"  {mark} {r.name:<22} {r.message}")
    s = report.to_dict()["summary"]
    lines.append(f"Výsledek: {'OK' if report.ok else 'SELHALO'} "
                 f"(pass {s['pass']}, fail {s['fail']}, warn {s[WARN]}, skip {s[SKIP]})")
    return "\n".join(lines)
