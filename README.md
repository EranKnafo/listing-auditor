# listing-auditor

A small, dependency-free Python engine that **scores rental listings 0–100, explains every deduction, and proposes fixes** — auto-applying only the ones that are provably low-risk.

It combines two kinds of checking:

- **Rules** for violations you can write down (missing license, minimum stay above maximum stay, phone number in a title, fees outside their band).
- **Robust statistics** for the ones you can't: a base price that is legal under every rule but 3× its comparable peers.

All data in this repo is synthetic. The included generator plants known defects, so detection quality is *measured*, not asserted.

```
$ listing-auditor benchmark
planted defects : 129 across 97 listings
detected        : 129 (recall 100.0%)
clean listings  : 103; flagged MEDIUM+ : 0 (false-positive rate 0.0%)
```

## Quick start

```bash
pip install -e ".[dev]"
listing-auditor generate --count 60 --seed 7 --out data/sample_listings.json
listing-auditor audit data/sample_listings.json --min-severity MEDIUM
listing-auditor fix data/sample_listings.json --write fixed.json   # dry run without --write
pytest -q                                                          # 42 tests
```

```
Audited 60 listings · average score 92.1/100
Findings by severity: CRITICAL 7, HIGH 10, MEDIUM 20, LOW 12, INFO 0

Lowest-scoring 3 listings:
   58  PNC-029 (lst_0029)
         [CRITICAL] MIN_GT_MAX: minimum stay (14) exceeds maximum stay (7)
         [MEDIUM  ] HERO_PHOTO_QUALITY: hero photo is 1080x1920; needs landscape and >= 1600px wide
         [MEDIUM  ] STAY_CLASS_AMBIGUOUS: no license and minimum stay under the long-term threshold; ...
```

Output formats: `console`, `json`, `csv`, `md`; `--fail-under N` makes the command exit non-zero for CI gating.

## Architecture

```
 ListingSource ──► engine.audit() ──► AuditResult ──► reporters (console / json / csv / md / slack payload)
 (JSON file,        │  builds Context once              │
  or your own        │  runs every registered check      └─► patches.collect ─► apply (pure) ─► ListingSink
  system adapter)    │  isolates failures                      safe only           stale-checked    (new file)
                     ▼
        checks/  completeness · marketing · pricing · policy · anomaly      (one decorator to add another)
```

| Decision | Why |
|---|---|
| Checks are plain functions registered with `@check("name")` | Adding a rule family never touches the engine. |
| Engine builds a portfolio `Context` once | Peer comparisons (anomaly check) need the whole portfolio, not one listing at a time. |
| A crashing check becomes a `CHECK_ERROR` finding | One malformed listing must not abort a nightly run or hide silently. |
| Thresholds live in JSON, validated on load | Operators tune bands without a code change; inverted ranges fail fast. |
| `Patch.safe` separates auto-fix from proposal | Formatting fixes are auto-applied; anything touching price or policy is **only proposed**. |
| Patches record the old value and are skipped if stale | Never overwrite data that changed since the audit ran. |
| Patching is pure and writes to a copy | The source is never modified; a re-audit after applying shows the score lift. |
| Source/Sink are small protocols | Pointing this at a real property-management system means writing one adapter. |

### Two design choices worth calling out

**Don't guess when the rules are ambiguous.** Discount bands differ for short-term vs long-term stays, and the class is inferred from license + minimum stay. When neither signal is present the engine reports `STAY_CLASS_AMBIGUOUS` instead of picking a class, and still checks values against the *union* of all classes' bands so a factor that is wrong under every class is never missed.

**A z-score alone over-fires.** With five peers the MAD is tiny, so a price 7% under the median scored a robust z of −6.7. The anomaly check therefore requires both a high modified z-score *and* a material relative gap from the median (`anomaly.min_relative_deviation`). This was found by the ground-truth benchmark and is covered by a regression test.

## Adapting it to a real system

Implement `ListingSource.load() -> list[dict]` against your API (see [`docs/SCHEMA.md`](docs/SCHEMA.md) for the dict shape) and, if you want write-back, a `ListingSink`. Everything else — checks, scoring, reports, patches — is unchanged.

## Layout

```
src/listing_auditor/
  models.py        Listing, Finding, Patch, Severity, AuditResult
  registry.py      @check decorator, Context (portfolio peer data)
  engine.py        audit(): context → checks → score, with failure isolation
  config.py        packaged defaults + JSON override, validated
  checks/          completeness, marketing, pricing, policy, anomaly
  patches.py       collect / apply / diff (pure, stale-safe)
  reporters/       console, json, csv, markdown, slack payload
  sources/         adapter protocols, JSON file adapter, seeded synthetic generator
tests/             unit, per-check, patch safety, CLI, and ground-truth end-to-end
```

## Limitations

- The checks are rules plus one robust statistic, not a learned model. The anomaly check is deliberately simple and explainable; a natural next step is peer comparison on more features (seasonality, amenities) or a learned price model.
- Synthetic data validates the logic, not real-world coverage; thresholds in `default_config.json` are illustrative and should be calibrated to your portfolio.
- No network code ships here. `to_slack_payload` builds a webhook payload; posting it is left to the caller.

MIT licensed.
