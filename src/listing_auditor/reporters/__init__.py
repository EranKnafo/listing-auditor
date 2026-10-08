"""Reporters turn an AuditResult into text. Each is a pure function: easy to test, easy to add."""
from __future__ import annotations

import csv
import io
import json

from ..models import AuditResult, Severity


def to_console(result: AuditResult, top: int = 10, min_severity: Severity = Severity.INFO) -> str:
    out = [
        f"Audited {len(result.reports)} listings · average score {result.average_score:.1f}/100",
        "Findings by severity: " + ", ".join(f"{k} {v}" for k, v in result.counts_by_severity().items()),
        "",
        "Most common issues:",
    ]
    out += [f"  {n:>4}  {code}" for code, n in list(result.counts_by_code().items())[:8]]
    out += ["", f"Lowest-scoring {top} listings:"]
    for r in sorted(result.reports, key=lambda r: r.score)[:top]:
        shown = [f for f in r.findings if f.severity >= min_severity]
        if not shown:
            continue
        out.append(f"  {r.score:>3}  {r.name} ({r.listing_id})")
        out += [f"         [{f.severity.name:<8}] {f.code}: {f.message}" for f in shown]
    return "\n".join(out)


def to_json(result: AuditResult) -> str:
    return json.dumps(
        {
            "average_score": round(result.average_score, 2),
            "by_severity": result.counts_by_severity(),
            "by_code": result.counts_by_code(),
            "listings": [
                {
                    "id": r.listing_id,
                    "name": r.name,
                    "score": r.score,
                    "findings": [
                        {
                            "check": f.check,
                            "code": f.code,
                            "severity": f.severity.name,
                            "message": f.message,
                            "fix": None
                            if f.patch is None
                            else {"field": f.patch.field, "from": f.patch.old, "to": f.patch.new, "auto": f.patch.safe},
                        }
                        for f in r.findings
                    ],
                }
                for r in result.reports
            ],
        },
        indent=2,
    )


def to_csv(result: AuditResult) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["listing_id", "listing", "score", "check", "code", "severity", "message", "auto_fixable"])
    for r in result.reports:
        for f in r.findings:
            w.writerow([r.listing_id, r.name, r.score, f.check, f.code, f.severity.name, f.message,
                        bool(f.patch and f.patch.safe)])
    return buf.getvalue()


def to_markdown(result: AuditResult, top: int = 10) -> str:
    out = [
        "# Listing audit summary", "",
        f"**{len(result.reports)}** listings · average score **{result.average_score:.1f}/100**", "",
        "| Severity | Findings |", "|---|---|",
    ]
    out += [f"| {k} | {v} |" for k, v in result.counts_by_severity().items()]
    out += ["", "## Most common issues", "", "| Code | Listings affected |", "|---|---|"]
    out += [f"| `{c}` | {n} |" for c, n in list(result.counts_by_code().items())[:10]]
    out += ["", f"## Lowest-scoring {top}", "", "| Score | Listing | Top issue |", "|---|---|---|"]
    for r in sorted(result.reports, key=lambda r: r.score)[:top]:
        top_issue = f"`{r.findings[0].code}`" if r.findings else "–"
        out.append(f"| {r.score} | {r.name} | {top_issue} |")
    return "\n".join(out) + "\n"


def to_slack_payload(result: AuditResult, top: int = 5) -> dict:
    """Build a Slack incoming-webhook payload. Posting it is left to the caller."""
    worst = sorted(result.reports, key=lambda r: r.score)[:top]
    lines = [f"• *{r.name}* — {r.score}/100 ({r.findings[0].code})" for r in worst if r.findings]
    return {
        "text": f"Listing audit: {len(result.reports)} listings, avg {result.average_score:.0f}/100",
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn",
             "text": f"*Listing audit* — {len(result.reports)} listings, average *{result.average_score:.0f}/100*"}},
            {"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(lines) or "No issues."}},
        ],
    }


FORMATS = {"console": to_console, "json": to_json, "csv": to_csv, "md": to_markdown}
