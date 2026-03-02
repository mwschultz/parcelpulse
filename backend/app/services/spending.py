"""
BLS spending estimates — pure sync computation, no DB or HTTP.
Loads bls_spending.json once at module import and fills null cells via linear interpolation.
"""
import json
from pathlib import Path

_DATA_PATH = Path(__file__).parent.parent.parent / "data" / "bls_spending.json"

BRACKETS = [
    "lt_15000",
    "15000_29999",
    "30000_39999",
    "40000_49999",
    "50000_69999",
    "70000_99999",
    "100000_149999",
    "150000_199999",
    "ge_200000",
]

# Midpoint of each bracket (used for interpolation)
MIDPOINTS = {
    "lt_15000": 7500,
    "15000_29999": 22500,
    "30000_39999": 35000,
    "40000_49999": 45000,
    "50000_69999": 60000,
    "70000_99999": 85000,
    "100000_149999": 125000,
    "150000_199999": 175000,
    "ge_200000": 250000,
}

BRACKET_LABELS = {
    "lt_15000": "Less than $15,000",
    "15000_29999": "$15,000\u2013$29,999",
    "30000_39999": "$30,000\u2013$39,999",
    "40000_49999": "$40,000\u2013$49,999",
    "50000_69999": "$50,000\u2013$69,999",
    "70000_99999": "$70,000\u2013$99,999",
    "100000_149999": "$100,000\u2013$149,999",
    "150000_199999": "$150,000\u2013$199,999",
    "ge_200000": "$200,000 and more",
}

CATEGORY_DISPLAY_ORDER = [
    "food_at_home",
    "food_away_from_home",
    "transportation",
    "healthcare",
    "entertainment",
    "apparel_and_services",
    "personal_care_products_services",
    "education",
]

CATEGORY_LABELS = {
    "food_at_home": "Food at Home",
    "food_away_from_home": "Food Away from Home",
    "transportation": "Transportation",
    "healthcare": "Healthcare",
    "entertainment": "Entertainment",
    "apparel_and_services": "Apparel & Services",
    "personal_care_products_services": "Personal Care",
    "education": "Education",
}


def _fill_nulls(raw_data: dict) -> dict:
    """
    Fill suppressed (null) cells via linear interpolation by bracket midpoint.
    Returns a new dict with all nulls replaced by interpolated integer values.
    """
    all_categories = set()
    for bracket in BRACKETS:
        all_categories.update(raw_data[bracket].keys())

    filled = {b: dict(raw_data[b]) for b in BRACKETS}

    for cat in all_categories:
        # Collect known (non-null) data points as (midpoint, value) pairs
        known = [
            (MIDPOINTS[b], filled[b][cat])
            for b in BRACKETS
            if filled[b].get(cat) is not None
        ]
        if not known:
            continue

        for i, bracket in enumerate(BRACKETS):
            if filled[bracket].get(cat) is not None:
                continue

            x = MIDPOINTS[bracket]

            # Find neighbors: largest known midpoint <= x and smallest known midpoint >= x
            lower = [(mx, mv) for mx, mv in known if mx <= x]
            upper = [(mx, mv) for mx, mv in known if mx >= x]

            if lower and upper:
                # Interpolate between nearest lower and upper
                x0, y0 = max(lower, key=lambda p: p[0])
                x1, y1 = min(upper, key=lambda p: p[0])
                if x1 == x0:
                    value = y0
                else:
                    t = (x - x0) / (x1 - x0)
                    value = y0 + t * (y1 - y0)
            elif upper:
                # Extrapolate below: use slope of two nearest upper points
                sorted_upper = sorted(upper, key=lambda p: p[0])
                if len(sorted_upper) >= 2:
                    x0, y0 = sorted_upper[0]
                    x1, y1 = sorted_upper[1]
                    slope = (y1 - y0) / (x1 - x0) if x1 != x0 else 0
                    value = y0 + slope * (x - x0)
                else:
                    value = sorted_upper[0][1]
            else:
                # Extrapolate above: use slope of two nearest lower points
                sorted_lower = sorted(lower, key=lambda p: p[0])
                if len(sorted_lower) >= 2:
                    x0, y0 = sorted_lower[-2]
                    x1, y1 = sorted_lower[-1]
                    slope = (y1 - y0) / (x1 - x0) if x1 != x0 else 0
                    value = y1 + slope * (x - x1)
                else:
                    value = sorted_lower[-1][1]

            filled[bracket][cat] = max(0, round(value))

    return filled


def _load_data() -> dict:
    with open(_DATA_PATH) as f:
        raw = json.load(f)
    bracket_data = {b: raw[b] for b in BRACKETS}
    return _fill_nulls(bracket_data)


# Module-level filled data — loaded once at import
_FILLED: dict = _load_data()


def _income_to_bracket(income: int) -> str:
    if income < 15_000:
        return "lt_15000"
    elif income < 30_000:
        return "15000_29999"
    elif income < 40_000:
        return "30000_39999"
    elif income < 50_000:
        return "40000_49999"
    elif income < 70_000:
        return "50000_69999"
    elif income < 100_000:
        return "70000_99999"
    elif income < 150_000:
        return "100000_149999"
    elif income < 200_000:
        return "150000_199999"
    else:
        return "ge_200000"


NATIONAL_MEDIAN_INCOME = 75000  # ACS 2022 national median HH income


def get_spending(median_household_income: int, households: int) -> dict | None:
    """
    Return spending estimates for a trade area given median household income and
    household count. Falls back to national median when income is unavailable.
    Returns None only if households is also <= 0.
    """
    if households <= 0:
        return None

    is_estimated = median_household_income <= 0
    income = NATIONAL_MEDIAN_INCOME if is_estimated else median_household_income
    bracket = _income_to_bracket(income)
    bracket_data = _FILLED[bracket]

    categories = []
    for key in CATEGORY_DISPLAY_ORDER:
        per_unit = bracket_data.get(key)
        if per_unit is None:
            continue
        categories.append({
            "key": key,
            "label": CATEGORY_LABELS[key],
            "per_unit": int(per_unit),
            "total": int(per_unit) * households,
        })

    return {
        "bracket": bracket,
        "bracket_label": BRACKET_LABELS[bracket],
        "households": households,
        "categories": categories,
        "is_estimated": is_estimated,
    }
