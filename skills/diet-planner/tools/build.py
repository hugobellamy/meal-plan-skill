#!/usr/bin/env python3
"""build — render the human-facing markdown from the meal objects.

  build.py meal-plan 1     # weeks/week-01/meal-plan.md  (per-portion intake by day)
  build.py recipes 1       # weeks/week-01/recipes.md    (household scale + macro tables)
  build.py all 1

Every number is summed from real McCance rows, so the meal plan and the recipe
macro tables are automatically consistent. recipes.md leaves the Method section
blank for the LLM to fill in with actual cooking steps.
"""
import argparse

import _db
import _state


def _slot_label(slot: str, day: str) -> str:
    parts = str(slot).split()
    if parts and parts[0].lower().startswith(day.lower()[:3]):
        return " ".join(parts[1:]) or slot
    return slot


def render_meal_plan(week: str) -> str:
    wk = _state.normalize_week(week)
    by_day = _state.schedule(week)
    days = _state.ordered_days(by_day)
    out = [f"# Meal Plan — {wk.replace('-', ' ').title()}", "",
           "_Per-portion intake — what you actually eat. Numbers are summed from "
           "the McCance food database; do not hand-edit them (re-run "
           "`build.py meal-plan`)._", ""]
    if not days:
        out.append("_No meals scheduled yet. Give meals an `--eat-on` schedule._")
        return "\n".join(out) + "\n"

    week_acc = _db.empty_totals()
    for day in days:
        out += [f"## {day}", "",
                "| Slot | Meal | kcal | P (g) | C (g) | F (g) |",
                "|---|---|---:|---:|---:|---:|"]
        day_acc = _db.empty_totals()
        for meal, slot in by_day[day]:
            pp = _state.per_portion(_state.meal_totals(meal), meal.get("portions", 1))
            _db.add_totals(day_acc, pp)
            r = _db.round_totals(pp)
            out.append(f"| {_slot_label(slot, day)} | {meal['name']} | "
                       f"{r['kcal']:.0f} | {r['protein_g']:.1f} | "
                       f"{r['carbs_g']:.1f} | {r['fat_g']:.1f} |")
        d = _db.round_totals(day_acc)
        out.append(f"| **Total** | | **{d['kcal']:.0f}** | **{d['protein_g']:.1f}** "
                   f"| **{d['carbs_g']:.1f}** | **{d['fat_g']:.1f}** |")
        out.append("")
        _db.add_totals(week_acc, day_acc)

    avg = _db.round_totals({k: v / len(days) for k, v in week_acc.items()})
    out += ["## Weekly average", "",
            "| | kcal | P (g) | C (g) | F (g) | Fibre (g) | Salt (g) |",
            "|---|---:|---:|---:|---:|---:|---:|",
            f"| Average/day | {avg['kcal']:.0f} | {avg['protein_g']:.1f} | "
            f"{avg['carbs_g']:.1f} | {avg['fat_g']:.1f} | {avg['fibre_g']:.1f} "
            f"| {avg['salt_g']:.2f} |", ""]
    return "\n".join(out) + "\n"


def render_recipes(week: str) -> str:
    wk = _state.normalize_week(week)
    meals = _state.list_meals(week)
    out = [f"# Recipes — {wk.replace('-', ' ').title()}", "",
           "_Household scale — the actual quantities to cook. Ingredient amounts "
           "and macro tables are generated; write the **Method** for each._", ""]
    if not meals:
        out.append("_No meals yet._")
        return "\n".join(out) + "\n"

    for meal in meals:
        portions = meal.get("portions", 1)
        out += [f"## {meal['name']}", "", f"Makes {portions} portion(s).", "",
                "**Ingredients**", ""]
        for it in meal["items"]:
            note = f" — {it['note']}" if it.get("note") else ""
            out.append(f"- {it['grams']:.0f} g {it['name']}{note}")
        out += ["", "**Macros**", "",
                "| Ingredient | Amount | kcal | Protein (g) | Carbs (g) | Fat (g) |",
                "|---|---:|---:|---:|---:|---:|"]
        totals = _db.empty_totals()
        for it in meal["items"]:
            rec = _db.get(it["food_code"])
            s = _db.scale(rec, it["grams"])
            _db.add_totals(totals, s)
            r = _db.round_totals(s)
            out.append(f"| {it['name']} | {it['grams']:.0f} g | {r['kcal']:.0f} "
                       f"| {r['protein_g']:.1f} | {r['carbs_g']:.1f} | {r['fat_g']:.1f} |")
        rt = _db.round_totals(totals)
        rp = _db.round_totals(_state.per_portion(totals, portions))
        out += [f"| **Total ({portions} portions)** | | **{rt['kcal']:.0f}** | "
                f"**{rt['protein_g']:.1f}** | **{rt['carbs_g']:.1f}** | **{rt['fat_g']:.1f}** |",
                f"| **Per portion** | | **{rp['kcal']:.0f}** | **{rp['protein_g']:.1f}** "
                f"| **{rp['carbs_g']:.1f}** | **{rp['fat_g']:.1f}** |", "",
                "**Method**", "",
                "<!-- Write the cooking steps here. The numbers above are fixed; "
                "this is the only part to author by hand. -->",
                "1. ", "", "---", ""]
    return "\n".join(out) + "\n"


def _write(week: str, name: str, text: str):
    d = _state.week_dir(week, create=True)
    path = d / name
    path.write_text(text, encoding="utf-8")
    print(f"Wrote {path}")


def cmd_meal_plan(args):
    _write(args.week, "meal-plan.md", render_meal_plan(args.week))


def cmd_recipes(args):
    _write(args.week, "recipes.md", render_recipes(args.week))


def cmd_all(args):
    cmd_meal_plan(args)
    cmd_recipes(args)


def main():
    p = argparse.ArgumentParser(description="Render meal-plan.md / recipes.md.")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in [("meal-plan", cmd_meal_plan), ("recipes", cmd_recipes), ("all", cmd_all)]:
        sp = sub.add_parser(name)
        sp.add_argument("week")
        sp.set_defaults(func=fn)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
