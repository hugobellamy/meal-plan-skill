# Diet Planner — Agent Skill

Diet planning skill for [Claude Code](https://claude.com/claude-code), [OpenCode](https://opencode.ai), and [OpenClaw](https://openclaw.com). Creates weekly meal plans based on custom requirments with recipes, macro tracking, and shopping lists.

## What it does

Runs a setup conversation to build your profile, then generates weekly meal plans with per-recipe macro breakdowns, household-scaled recipes, and shopping lists. Adapts over time based on your feedback and progress. Food choices are guided by reference docs covering sports nutrition, gut health, and vegetarian/vegan needs.

**Macros are database-grounded, not estimated.** Instead of the model guessing calories and macros, it picks real foods and amounts from the McCance & Widdowson CoFID 2021 (UK) food-composition database, and small standard-library Python tools sum the numbers from the actual per-100g rows. The model's job is *which food and how much*; the arithmetic is the tool's. The meal-plan totals and the recipe macro tables are computed from the same meal objects, so they're consistent by construction.

## Install

Clone into your skills directory:

```bash
# Claude Code
git clone https://github.com/hugobellamy/diet-planner ~/.claude/skills/diet-planner

# OpenCode (also searches ~/.claude/skills/ and ~/.agents/skills/)
git clone https://github.com/hugobellamy/diet-planner ~/.config/opencode/skills/diet-planner

# OpenClaw
git clone https://github.com/hugobellamy/diet-planner ~/.openclaw/skills/diet-planner
```

Then start a new session and say something like "help me plan my meals for the week".

## Reference docs

Loaded automatically based on your profile tags:

| Doc | When | Covers |
|-----|------|--------|
| `general-health.md` | Always | UPF avoidance, fat quality, micronutrients, satiety, hydration |
| `sports-performance.md` | Training/body comp goals | Protein targets, carb timing, supplements |
| `gut-microbiome.md` | Gut health goals | 30 plants/week, fermented foods, resistant starch, prebiotics |
| `vegetarian.md` | Vegetarian users | Protein quality, iron/B12/omega-3/zinc, creatine |
| `vegan.md` | Vegan users | Mandatory supplements, protein combining, calcium, iodine |


## File structure

```
diet-planner/
├── SKILL.md                    # Main skill definition
├── tools/                      # Database-grounded planning tools (stdlib Python)
│   ├── fooddb.py               #   search / show / add foods
│   ├── meal.py                 #   build & inspect meal objects
│   ├── week.py                 #   daily/weekly totals vs target
│   ├── build.py                #   render meal-plan.md & recipes.md
│   ├── shopping.py             #   two-part shopping list
│   └── _db.py / _state.py      #   shared helpers
├── data/
│   ├── foods.csv               # McCance CoFID 2021, per 100 g (committed)
│   └── source/SOURCE.md        # how to rebuild foods.csv
├── scripts/
│   └── build_db.py             # foods.csv builder (run with: uv run)
├── docs/                       # Evidence-based reference docs
│   ├── general-health.md
│   ├── sports-performance.md
│   ├── gut-microbiome.md
│   ├── vegetarian.md
│   ├── vegan.md
│   └── tips.md
└── templates/
    └── profile-template.md
```

## Why database-grounding — measured

The [Food Nutrition Benchmark](https://github.com/hugobellamy/food-data-benchmark)
compares the same models *guessing* macros vs using the database-grounded
workflow this skill is built on (decompose → search → pick the matching entry and
weight → sum). Mean R² (higher is better) on the same 50 test meals:

| Model | Without tool (guess) | With tool | Δ |
|:------|-----------:|---------:|------:|
| gemma-4-31b (local) | 0.937 | **0.985** | +0.05 |
| gemini-3.5-flash | 0.948 | **0.984** | +0.04 |
| claude-sonnet-4.6 | 0.825 | **0.987** | +0.16 |
| claude-haiku-4.5 | 0.776 | **0.923** | +0.15 |
| qwen3-235b-a22b-2507 | 0.736 | **0.985** | +0.25 |

**The tool helps every model, most where the model is weakest.** Without it the
models spread from 0.74 to 0.95; with it they converge to ~0.92–0.99 — the
database equalizes nutrition knowledge, so a cheap model with the tool matches an
expensive one. The biggest single lever is matching the food's *form* (canned vs
dried, boiled vs raw) and weighing on that entry's basis.

> Absolute with-tool scores are an optimistic upper bound — the benchmark's test
> foods are themselves drawn from the McCance database the tool searches. The
> *within-model improvement* (Δ) is a controlled experiment and is consistently
> positive. See the [full benchmark](https://github.com/hugobellamy/food-data-benchmark)
> for methodology, the leakage caveat, and the estimate-only baselines.

## Research sources

Reference docs are distilled from peer-reviewed research: Iraki et al. 2019, Helms et al. 2023, Morton et al. 2018 (sports nutrition); Stanford FeFiFo Study (Cell, 2021), American Gut Project (gut microbiome); Rogerson 2017, Hevia-Larrain et al. 2021 (vegetarian/vegan); Neurology 2024 on UPFs, Framingham Offspring Cohort on choline, and multiple systematic reviews.

