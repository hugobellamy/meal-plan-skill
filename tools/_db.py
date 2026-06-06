"""Shared food-database access for the diet-planner tools.

Standard library only — no pandas/numpy at runtime. Reads the vendored
data/foods.csv (built by scripts/build_db.py from McCance CoFID 2021) plus an
optional data/custom-foods.csv of user-added rows. All nutrient values are per
100 g of food.
"""
from __future__ import annotations
import csv
import difflib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
# Base table ships with the skill. Custom foods are PER-PROJECT: they live in the
# user's working directory so they accumulate per diet project, never pollute the
# installed skill, and survive `git pull` updates of the skill.
FOODS_CSV = ROOT / "data" / "foods.csv"
CUSTOM_CSV = Path.cwd() / "custom-foods.csv"

# Per-100g nutrient fields carried through the whole pipeline, in display order.
NUTRIENTS = ["kcal", "protein_g", "fat_g", "satfat_g",
             "carbs_g", "sugars_g", "fibre_g", "salt_g"]
NUTRIENT_LABELS = {
    "kcal": "kcal", "protein_g": "Protein (g)", "fat_g": "Fat (g)",
    "satfat_g": "SatFat (g)", "carbs_g": "Carbs (g)", "sugars_g": "Sugars (g)",
    "fibre_g": "Fibre (g)", "salt_g": "Salt (g)",
}
CUSTOM_HEADER = ["food_code", "name", "group"] + NUTRIENTS


def _coerce(row: dict) -> dict:
    """Turn raw CSV strings into a clean food record with float nutrients."""
    out = {
        "food_code": (row.get("food_code") or "").strip(),
        "name": (row.get("name") or "").strip(),
        "group": (row.get("group") or "").strip(),
    }
    for n in NUTRIENTS:
        try:
            out[n] = float(row.get(n) or 0)
        except (TypeError, ValueError):
            out[n] = 0.0
    return out


def load_foods() -> list[dict]:
    """All foods: base McCance table plus any custom additions (custom wins)."""
    foods: dict[str, dict] = {}
    for path in (FOODS_CSV, CUSTOM_CSV):
        if not path.exists():
            continue
        with path.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                rec = _coerce(row)
                if rec["food_code"]:
                    foods[rec["food_code"]] = rec
    return list(foods.values())


def get(code: str) -> dict | None:
    code = code.strip()
    for rec in load_foods():
        if rec["food_code"] == code:
            return rec
    return None


def search(query: str, limit: int = 12, foods: list[dict] | None = None) -> list[dict]:
    """Rank foods against a free-text query.

    Score = number of query tokens appearing as substrings in the food name
    (the dominant signal), plus a fuzzy whole-string ratio as a tiebreak. Good
    enough for the LLM to pick a code from a shortlist; deterministic and fast.
    """
    if foods is None:
        foods = load_foods()
    q = query.lower().strip()
    tokens = [t for t in q.replace(",", " ").split() if t]
    scored = []
    for rec in foods:
        name = rec["name"].lower()
        token_hits = sum(1 for t in tokens if t in name)
        ratio = difflib.SequenceMatcher(None, q, name).ratio()
        # Slightly reward shorter names so a clean exact item beats a long combo.
        score = token_hits + 0.5 * ratio - 0.0005 * len(name)
        if token_hits or ratio > 0.4:
            scored.append((score, rec))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [rec for _, rec in scored[:limit]]


def scale(rec: dict, grams: float) -> dict:
    """Nutrients for `grams` of a food (record holds per-100g values)."""
    factor = grams / 100.0
    return {n: rec[n] * factor for n in NUTRIENTS}


def empty_totals() -> dict:
    return {n: 0.0 for n in NUTRIENTS}


def add_totals(acc: dict, more: dict) -> dict:
    for n in NUTRIENTS:
        acc[n] = acc.get(n, 0.0) + more.get(n, 0.0)
    return acc


def round_totals(t: dict) -> dict:
    """Display rounding: kcal whole, grams to 1 dp, salt to 2 dp."""
    out = {}
    for n in NUTRIENTS:
        v = t.get(n, 0.0)
        if n == "kcal":
            out[n] = round(v)
        elif n == "salt_g":
            out[n] = round(v, 2)
        else:
            out[n] = round(v, 1)
    return out
