from listing_auditor import audit


def codes(row, config, only=None):
    # Audit the listing inside a small portfolio so peer-based checks have context.
    return {f.code for r in audit([row], config, only=only).reports for f in r.findings}


def test_clean_listing_scores_100(clean, config):
    assert audit([clean], config).reports[0].score == 100


def test_phone_number_in_title(clean, config):
    clean["title"] = "Cozy Loft 555-123-4567"
    assert "TITLE_PHONE" in codes(clean, config, ["marketing"])


def test_banned_phrase_is_not_mislabelled_as_phone(clean, config):
    clean["title"] = "Cozy Loft best price"
    c = codes(clean, config, ["marketing"])
    assert "TITLE_BANNED_PHRASE" in c and "TITLE_PHONE" not in c


def test_amenity_claim_mismatch_proposes_unsafe_patch(clean, config):
    clean["amenities"] = [a for a in clean["amenities"] if a != "hot_tub"]
    clean["description"] += " Relax in the hot tub."
    result = audit([clean], config, only=["marketing"])
    patch = next(f.patch for f in result.findings if f.code == "AMENITY_CLAIM_MISMATCH")
    assert patch.safe is False and "hot_tub" in patch.new


def test_ambiguous_stay_class_is_flagged_not_guessed(clean, config):
    clean["license_number"] = None
    clean["terms"]["min_nights"] = 2
    assert "STAY_CLASS_AMBIGUOUS" in codes(clean, config, ["pricing"])


def test_long_term_bands_differ_from_short_term(clean, config):
    clean["license_number"] = None
    clean["terms"]["min_nights"] = 30
    clean["prices"]["monthly_factor"] = 0.60  # fine for long_term (0.55-0.80), too deep for short_term (0.70-0.85)
    assert "DISCOUNT_OUT_OF_BAND" not in codes(clean, config, ["pricing"])
    clean["license_number"] = "X-1"
    assert "DISCOUNT_OUT_OF_BAND" in codes(clean, config, ["pricing"])


def test_unknown_class_still_catches_values_wrong_everywhere(clean, config):
    clean["license_number"] = None
    clean["terms"]["min_nights"] = 2
    clean["prices"]["weekly_factor"] = 0.5
    assert "DISCOUNT_OUT_OF_BAND" in codes(clean, config, ["pricing"])


def test_extra_guest_fee_uses_occupancy_tier(clean, config):
    clean["accommodates"], clean["bedrooms"] = 4, 2
    clean["prices"]["extra_guest_fee"] = 20  # tier <=4 must be 0
    assert "EXTRA_GUEST_FEE_OUT_OF_BAND" in codes(clean, config, ["pricing"])


def test_invalid_base_price_short_circuits_without_crashing(clean, config):
    clean["prices"]["base_price"] = None
    r = audit([clean], config)
    assert {f.code for f in r.findings} >= {"BASE_PRICE_INVALID", "MISSING_FIELD"}
    assert "CHECK_ERROR" not in {f.code for f in r.findings}


def test_license_required_only_for_short_stays(clean, config):
    clean["address"]["city"] = "Lakeport"
    clean["license_number"] = None
    clean["terms"]["min_nights"] = 2
    assert "LICENSE_REQUIRED" in codes(clean, config, ["policy"])
    clean["terms"]["min_nights"] = 30
    assert "LICENSE_REQUIRED" not in codes(clean, config, ["policy"])


def test_min_nights_greater_than_max(clean, config):
    clean["terms"].update(min_nights=10, max_nights=5)
    assert "MIN_GT_MAX" in codes(clean, config, ["policy"])


def test_checkout_must_precede_checkin(clean, config):
    clean["terms"].update(check_in_time="10:00", check_out_time="11:00")
    assert "TIME_ORDER" in codes(clean, config, ["policy"])


def test_price_outlier_needs_both_z_and_material_gap(portfolio, config):
    rows, injected = portfolio
    target = next(r for r in rows if r["id"] not in injected)
    # A 7% gap is not worth flagging even when the peer group is tight.
    import copy
    rows = copy.deepcopy(rows)
    t = next(r for r in rows if r["id"] == target["id"])
    t["prices"]["base_price"] = round(t["prices"]["base_price"] * 0.93)
    assert "PRICE_OUTLIER" not in {f.code for r in audit(rows, config).reports if r.listing_id == t["id"] for f in r.findings}
    t["prices"]["base_price"] = round(target["prices"]["base_price"] * 3)
    assert "PRICE_OUTLIER" in {f.code for r in audit(rows, config).reports if r.listing_id == t["id"] for f in r.findings}


def test_a_crashing_check_is_isolated(clean, config, monkeypatch):
    from listing_auditor import registry

    def boom(lst, ctx):
        raise RuntimeError("kaboom")

    monkeypatch.setitem(registry._REGISTRY, "boom", boom)
    result = audit([clean], config)
    got = {f.code for f in result.findings}
    assert "CHECK_ERROR" in got
    assert result.reports[0].score < 100  # the failure is visible, and every other check still ran
