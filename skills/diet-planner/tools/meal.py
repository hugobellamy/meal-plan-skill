#!/usr/bin/env python3
"""meal — build and inspect meal objects from real database foods.

A meal is a list of (food_code, grams) items. The macros are never guessed: every
total is summed from the McCance rows. Workflow:

  meal.py new 1 beef-hash --name "Cowboy Beef & Potato Hash" --portions 4 --type batch
  meal.py add 1 beef-hash --code 18-507 --grams 500     # find codes via fooddb.py
  meal.py add 1 beef-hash --code 11-858 --grams 800
  meal.py set 1 beef-hash --code 11-858 --grams 1000    # change an amount
  meal.py rm  1 beef-hash --code 11-858                 # remove an item
  meal.py show 1 beef-hash                              # summed totals + per portion
  meal.py list 1                                        # all meals in the week
  meal.py schedule 1 beef-hash --eat-on "Mon Lunch" "Mon Dinner"

Grams are TOTAL cooked grams (household). Per-portion = total / portions, and is
what the user actually eats — the meal plan tracks per-portion.
"""
import argparse
import json
import sys

import _db
import _state


def _get_food_or_die(code: str) -> dict:
    rec = _db.get(code)
    if rec is None:
        print(f"No food with code {code!r}. Search with `fooddb.py search ...` "
              f"or create it with `fooddb.py add`.", file=sys.stderr)
        sys.exit(1)
    return rec


def cmd_new(args):
    if _state.meal_path(args.week, args.meal_id).exists():
        print(f"Meal {args.meal_id!r} already exists; edit it with add/set/rm.",
              file=sys.stderr)
        sys.exit(1)
    meal = {
        "meal_id": args.meal_id,
        "name": args.name or args.meal_id,
        "portions": args.portions,
        "type": args.type,
        "eat_on": args.eat_on or [],
        "items": [],
    }
    p = _state.save_meal(args.week, meal)
    print(f"Created {p}  ({meal['name']}, {meal['portions']} portion(s))")


def cmd_add(args):
    meal = _state.load_meal(args.week, args.meal_id)
    rec = _get_food_or_die(args.code)
    for it in meal["items"]:
        if it["food_code"] == args.code:
            print(f"{args.code} already in meal; use `set` to change its amount.",
                  file=sys.stderr)
            sys.exit(1)
    meal["items"].append({
        "food_code": args.code, "name": rec["name"],
        "grams": args.grams, "note": args.note or "",
    })
    _state.save_meal(args.week, meal)
    _show(meal)


def cmd_set(args):
    meal = _state.load_meal(args.week, args.meal_id)
    for it in meal["items"]:
        if it["food_code"] == args.code:
            it["grams"] = args.grams
            _state.save_meal(args.week, meal)
            _show(meal)
            return
    print(f"{args.code} not in meal {args.meal_id!r}; add it first.", file=sys.stderr)
    sys.exit(1)


def cmd_rm(args):
    meal = _state.load_meal(args.week, args.meal_id)
    before = len(meal["items"])
    meal["items"] = [it for it in meal["items"] if it["food_code"] != args.code]
    if len(meal["items"]) == before:
        print(f"{args.code} not in meal {args.meal_id!r}.", file=sys.stderr)
        sys.exit(1)
    _state.save_meal(args.week, meal)
    _show(meal)


def cmd_schedule(args):
    meal = _state.load_meal(args.week, args.meal_id)
    if args.portions is not None:
        meal["portions"] = args.portions
    if args.type is not None:
        meal["type"] = args.type
    if args.eat_on is not None:
        meal["eat_on"] = args.eat_on
    _state.save_meal(args.week, meal)
    print(f"Updated {meal['meal_id']}: portions={meal['portions']}, "
          f"type={meal.get('type')}, eat_on={meal.get('eat_on')}")


