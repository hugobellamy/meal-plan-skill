#!/usr/bin/env python3
"""week — roll meal objects up into the week's daily and weekly nutrition.

  week.py totals 1            # day-by-day per-portion macros + weekly average
  week.py totals 1 --json

Reads every meal in weeks/week-NN/meals/ and its eat_on schedule. If a
profile.json exists in the project root with target_daily_calories / macros,
the weekly average is compared against it.
"""
import argparse
import json
from pathlib import Path

import _db
import _state


def load_profile() -> dict:
    p = Path.cwd() / "profile.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def cmd_totals(args):
    by_day = _state.daily_totals(args.week)
    if not by_day:
        print(f"No scheduled meals in {_state.normalize_week(args.week)}. "
              f"Give meals an --eat-on schedule, then re-run.")
        return
    days = _state.ordered_days(by_day)
    week_acc = _db.empty_totals()
    rows = []
    for d in days:
        rt = _db.round_totals(by_day[d])
        rows.append((d, rt))
        _db.add_totals(week_acc, by_day[d])
    avg = _db.round_totals({k: v / len(days) for k, v in week_acc.items()})

    if args.json:
        print(json.dumps({
            "days": {d: rt for d, rt in rows}, "weekly_average": avg,
        }, indent=2))
        return

    print(f"{_state.normalize_week(args.week)} — per-portion intake by day")
    print(f"  {'day':<6}{'kcal':>7}{'P':>7}{'C':>7}{'F':>7}{'Fibre':>7}{'Salt':>7}")
    for d, rt in rows:
        print(f"  {d:<6}{rt['kcal']:>7.0f}{rt['protein_g']:>7.1f}{rt['carbs_g']:>7.1f}"
              f"{rt['fat_g']:>7.1f}{rt['fibre_g']:>7.1f}{rt['salt_g']:>7.2f}")
    print(f"  {'AVG':<6}{avg['kcal']:>7.0f}{avg['protein_g']:>7.1f}{avg['carbs_g']:>7.1f}"
          f"{avg['fat_g']:>7.1f}{avg['fibre_g']:>7.1f}{avg['salt_g']:>7.2f}")

    prof = load_profile()
    target = prof.get("target_daily_calories") or prof.get("daily_calories")
    if target:
        diff = avg["kcal"] - target
        print(f"\n  Target {target} kcal/day — average is {diff:+.0f} kcal/day "
              f"({'over' if diff > 0 else 'under'}).")
    macros = prof.get("macros") or {}
    if macros:
        bits = []
        for k, label in [("protein_g", "P"), ("carbs_g", "C"), ("fat_g", "F")]:
            if macros.get(k):
                bits.append(f"{label} {avg[k]:.0f}/{macros[k]}g")
        if bits:
            print("  Macro avg vs target: " + ", ".join(bits))


def main():
    p = argparse.ArgumentParser(description="Week-level nutrition rollup.")
    sub = p.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("totals")
    t.add_argument("week")
    t.add_argument("--json", action="store_true")
    t.set_defaults(func=cmd_totals)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
