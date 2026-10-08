"""End-to-end: audit a synthetic portfolio and compare against the defects we planted."""
from listing_auditor import Severity, audit


def test_every_planted_defect_is_detected(portfolio, config):
    rows, injected = portfolio
    found = {r.listing_id: {f.code for f in r.findings} for r in audit(rows, config).reports}
    missed = [(lid, c) for lid, codes in injected.items() for c in codes if c not in found[lid]]
    assert not missed, f"missed planted defects: {missed}"


def test_clean_listings_have_no_medium_or_worse_findings(portfolio, config):
    rows, injected = portfolio
    noisy = {
        r.listing_id: [f.code for f in r.findings if f.severity >= Severity.MEDIUM]
        for r in audit(rows, config).reports
        if r.listing_id not in injected
    }
    assert not {k: v for k, v in noisy.items() if v}


def test_generator_is_deterministic():
    from listing_auditor.sources.synthetic import generate

    assert generate(30, 5) == generate(30, 5)
    assert generate(30, 5) != generate(30, 6)
