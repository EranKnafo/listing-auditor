"""Seeded synthetic portfolio with *known* injected defects.

Because every defect is injected on purpose, we know the ground truth: the test suite
and ``listing-auditor benchmark`` can measure recall (did we catch what we planted?) and
false-positive rate (did we flag listings we left clean?). All data is fictional.
"""
from __future__ import annotations

import random
from typing import Callable

CITIES = [  # (city, state, price multiplier, code)
    ("Lakeport", "CA", 1.15, "LKP"),
    ("Pinecrest", "CA", 0.95, "PNC"),
    ("Harbor Bay", "WA", 1.30, "HBY"),
    ("Cedar Falls", "OR", 0.85, "CDF"),
]
ADJECTIVES = ["Sunny", "Cozy", "Modern", "Peaceful", "Charming", "Bright", "Rustic"]
TYPES = ["Cottage", "Cabin", "Loft", "Bungalow", "Retreat"]
ROOMS = ["Living room", "Kitchen", "Primary bedroom", "Bedroom", "Bathroom", "Exterior", "Patio", "Dining area"]
OPTIONAL_AMENITIES = ["parking", "washer", "dryer", "air_conditioning", "tv", "pool", "hot_tub", "fireplace", "ev_charger"]
FEE_TIERS = [(4, (0, 0)), (7, (15, 35)), (10, (25, 50)), (999, (35, 60))]
LICENSE_CITIES = {"Lakeport", "Harbor Bay"}  # mirrors default_config.json


def _clean_listing(i: int, rng: random.Random) -> dict:
    city, state, mult, code = rng.choice(CITIES)
    beds = rng.choices([1, 2, 3, 4, 5], weights=[20, 30, 25, 15, 10])[0]
    occ = beds * 2 + rng.randint(0, 1)
    long_term = rng.random() < 0.15
    lid = f"lst_{i:04d}"

    amenities = ["wifi", "smoke_detector", "kitchen", "heating"] + rng.sample(OPTIONAL_AMENITIES, rng.randint(3, 6))
    feats = {"pool": "a private pool", "hot_tub": "a hot tub", "fireplace": "a fireplace", "ev_charger": "an EV charger"}
    extras = [feats[a] for a in amenities if a in feats]
    description = (
        f"Welcome to this {beds}-bedroom home in {city}, set a short walk from the water and the town centre. "
        f"It sleeps {occ} comfortably, with a fully equipped kitchen, fast wifi and plenty of space to spread out. "
        + (f"Guests enjoy {', '.join(extras)}. " if extras else "")
        + "Mornings start with coffee on the patio and evenings end around the dining table. "
        "Local restaurants, trails and a farmers market are all within a ten minute drive. "
        "We take care of every detail so you can simply arrive and relax."
    )

    stay = "long_term" if long_term else "short_term"
    bands = {
        "short_term": {"weekly_factor": (0.87, 0.93), "monthly_factor": (0.72, 0.83)},
        "long_term": {"weekly_factor": (0.92, 1.0), "monthly_factor": (0.58, 0.78)},
    }[stay]
    tier_fee = next(fee for max_occ, fee in FEE_TIERS if occ <= max_occ)

    return {
        "id": lid,
        "nickname": f"{code}-{i:03d}",
        "title": f"{rng.choice(ADJECTIVES)} {beds}BR {rng.choice(TYPES)} in {city}",
        "description": description,
        "address": {"city": city, "state": state, "zip": f"{rng.randint(90000, 99999)}"},
        "bedrooms": beds,
        "bathrooms": max(1, beds - rng.randint(0, 1)),
        "accommodates": occ,
        "amenities": amenities,
        "photos": [
            {"url": f"https://photos.example.com/{lid}/{n}.jpg", "caption": rng.choice(ROOMS), "width": 1920, "height": 1280}
            for n in range(rng.randint(16, 28))
        ],
        "prices": {
            "base_price": round((85 + 55 * beds) * mult * rng.uniform(0.93, 1.07)),
            "weekly_factor": round(rng.uniform(*bands["weekly_factor"]), 2),
            "monthly_factor": round(rng.uniform(*bands["monthly_factor"]), 2),
            "weekend_factor": round(rng.uniform(1.05, 1.25), 2),
            "cleaning_fee": round(beds * rng.uniform(35, 70)),
            "extra_guest_fee": 5 * round(rng.uniform(*tier_fee) / 5) if tier_fee[1] else 0,
        },
        "terms": {
            "min_nights": 30 if long_term else rng.choice([1, 2, 3]),
            "max_nights": rng.choice([90, 180, 365]),
            "cancellation_policy": rng.choice(["flexible", "moderate", "strict"]),
            "check_in_time": rng.choice(["15:00", "16:00"]),
            "check_out_time": rng.choice(["10:00", "11:00"]),
        },
        "license_number": None if long_term else f"STR-{code}-{i:05d}",
        "ota_links": {p: f"https://{p}.example.com/rooms/{lid}" for p in ("airbnb", "vrbo", "booking")},
    }