def _show(meal: dict, as_json: bool = False):
    totals = _state.meal_totals(meal)
    pp = _state.per_portion(totals, meal.get("portions", 1))
    if as_json:
        print(json.dumps({
            "meal": meal,
            "totals_household": _db.round_totals(totals),
            "per_portion": _db.round_totals(pp),
        }, indent=2))
        return
    print(f"\n{meal['name']}  [{meal['meal_id']}]  "
          f"{meal.get('portions', 1)} portion(s), type={meal.get('type', '-')}")
    if meal.get("eat_on"):
        print(f"  eaten: {', '.join(meal['eat_on'])}")
    print(f"  {'food':<46}{'grams':>7}{'kcal':>7}{'P':>7}{'C':>7}{'F':>7}")
    for it in meal["items"]:
        rec = _get_food_or_die(it["food_code"])
        s = _db.scale(rec, it["grams"])
        print(f"  {it['name'][:44]:<46}{it['grams']:>7.0f}{s['kcal']:>7.0f}"
              f"{s['protein_g']:>7.1f}{s['carbs_g']:>7.1f}{s['fat_g']:>7.1f}")
    rt = _db.round_totals(totals)
    rp = _db.round_totals(pp)
    print(f"  {'TOTAL (household)':<46}{'':>7}{rt['kcal']:>7.0f}"
          f"{rt['protein_g']:>7.1f}{rt['carbs_g']:>7.1f}{rt['fat_g']:>7.1f}")
    print(f"  {'PER PORTION':<46}{'':>7}{rp['kcal']:>7.0f}"
          f"{rp['protein_g']:>7.1f}{rp['carbs_g']:>7.1f}{rp['fat_g']:>7.1f}")
    print(f"  (per portion also: SatFat {rp['satfat_g']}g, Sugars {rp['sugars_g']}g, "
          f"Fibre {rp['fibre_g']}g, Salt {rp['salt_g']}g)")


def cmd_show(args):
    _show(_state.load_meal(args.week, args.meal_id), as_json=args.json)


def cmd_list(args):
    meals = _state.list_meals(args.week)
    if not meals:
        print(f"No meals yet in {_state.normalize_week(args.week)}.")
        return
    print(f"{_state.normalize_week(args.week)}: {len(meals)} meal(s)")
    for m in meals:
        pp = _db.round_totals(_state.per_portion(
            _state.meal_totals(m), m.get("portions", 1)))
        print(f"  {m['meal_id']:<22} {m['name'][:34]:<34} "
              f"{pp['kcal']:>4.0f}kcal/portion  P{pp['protein_g']}")


def main():
    p = argparse.ArgumentParser(description="Build/inspect meal objects.")
    sub = p.add_subparsers(dest="cmd", required=True)

    n = sub.add_parser("new")
    n.add_argument("week"); n.add_argument("meal_id")
    n.add_argument("--name"); n.add_argument("--portions", type=int, default=1)
    n.add_argument("--type", default="single")
    n.add_argument("--eat-on", nargs="*", dest="eat_on")
    n.set_defaults(func=cmd_new)

    a = sub.add_parser("add")
    a.add_argument("week"); a.add_argument("meal_id")
    a.add_argument("--code", required=True); a.add_argument("--grams", type=float, required=True)
    a.add_argument("--note")
    a.set_defaults(func=cmd_add)

    s = sub.add_parser("set")
    s.add_argument("week"); s.add_argument("meal_id")
    s.add_argument("--code", required=True); s.add_argument("--grams", type=float, required=True)
    s.set_defaults(func=cmd_set)

    r = sub.add_parser("rm")
    r.add_argument("week"); r.add_argument("meal_id"); r.add_argument("--code", required=True)
    r.set_defaults(func=cmd_rm)

    sc = sub.add_parser("schedule", help="update portions/type/eat-on")
    sc.add_argument("week"); sc.add_argument("meal_id")
    sc.add_argument("--portions", type=int); sc.add_argument("--type")
    sc.add_argument("--eat-on", nargs="*", dest="eat_on")
    sc.set_defaults(func=cmd_schedule)

    sh = sub.add_parser("show")
    sh.add_argument("week"); sh.add_argument("meal_id"); sh.add_argument("--json", action="store_true")
    sh.set_defaults(func=cmd_show)

    ls = sub.add_parser("list"); ls.add_argument("week"); ls.set_defaults(func=cmd_list)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
