# Food database source

`../foods.csv` is built from **McCance & Widdowson's *The Composition of Foods
Integrated Dataset* (CoFID) 2021** — the UK national food-composition database
(Public Health England / Department of Health), values per 100 g.

The source workbook (`McCance_CoFID_2021.xlsx`, ~4.6 MB) is git-ignored to keep
the repo lean. To rebuild `foods.csv`, fetch it and run the build script:

```bash
curl -sL -o data/source/McCance_CoFID_2021.xlsx \
  "https://raw.githubusercontent.com/hugobellamy/food-data-benchmark/main/data/source/McCance_Widdowsons_Composition_of_Foods_Integrated_Dataset_2021..xlsx"
uv run scripts/build_db.py
```

The official source is also available from the UK government:
https://www.gov.uk/government/publications/composition-of-foods-integrated-dataset-cofid

User-added foods (`fooddb.py add`) live in a `custom-foods.csv` in the user's own
project directory — not here in the skill. They're merged on top of `foods.csv`
at runtime, so they survive both rebuilds and skill updates.