# --- defect injectors: each returns the finding code it plants, or None if not applicable ----------
Injector = Callable[[dict, random.Random], "str | None"]


def _title_phone(l, r):
    l["title"] += f" call 555-201-{r.randint(1000, 9999)}"
    return "TITLE_PHONE"


def _title_caps(l, r):
    l["title"] = l["title"].upper()
    return "TITLE_CAPS"


def _photos_few(l, r):
    l["photos"] = l["photos"][: r.randint(3, 8)]
    return "PHOTOS_FEW"


def _hero_portrait(l, r):
    l["photos"][0].update(width=1080, height=1920)
    return "HERO_PHOTO_QUALITY"


def _claim_mismatch(l, r):
    absent = [(p, a) for p, a in (("pool", "pool"), ("hot tub", "hot_tub"), ("fireplace", "fireplace")) if a not in l["amenities"]]
    if not absent:
        return None
    phrase, _ = r.choice(absent)
    l["description"] += f" Don't miss the {phrase}!"
    return "AMENITY_CLAIM_MISMATCH"


def _occupancy(l, r):
    l["accommodates"] = l["bedrooms"] * 3 + r.randint(2, 4)
    return "OCCUPANCY_EXCEEDED"


def _weekly_band(l, r):
    l["prices"]["weekly_factor"] = 0.60
    return "DISCOUNT_OUT_OF_BAND"


def _cleaning(l, r):
    l["prices"]["cleaning_fee"] = 0
    return "CLEANING_FEE_OUT_OF_BAND"


def _extra_guest(l, r):
    l["prices"]["extra_guest_fee"] = 200
    return "EXTRA_GUEST_FEE_OUT_OF_BAND"


def _price_outlier(l, r):
    l["prices"]["base_price"] = round(l["prices"]["base_price"] * 3.5)
    return "PRICE_OUTLIER"


def _license(l, r):
    if l["address"]["city"] not in LICENSE_CITIES or l["terms"]["min_nights"] >= 30:
        return None
    l["license_number"] = None
    return "LICENSE_REQUIRED"


def _min_gt_max(l, r):
    l["terms"].update(min_nights=14, max_nights=7)
    return "MIN_GT_MAX"


def _time_format(l, r):
    if not l["terms"]["check_in_time"][:2].isdigit() or ":" not in l["terms"]["check_in_time"]:
        return None  # already mangled by an earlier injection
    hh = int(l["terms"]["check_in_time"][:2]) - 12
    l["terms"]["check_in_time"] = f"{hh}PM"
    return "TIME_FORMAT"


def _ota_missing(l, r):
    del l["ota_links"][r.choice(list(l["ota_links"]))]
    return "OTA_LINK_MISSING"


INJECTORS: list[Injector] = [
    _title_phone, _title_caps, _photos_few, _hero_portrait, _claim_mismatch, _occupancy, _weekly_band,
    _cleaning, _extra_guest, _price_outlier, _license, _min_gt_max, _time_format, _ota_missing,
]


def generate(count: int = 60, seed: int = 7, defect_rate: float = 0.5) -> tuple[list[dict], dict[str, list[str]]]:
    """Return ``(listings, injected)`` where ``injected`` maps listing id -> planted finding codes."""
    rng = random.Random(seed)
    listings = [_clean_listing(i + 1, rng) for i in range(count)]
    injected: dict[str, list[str]] = {}
    for lst in listings:
        if rng.random() >= defect_rate:
            continue
        codes: list[str] = []
        for _ in range(rng.choice([1, 1, 2])):
            for inj in rng.sample(INJECTORS, len(INJECTORS)):
                code = inj(lst, rng)
                if code:
                    codes.append(code)
                    break
        injected[lst["id"]] = codes
    return listings, injected
