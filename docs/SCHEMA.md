# Listing schema

The engine consumes plain dicts. A source adapter maps whatever system you use into this shape.
Unknown extra keys are ignored. Missing optional keys simply skip the checks that need them.

```jsonc
{
  "id": "lst_0001",                 // required, unique
  "nickname": "LKP-001",            // optional, used in reports
  "title": "Sunny 3BR Cabin in Lakeport",
  "description": "…",
  "address": { "city": "Lakeport", "state": "CA", "zip": "95453" },
  "bedrooms": 3, "bathrooms": 2, "accommodates": 6,
  "amenities": ["wifi", "smoke_detector", "kitchen", "heating", "pool"],
  "photos": [ { "url": "…", "caption": "Kitchen", "width": 1920, "height": 1280 } ],
  "prices": {
    "base_price": 240,              // nightly
    "weekly_factor": 0.9,           // multiplier on nightly rate for 7+ nights
    "monthly_factor": 0.78,
    "weekend_factor": 1.15,
    "cleaning_fee": 150,
    "extra_guest_fee": 25
  },
  "terms": {
    "min_nights": 2, "max_nights": 180,
    "cancellation_policy": "moderate",   // flexible | moderate | strict
    "check_in_time": "15:00", "check_out_time": "11:00"
  },
  "license_number": "STR-LKP-00001",     // null for long-term-only listings
  "ota_links": { "airbnb": "…", "vrbo": "…", "booking": "…" }
}
```

## Finding codes

| Check | Codes |
|---|---|
| completeness | `MISSING_FIELD` `PHOTOS_FEW` `HERO_PHOTO_QUALITY` `PHOTO_CAPTIONS` `AMENITIES_MISSING` `OTA_LINK_MISSING` |
| marketing | `TITLE_WHITESPACE` `TITLE_CAPS` `TITLE_TOO_LONG` `TITLE_PHONE` `TITLE_BANNED_PHRASE` `DESCRIPTION_SHORT` `AMENITY_CLAIM_MISMATCH` |
| pricing | `BASE_PRICE_INVALID` `STAY_CLASS_AMBIGUOUS` `DISCOUNT_OUT_OF_BAND` `WEEKEND_FACTOR_OUT_OF_BAND` `CLEANING_FEE_OUT_OF_BAND` `EXTRA_GUEST_FEE_OUT_OF_BAND` |
| policy | `OCCUPANCY_EXCEEDED` `MIN_GT_MAX` `LICENSE_REQUIRED` `CANCELLATION_POLICY_INVALID` `TIME_INVALID` `TIME_FORMAT` `TIME_ORDER` |
| anomaly | `PRICE_OUTLIER` |
| engine | `CHECK_ERROR` |

Auto-fixable (`safe`) patches: `TITLE_WHITESPACE`, `TITLE_CAPS`, `TIME_FORMAT`. Everything else that carries a patch is a proposal for human review.

## Writing a check

```python
from listing_auditor.registry import check
from listing_auditor.models import Finding, Severity

@check("my_rule")
def my_rule(listing, ctx):
    if listing.get("bedrooms") == 0:
        yield Finding("my_rule", "ZERO_BEDROOMS", Severity.LOW, "studio?", listing.id)
```

Import the module from `checks/__init__.py` and it runs on every audit.
