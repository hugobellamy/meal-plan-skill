# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "openpyxl"]
# ///
"""Build the lean, greppable food database (data/foods.csv) from the McCance &
Widdowson Composition of Foods Integrated Dataset (CoFID) 2021 source workbook.

One-off build step. The runtime tools (tools/*.py) read the produced foods.csv
with the standard library only — they never import pandas. Re-run this only when
refreshing the source data:

    uv run scripts/build_db.py

All nutrient values are per 100 g of food, matching the source convention.
Trace ('Tr') and not-measured ('N') values are coerced to 0.
"""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "source" / "McCance_CoFID_2021.xlsx"
OUT = ROOT / "data" / "foods.csv"

# Source column -> our lean column name. All per 100 g.
PROX_COLS = {
    "Food Code": "food_code",
    "Food Name": "name",
    "Group": "group",
    "Energy (kcal) (kcal)": "kcal",
    "Protein (g)": "protein_g",
    "Fat (g)": "fat_g",
    "Satd FA /100g fd (g)": "satfat_g",
    "Carbohydrate (g)": "carbs_g",
    "Total sugars (g)": "sugars_g",
    "AOAC fibre (g)": "fibre_g_aoac",
    "NSP (g)": "fibre_g_nsp",
}
NUM_COLS = ["kcal", "protein_g", "fat_g", "satfat_g", "carbs_g",
            "sugars_g", "fibre_g_aoac", "fibre_g_nsp", "sodium_mg"]


def main():
    prox = pd.read_excel(SRC, sheet_name="1.3 Proximates", header=0, skiprows=[1, 2])
    df = prox[list(PROX_COLS)].rename(columns=PROX_COLS).copy()

    # Sodium lives on the Inorganics sheet; its food-code column is unnamed (' ').
    inorg = pd.read_excel(SRC, sheet_name="1.4 Inorganics", header=0, skiprows=[1, 2])
    inorg = inorg.rename(columns={inorg.columns[0]: "food_code"})
    df = df.merge(inorg[["food_code", "Sodium (mg)"]].rename(
        columns={"Sodium (mg)": "sodium_mg"}), on="food_code", how="left")

    # Coerce nutrients: 'Tr' (trace) and 'N' (not measured) -> NaN -> 0.
    for c in NUM_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    # Prefer AOAC fibre (the modern standard); fall back to NSP where AOAC is 0.
    df["fibre_g"] = df["fibre_g_aoac"].where(df["fibre_g_aoac"] > 0, df["fibre_g_nsp"])
    # Salt (g) = sodium (mg) * 2.5 / 1000.
    df["salt_g"] = df["sodium_mg"] * 2.5 / 1000

    df = df.dropna(subset=["name"])
    df["name"] = df["name"].str.strip()
    df = df[df["name"] != ""].reset_index(drop=True)

    out = df[["food_code", "name", "group", "kcal", "protein_g", "fat_g",
              "satfat_g", "carbs_g", "sugars_g", "fibre_g", "salt_g"]].copy()
    out["kcal"] = out["kcal"].round().astype(int)
    for c in ["protein_g", "fat_g", "satfat_g", "carbs_g", "sugars_g", "fibre_g"]:
        out[c] = out[c].round(2)
    out["salt_g"] = out["salt_g"].round(3)

    out.to_csv(OUT, index=False)
    print(f"Wrote {len(out)} foods -> {OUT.relative_to(ROOT)}")
    print(out.head(5).to_string(index=False))


if __name__ == "__main__":
    main()
