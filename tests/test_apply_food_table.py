from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "apply_food_table", ROOT / "scripts" / "apply_food_table.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

TABLE = json.loads((ROOT / "examples" / "personal-food-table.json").read_text(encoding="utf-8"))


class ApplyFoodTableTest(unittest.TestCase):
    def test_alias_match_computes_range_from_per_100g(self) -> None:
        meal = {
            "foods": [
                {"name": "熟白飯", "portion_g_low": 100, "portion_g_high": 200, "confidence": 0.8}
            ],
            "nutrition_range": {"available_carbs_g": {"low": 27, "high": 55}},
        }
        out = MODULE.apply_override(meal, TABLE)
        food = out["foods"][0]
        self.assertEqual(food["source"], "personal_table")
        self.assertEqual(food["matched_ref"], "白飯")
        # carb_per_100g 28 -> 100 g = 28.0, 200 g = 56.0
        self.assertEqual(food["nutrition_range"]["carbs_g"], {"low": 28.0, "high": 56.0})
        ov = out["personal_table_override"]
        self.assertEqual(ov["matched_foods"], 1)
        self.assertEqual(ov["gi_weighted"], 73)
        self.assertEqual(ov["gi_source"], "personal_table")  # coverage >= 0.8

    def test_no_match_passthrough(self) -> None:
        meal = {"foods": [{"name": "牛肉麵", "portion_g_low": 300, "portion_g_high": 500}]}
        out = MODULE.apply_override(meal, TABLE)
        self.assertEqual(out["foods"][0]["source"], "vision")
        self.assertIsNone(out["foods"][0]["matched_ref"])
        self.assertEqual(out["personal_table_override"]["matched_foods"], 0)
        self.assertIsNone(out["personal_table_override"]["gi_weighted"])

    def test_partial_gi_coverage_flagged(self) -> None:
        meal = {
            "foods": [{"name": "白飯", "portion_g_low": 100, "portion_g_high": 100}],
            "nutrition_range": {"available_carbs_g": {"low": 100, "high": 140}},
        }
        out = MODULE.apply_override(meal, TABLE)
        # table available carbs ~27.6 vs meal midpoint 120 -> coverage ~0.23 < 0.8
        self.assertEqual(out["personal_table_override"]["gi_source"], "partial")

    def test_default_portion_used_when_missing(self) -> None:
        meal = {"foods": [{"name": "無糖豆漿"}]}
        out = MODULE.apply_override(meal, TABLE)
        food = out["foods"][0]
        # default_portion_g 260, carb_per_100g 1.8 -> 4.68 -> 4.7 both ends
        self.assertEqual(food["nutrition_range"]["carbs_g"], {"low": 4.7, "high": 4.7})

    def test_gl_from_table_computed(self) -> None:
        meal = {
            "foods": [{"name": "白飯", "portion_g_low": 150, "portion_g_high": 150}],
            "nutrition_range": {"available_carbs_g": {"low": 40, "high": 45}},
        }
        out = MODULE.apply_override(meal, TABLE)
        ov = out["personal_table_override"]
        ac = ov["nutrition_range_from_table"]["available_carbs_g"]
        expected_low = round(ov["gi_weighted"] * ac["low"] / 100.0, 1)
        self.assertEqual(ov["estimated_gl_from_table"]["low"], expected_low)


if __name__ == "__main__":
    unittest.main()
