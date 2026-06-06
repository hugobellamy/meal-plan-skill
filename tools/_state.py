"""Week/meal state on disk, plus macro summing.

State lives in the USER's project directory (current working directory), not in
the skill install:

    weeks/
      week-01/
        meals/
          <meal_id>.json     # one meal object per file
        meal-plan.md         # generated
        recipes.md           # generated (method left blank for the LLM)
        shopping.json        # intermediate for the 2-part shopping list
        shopping-list.md     # generated

A meal object:
    {
      "meal_id": "beef-potato-hash",
      "name": "Cowboy Beef & Potato Hash",
      "portions": 4,              # how many portions this batch yields
      "type": "batch",           # batch | fixed | snack | single (free text)
      "eat_on": ["Mon Lunch", "Mon Dinner"],   # optional schedule
      "items": [
        {"food_code": "...", "name": "...", "grams": 500, "note": ""}
      ]
    }

Item grams are TOTAL grams cooked (household). Per-portion = total / portions.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

import _db

WEEKS = Path.cwd() / "weeks"


def normalize_week(week: str) -> str:
    """Accept '1', '01', 'week-1', 'week-01' -> 'week-01'."""
    m = re.search(r"(\d+)", str(week))
    if not m:
        raise SystemExit(f"Could not read a week number from {week!r}")
    return f"week-{int(m.group(1)):02d}"


def week_dir(week: str, create: bool = False) -> Path:
    d = WEEKS / normalize_week(week)
    if create:
        (d / "meals").mkdir(parents=True, exist_ok=True)
    return d


def meal_path(week: str, meal_id: str) -> Path:
    return week_dir(week) / "meals" / f"{meal_id}.json"


def load_meal(week: str, meal_id: str) -> dict:
    p = meal_path(week, meal_id)
    if not p.exists():
        raise SystemExit(f"No meal {meal_id!r} in {normalize_week(week)}. "
                         f"Create it with `meal.py new`.")
    return json.loads(p.read_text(encoding="utf-8"))


def save_meal(week: str, meal: dict) -> Path:
    week_dir(week, create=True)
    p = meal_path(week, meal["meal_id"])
    p.write_text(json.dumps(meal, indent=2) + "\n", encoding="utf-8")
    return p


def list_meals(week: str) -> list[dict]:
    mdir = week_dir(week) / "meals"
    if not mdir.exists():
        return []
    meals = [json.loads(p.read_text(encoding="utf-8"))
             for p in sorted(mdir.glob("*.json"))]
    return meals


def meal_totals(meal: dict) -> dict:
    """Sum real per-100g rows * grams/100 over every item -> household totals."""
    acc = _db.empty_totals()
    for item in meal.get("items", []):
        rec = _db.get(item["food_code"])
        if rec is None:
            raise SystemExit(
                f"Item {item['food_code']!r} in meal {meal['meal_id']!r} is not "
                f"in the database. Re-add it or create it with `fooddb.py add`.")
        _db.add_totals(acc, _db.scale(rec, item["grams"]))
    return acc


def per_portion(totals: dict, portions: int) -> dict:
    portions = max(int(portions or 1), 1)
    return {k: v / portions for k, v in totals.items()}


DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
_DAY_ALIASES = {
    "mon": "Mon", "monday": "Mon", "tue": "Tue", "tues": "Tue", "tuesday": "Tue",
    "wed": "Wed", "weds": "Wed", "wednesday": "Wed", "thu": "Thu", "thur": "Thu",
    "thurs": "Thu", "thursday": "Thu", "fri": "Fri", "friday": "Fri",
    "sat": "Sat", "saturday": "Sat", "sun": "Sun", "sunday": "Sun",
}


def _day_of(slot: str) -> str:
    first = str(slot).strip().split()[0].lower() if str(slot).strip() else ""
    return _DAY_ALIASES.get(first, "Other")


def schedule(week: str) -> dict[str, list[tuple[dict, str]]]:
    """Map each day -> [(meal, slot_label), ...] from every meal's eat_on list.

    A meal with no eat_on contributes nothing to the daily plan (it still exists
    for recipes/shopping). Each eat_on entry = one portion eaten in that slot.
    """
    by_day: dict[str, list[tuple[dict, str]]] = {}
    for meal in list_meals(week):
        for slot in meal.get("eat_on", []) or []:
            by_day.setdefault(_day_of(slot), []).append((meal, slot))
    return by_day


def ordered_days(by_day: dict) -> list[str]:
    days = [d for d in DAY_ORDER if d in by_day]
    if "Other" in by_day:
        days.append("Other")
    return days


def daily_totals(week: str) -> dict[str, dict]:
    """Day -> summed per-portion macros of every portion eaten that day."""
    out: dict[str, dict] = {}
    for day, entries in schedule(week).items():
        acc = _db.empty_totals()
        for meal, _slot in entries:
            _db.add_totals(acc, per_portion(meal_totals(meal), meal.get("portions", 1)))
        out[day] = acc
    return out
