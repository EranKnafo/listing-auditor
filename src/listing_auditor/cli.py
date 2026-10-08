"""Command line: generate sample data, audit it, preview/apply safe fixes, and benchmark detection."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import load_config
from .engine import audit
from .models import Severity
from .patches import apply_patches, collect_patches, render_diff
from .reporters import FORMATS
from .sources import JsonFileSink, JsonFileSource
from .sources.synthetic import generate


def _cmd_generate(a: argparse.Namespace) -> int:
    rows, injected = generate(a.count, a.seed, a.defect_rate)
    Path(a.out).write_text(json.dumps(rows, indent=2) + "\n")
    if a.truth:
        Path(a.truth).write_text(json.dumps(injected, indent=2) + "\n")
    print(f"wrote {len(rows)} listings to {a.out} ({len(injected)} with planted defects)")
    return 0


def _cmd_audit(a: argparse.Namespace) -> int:
    rows = JsonFileSource(a.input).load()
    result = audit(rows, load_config(a.config), only=a.only)
    fmt = FORMATS[a.format]
    if a.format == "console":
        text = fmt(result, top=a.top, min_severity=Severity[a.min_severity])
    elif a.format == "md":
        text = fmt(result, top=a.top)
    else:
        text = fmt(result)
    if a.out:
        Path(a.out).write_text(text)
        print(f"wrote {a.format} report to {a.out}")
    else:
        print(text)
    if a.fail_under is not None and result.average_score < a.fail_under:
        print(f"average score {result.average_score:.1f} is below --fail-under {a.fail_under}", file=sys.stderr)
        return 1
    return 0


def _cmd_fix(a: argparse.Namespace) -> int:
    rows = JsonFileSource(a.input).load()
    config = load_config(a.config)
    result = audit(rows, config)
    safe = collect_patches(result)
    review = [p for p in collect_patches(result, include_unsafe=True) if not p.safe]
    outcome = apply_patches(rows, safe)
    print(render_diff(outcome.applied) or "no safe fixes to apply")
    if review:
        print(f"\n{len(review)} proposed change(s) need human review (not applied):")
        print(render_diff(review))
    if outcome.skipped_stale:
        print(f"\nskipped {len(outcome.skipped_stale)} stale patch(es)")
    if a.write:
        sink = JsonFileSink(outcome.rows, a.write)
        for p in outcome.applied:
            sink.update(p.listing_id, p.field, p.new)
        sink.commit()
        recheck = audit(outcome.rows, config)
        print(f"\nwrote {a.write}; re-audit average score {result.average_score:.1f} -> {recheck.average_score:.1f}")
    else:
        print("\n(dry run; pass --write PATH to save the fixed copy)")
    return 0


def _cmd_benchmark(a: argparse.Namespace) -> int:
    rows, injected = generate(a.count, a.seed, a.defect_rate)
    result = audit(rows, load_config(a.config))
    found = {r.listing_id: {f.code for f in r.findings} for r in result.reports}
    planted = sum(len(c) for c in injected.values())
    caught = sum(1 for lid, codes in injected.items() for c in codes if c in found[lid])
    clean = [lid for lid in found if lid not in injected]
    noisy = [lid for lid in clean if any(f.severity >= Severity.MEDIUM for f in next(r for r in result.reports if r.listing_id == lid).findings)]
    print(f"planted defects : {planted} across {len(injected)} listings")
    print(f"detected        : {caught} (recall {caught / planted:.1%})")
    print(f"clean listings  : {len(clean)}; flagged MEDIUM+ : {len(noisy)} (false-positive rate {len(noisy) / max(len(clean), 1):.1%})")
    return 0 if caught == planted and not noisy else 1


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="listing-auditor", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("generate", help="write a synthetic portfolio with planted defects")
    g.add_argument("--count", type=int, default=60)
    g.add_argument("--seed", type=int, default=7)
    g.add_argument("--defect-rate", type=float, default=0.5)
    g.add_argument("--out", default="data/sample_listings.json")
    g.add_argument("--truth", help="also write the planted-defect ground truth to this path")
    g.set_defaults(fn=_cmd_generate)

    r = sub.add_parser("audit", help="score listings and report findings")
    r.add_argument("input")
    r.add_argument("--config")
    r.add_argument("--only", nargs="+", help="run only these checks")
    r.add_argument("--format", choices=sorted(FORMATS), default="console")
    r.add_argument("--min-severity", choices=[s.name for s in Severity], default="LOW")
    r.add_argument("--top", type=int, default=10, help="how many lowest-scoring listings to show")
    r.add_argument("--out")
    r.add_argument("--fail-under", type=float, help="exit 1 if the average score is below this (for CI)")
    r.set_defaults(fn=_cmd_audit)

    f = sub.add_parser("fix", help="preview or apply safe auto-fixes; risky changes are only proposed")
    f.add_argument("input")
    f.add_argument("--config")
    f.add_argument("--write", help="write the fixed copy here (input is never modified)")
    f.set_defaults(fn=_cmd_fix)

    b = sub.add_parser("benchmark", help="measure detection recall on planted defects")
    b.add_argument("--count", type=int, default=200)
    b.add_argument("--seed", type=int, default=11)
    b.add_argument("--defect-rate", type=float, default=0.5)
    b.add_argument("--config")
    b.set_defaults(fn=_cmd_benchmark)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
