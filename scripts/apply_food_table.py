#!/usr/bin/env python3
"""Deterministic personal-food-table override for Ai-to-Agent-CGM-v3.

Given a meal record (schemas/meal-record.schema.json) and a personal food table
(schemas/personal-food-table.schema.json), match each food by name / aliases
and, for matches, compute that food's nutrition contribution as a range from the
table's per-100 g values and the confirmed portion range.

This is the deterministic fast path for frequently eaten foods. It does not
replace the Nutrition Matching Agent for unmatched or composite foods, and it
does not turn reference GI into a personal measured response.

Column mapping (table -> meal nutrition_range key):
    carb_per_100g        -> carbs_g
    net_carb_per_100g    -> available_carbs_g
    protein_per_100g     -> protein_g
    fat_per_100g         -> fat_g
    fiber_per_100g       -> fiber_g
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

OVERRIDE_VERSION = "1.0.0"
GI_COVERAGE_MIN = 0.8

FIELDS = {
    "carb_per_100g": "carbs_g",
    "net_carb_per_100g": "available_carbs_g",
    "protein_per_100g": "protein_g",
    "fat_per_100g": "fat_g",
    "fiber_per_100g": "fiber_g",
}
_SPLIT = re.compile(r"[,、;；/]")
_WS = re.compile(r"\s+")


def _norm(value: object) -> str:
    return _WS.sub("", str(value or "").strip().lower())


def _num(value: object) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if result == result else None


def build_index(rows: list[dict]) -> list[dict]:
    index = []
    for row in rows:
        keys = [_norm(row.get("name"))]
        keys += [_norm(a) for a in _SPLIT.split(str(row.get("aliases") or ""))]
        index.append({"keys": [k for k in keys if k], "row": row})
    return index


def lookup(index: list[dict], name: str) -> dict | None:
    n = _norm(name)
    if not n:
        return None
    for entry in index:
        if n in entry["keys"]:
            return entry["row"]
    for entry in index:
        if any(n in k or k in n for k in entry["keys"]):
            return entry["row"]
    return None


def _range(low: float, high: float) -> dict[str, float]:
    return {"low": round(low, 1), "high": round(high, 1)}


def apply_override(meal: dict, table_rows: list[dict]) -> dict:
    index = build_index(table_rows or [])
    foods_out: list[dict] = []
    agg = {key: [0.0, 0.0] for key in FIELDS.values()}
    gi_num = [0.0, 0.0]
    gi_den = [0.0, 0.0]
    matched = 0

    for food in meal.get("foods", []):
        hit = lookup(index, food.get("name", ""))
        new_food = dict(food)
        if hit is None:
            new_food.update(matched_ref=None, source="vision")
            foods_out.append(new_food)
            continue

        matched += 1
        portion_low = _num(food.get("portion_g_low"))
        portion_high = _num(food.get("portion_g_high"))
        if portion_low is None:
            portion_low = _num(hit.get("default_portion_g")) or 0.0
        if portion_high is None:
            portion_high = _num(hit.get("default_portion_g")) or portion_low

        contribution: dict[str, dict] = {}
        for col, key in FIELDS.items():
            per_100g = _num(hit.get(col))
            if per_100g is None:
                continue
            low = per_100g * portion_low / 100.0
            high = per_100g * portion_high / 100.0
            contribution[key] = _range(low, high)
            agg[key][0] += low
            agg[key][1] += high

        if "available_carbs_g" not in contribution and "carbs_g" in contribution:
            contribution["available_carbs_g"] = dict(contribution["carbs_g"])
            agg["available_carbs_g"][0] += contribution["carbs_g"]["low"]
            agg["available_carbs_g"][1] += contribution["carbs_g"]["high"]

        gi = _num(hit.get("gi"))
        if gi is not None and "available_carbs_g" in contribution:
            ac = contribution["available_carbs_g"]
            gi_num[0] += gi * ac["low"]
            gi_num[1] += gi * ac["high"]
            gi_den[0] += ac["low"]
            gi_den[1] += ac["high"]

        new_food.update(
            matched_ref=hit.get("name"),
            source="personal_table",
            nutrition_range=contribution,
        )
        foods_out.append(new_food)

    nutrition_from_table = {k: _range(v[0], v[1]) for k, v in agg.items() if v[1] > 0}

    gi_weighted = None
    gi_source = "none"
    den_mid = (gi_den[0] + gi_den[1]) / 2.0
    if den_mid > 0:
        gi_weighted = round(((gi_num[0] + gi_num[1]) / 2.0) / den_mid)
        meal_ac = meal.get("nutrition_range", {}).get("available_carbs_g")
        coverage = None
        if meal_ac:
            meal_low = _num(meal_ac.get("low"))
            meal_high = _num(meal_ac.get("high"))
            if meal_low is not None and meal_high is not None:
                meal_mid = (meal_low + meal_high) / 2.0
                coverage = den_mid / meal_mid if meal_mid else None
        gi_source = (
            "personal_table"
            if coverage is not None and coverage >= GI_COVERAGE_MIN
            else "partial"
        )

    gl_from_table = None
    if gi_weighted is not None and "available_carbs_g" in nutrition_from_table:
        ac = nutrition_from_table["available_carbs_g"]
        gl_from_table = _range(gi_weighted * ac["low"] / 100.0, gi_weighted * ac["high"] / 100.0)

    result = dict(meal)
    result["foods"] = foods_out
    result["personal_table_override"] = {
        "override_version": OVERRIDE_VERSION,
        "matched_foods": matched,
        "total_foods": len(meal.get("foods", [])),
        "nutrition_range_from_table": nutrition_from_table,
        "gi_weighted": gi_weighted,
        "gi_source": gi_source,
        "estimated_gl_from_table": gl_from_table,
    }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--meal", required=True, type=Path)
    parser.add_argument("--table", required=True, type=Path, help="personal food table JSON array")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    meal = json.loads(args.meal.read_text(encoding="utf-8"))
    table = json.loads(args.table.read_text(encoding="utf-8"))
    result = apply_override(meal, table)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    override = result["personal_table_override"]
    print(
        f"matched {override['matched_foods']}/{override['total_foods']} food(s); "
        f"wrote {args.output}"
    )


if __name__ == "__main__":
    main()
