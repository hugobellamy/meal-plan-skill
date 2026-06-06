#!/usr/bin/env python3
"""shopping — build the shopping list in two automated halves with the LLM in
the middle doing only the judgement step (grouping / shop-friendly labels).

  shopping.py extract 1     # auto: aggregate every meal's ingredients -> shopping.json
  # --- LLM step: edit shopping.json — set each item's "category", and tweak
  #     "buy_as"/"qty" into shop-friendly terms (raw weights, pack sizes) ---
  shopping.py render 1      # auto: shopping.json -> shopping-list.md, grouped

The extract half sums grams per food across all meals (household totals). The
render half just groups and formats — no nutrition guessing anywhere.
"""
import argparse
import json

import _state


def _qty_str(grams: float) -> str:
    return f"{grams / 1000:.2f} kg" if grams >= 1000 else f"{grams:.0f} g"


def cmd_extract(args):
    meals = _state.list_meals(args.week)
    agg: dict[str, dict] = {}
    for meal in meals:
        for it in meal["items"]:
            code = it["food_code"]
            entry = agg.setdefault(code, {
                "food_code": code, "name": it["name"], "grams": 0.0,
                "from_meals": [],
            })
            entry["grams"] += it["grams"]
            if meal["meal_id"] not in entry["from_meals"]:
                entry["from_meals"].append(meal["meal_id"])

    items = []
    for e in sorted(agg.values(), key=lambda x: x["name"].lower()):
        items.append({
            "food_code": e["food_code"],
            "name": e["name"],
            "grams": round(e["grams"], 1),
            "qty": _qty_str(e["grams"]),     # editable: change to pack-friendly text
            "buy_as": e["name"],             # editable: shop-friendly label
            "category": "",                  # FILL IN: Meat, Produce, Dairy, ...
            "from_meals": e["from_meals"],
        })

    doc = {
        "week": _state.normalize_week(args.week),
        "instructions": ("Set a 'category' for every item (e.g. Meat, Fish, "
                         "Produce, Dairy & Eggs, Frozen, Pantry, Other). Optionally "
                         "edit 'buy_as' to a shop-friendly name and 'qty' to a "
                         "purchase-friendly amount (raw weight / pack size). Then "
                         "run `shopping.py render`."),
        "items": items,
    }
    path = _state.week_dir(args.week, create=True) / "shopping.json"
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {path} — {len(items)} ingredient(s). "
          f"Now group them (set 'category'), then run `shopping.py render {args.week}`.")


def cmd_render(args):
    path = _state.week_dir(args.week) / "shopping.json"
    if not path.exists():
        raise SystemExit(f"No {path}. Run `shopping.py extract {args.week}` first.")
    doc = json.loads(path.read_text(encoding="utf-8"))

    groups: dict[str, list[dict]] = {}
    for it in doc["items"]:
        cat = (it.get("category") or "").strip() or "Uncategorised"
        groups.setdefault(cat, []).append(it)

    wk = _state.normalize_week(args.week)
    out = [f"# Shopping List — {wk.replace('-', ' ').title()}", "",
           "_Household totals for everything cooked this week._", ""]
    # Stable, sensible category order; unknown categories follow alphabetically.
    preferred = ["Meat", "Fish", "Produce", "Dairy & Eggs", "Frozen", "Pantry",
                 "Bakery", "Other"]
    ordered = [c for c in preferred if c in groups]
    ordered += sorted(c for c in groups if c not in preferred and c != "Uncategorised")
    if "Uncategorised" in groups:
        ordered.append("Uncategorised")

    for cat in ordered:
        out += [f"## {cat}", ""]
        for it in sorted(groups[cat], key=lambda x: x.get("buy_as", x["name"]).lower()):
            label = it.get("buy_as") or it["name"]
            qty = it.get("qty") or _qty_str(it["grams"])
            out.append(f"- [ ] {qty} — {label}")
        out.append("")

    path_md = _state.week_dir(args.week) / "shopping-list.md"
    path_md.write_text("\n".join(out) + "\n", encoding="utf-8")
    n = sum(len(v) for v in groups.values())
    print(f"Wrote {path_md} — {n} item(s) in {len(groups)} group(s).")
    if "Uncategorised" in groups:
        print(f"  Note: {len(groups['Uncategorised'])} item(s) had no category.")


def main():
    p = argparse.ArgumentParser(description="Two-part shopping list builder.")
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("extract"); e.add_argument("week"); e.set_defaults(func=cmd_extract)
    r = sub.add_parser("render"); r.add_argument("week"); r.set_defaults(func=cmd_render)
    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
