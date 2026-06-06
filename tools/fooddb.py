#!/usr/bin/env python3
"""fooddb — search and extend the food-composition database.

The LLM's grounding tool: find a real food, read its per-100g numbers, and (when
something genuinely isn't in the table) add a custom row so meals stay summable.

  fooddb.py search "chicken thigh"      # ranked candidates with per-100g macros
  fooddb.py show 18-504                  # one food's full per-100g breakdown
  fooddb.py add --name "Protein bar, ACME" --kcal 350 --protein 30 \
               --carbs 30 --fat 12 [--satfat 5 --sugars 2 --fibre 8 --salt 0.3]

All values are per 100 g. `add` appends to data/custom-foods.csv (git-tracked).
Use --json on search/show for machine-readable output.
"""
import argparse
import csv
import json
import sys

import _db


def _fmt_row(rec: dict) -> str:
    return (f"{rec['food_code']:<10} {rec['name'][:54]:<54} "
            f"{rec['kcal']:>4.0f}kcal P{rec['protein_g']:<5.1f} "
            f"C{rec['carbs_g']:<5.1f} F{rec['fat_g']:<5.1f}")


def cmd_search(args):
    results = _db.search(args.query, limit=args.limit)
    if args.json:
        print(json.dumps(results, indent=2))
        return
    if not results:
        print(f"No matches for {args.query!r}. "
              f"If it isn't in the table, add it with `fooddb.py add`.")
        return
    print(f"Top {len(results)} matches for {args.query!r} (per 100 g):")
    for rec in results:
        print("  " + _fmt_row(rec))
    print("\nAdd one to a meal with:  meal.py add <week> <meal_id> "
          "--code <food_code> --grams <g>")


def cmd_show(args):
    rec = _db.get(args.code)
    if not rec:
        print(f"No food with code {args.code!r}", file=sys.stderr)
        sys.exit(1)
    if args.json:
        print(json.dumps(rec, indent=2))
        return
    print(f"{rec['name']}  [{rec['food_code']}]  (per 100 g)")
    for n in _db.NUTRIENTS:
        print(f"  {_db.NUTRIENT_LABELS[n]:<12} {rec[n]}")


def _next_custom_code() -> str:
    n = 0
    if _db.CUSTOM_CSV.exists():
        with _db.CUSTOM_CSV.open(newline="", encoding="utf-8") as f:
            n = sum(1 for _ in csv.reader(f)) - 1  # minus header
    return f"custom-{max(n, 0) + 1:03d}"


def cmd_add(args):
    code = _next_custom_code()
    rec = {
        "food_code": code, "name": args.name.strip(), "group": "CUSTOM",
        "kcal": args.kcal, "protein_g": args.protein, "fat_g": args.fat,
        "satfat_g": args.satfat, "carbs_g": args.carbs, "sugars_g": args.sugars,
        "fibre_g": args.fibre, "salt_g": args.salt,
    }
    new_file = not _db.CUSTOM_CSV.exists()
    with _db.CUSTOM_CSV.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=_db.CUSTOM_HEADER)
        if new_file:
            w.writeheader()
        w.writerow(rec)
    print(f"Added {code}: {rec['name']} (per 100 g, "
          f"{rec['kcal']}kcal P{rec['protein_g']} C{rec['carbs_g']} F{rec['fat_g']})")


def main():
    p = argparse.ArgumentParser(description="Search/extend the food database.")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="rank foods by a free-text query")
    s.add_argument("query")
    s.add_argument("--limit", type=int, default=12)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_search)

    sh = sub.add_parser("show", help="full per-100g breakdown for one food code")
    sh.add_argument("code")
    sh.add_argument("--json", action="store_true")
    sh.set_defaults(func=cmd_show)

    a = sub.add_parser("add", help="append a custom food (per 100 g)")
    a.add_argument("--name", required=True)
    a.add_argument("--kcal", type=float, required=True)
    a.add_argument("--protein", type=float, required=True)
    a.add_argument("--carbs", type=float, required=True)
    a.add_argument("--fat", type=float, required=True)
    a.add_argument("--satfat", type=float, default=0)
    a.add_argument("--sugars", type=float, default=0)
    a.add_argument("--fibre", type=float, default=0)
    a.add_argument("--salt", type=float, default=0)
    a.set_defaults(func=cmd_add)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
