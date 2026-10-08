import copy

from listing_auditor import audit
from listing_auditor.models import Patch
from listing_auditor.patches import apply_patches, collect_patches


def messy(clean):
    clean["title"] = "  SUNNY   LOFT   DOWNTOWN  "
    clean["terms"]["check_in_time"] = "3PM"
    clean["prices"]["extra_guest_fee"] = 500  # unsafe: must only be proposed
    return clean


def test_safe_patches_fix_findings_and_recheck_is_clean(clean, config):
    rows = [messy(clean)]
    before = audit(rows, config)
    outcome = apply_patches(rows, collect_patches(before))
    after = audit(outcome.rows, config)
    after_codes = {f.code for f in after.findings}
    assert not after_codes & {"TITLE_WHITESPACE", "TITLE_CAPS", "TIME_FORMAT"}
    assert outcome.rows[0]["title"] == "Sunny Loft Downtown"
    assert outcome.rows[0]["terms"]["check_in_time"] == "15:00"
    assert after.average_score > before.average_score


def test_unsafe_patches_are_never_applied_by_default(clean, config):
    rows = [messy(clean)]
    patches = collect_patches(audit(rows, config))
    assert all(p.safe for p in patches)
    assert any(not p.safe for p in collect_patches(audit(rows, config), include_unsafe=True))
    assert apply_patches(rows, patches).rows[0]["prices"]["extra_guest_fee"] == 500


def test_input_rows_are_not_mutated(clean, config):
    rows = [messy(clean)]
    snapshot = copy.deepcopy(rows)
    apply_patches(rows, collect_patches(audit(rows, config)))
    assert rows == snapshot


def test_stale_patch_is_skipped_not_forced(clean):
    stale = Patch(clean["id"], "title", "what it used to say", "New Title", "test")
    out = apply_patches([clean], [stale])
    assert out.skipped_stale == [stale] and out.rows[0]["title"] == clean["title"]


def test_unknown_listing_is_skipped(clean):
    ghost = Patch("nope", "title", "a", "b", "test")
    assert apply_patches([clean], [ghost]).skipped_unknown == [ghost]
