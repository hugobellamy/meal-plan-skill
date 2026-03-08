# Diet Planner — Agent Skill

Evidence-based diet planning skill for [Claude Code](https://claude.com/claude-code), [OpenCode](https://opencode.ai), and [OpenClaw](https://openclaw.com). Creates personalised weekly meal plans with recipes, macro tracking, and shopping lists.

## What it does

Runs a setup conversation to build your profile (stats, goals, preferences, restrictions), then generates weekly meal plans with per-recipe macro breakdowns, household-scaled recipes, and shopping lists. Adapts over time based on your feedback and progress. Food choices are guided by reference docs covering sports nutrition, gut health, and vegetarian/vegan needs — loaded automatically based on your profile.

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

## Key features

- **Household-aware** — recipes and shopping lists scale for everyone you cook for; calorie tracking stays individual
- **Macro verification** — every recipe includes an ingredient-by-ingredient breakdown table that must add up
- **Pack size tracking** — tell the agent your shop's pack sizes to reduce waste
- **Feedback loop** — mention what worked or didn't and the agent remembers

## File structure

```
diet-planner/
├── SKILL.md                    # Main skill definition
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

## Model nutrition accuracy

R² scores from the [Food Nutrition Benchmark](https://github.com/hugobellamy/food-data-benchmark) — how well each LLM estimates calories and macros from food descriptions without internet access.

| Model                  |   Calories |   Protein |    Fat |   Carbs |   Mean R² |
|:-----------------------|-----------:|----------:|-------:|--------:|----------:|
| gemini-3-flash-preview |     0.8806 |    0.893  | 0.8736 |  0.8164 |    0.8659 |
| claude-sonnet-4.6      |     0.8273 |    0.7747 | 0.8253 |  0.7823 |    0.8024 |
| claude-haiku-4.5       |     0.6371 |    0.6205 | 0.7459 |  0.6861 |    0.6724 |
| qwen3-235b-a22b-2507   |     0.6664 |    0.5876 | 0.62   |  0.6314 |    0.6264 |

See the [full benchmark](https://github.com/hugobellamy/food-data-benchmark) for soft vs raw prompt breakdowns and methodology.

## Research sources

Reference docs are distilled from peer-reviewed research: Iraki et al. 2019, Helms et al. 2023, Morton et al. 2018 (sports nutrition); Stanford FeFiFo Study (Cell, 2021), American Gut Project (gut microbiome); Rogerson 2017, Hevia-Larrain et al. 2021 (vegetarian/vegan); Neurology 2024 on UPFs, Framingham Offspring Cohort on choline, and multiple systematic reviews.

