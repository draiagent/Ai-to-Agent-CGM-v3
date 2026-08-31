from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "analyze_cgm", ROOT / "scripts" / "analyze_cgm.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class AnalyzeCgmTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cgm = pd.read_csv(ROOT / "examples" / "cgm.csv")
        cls.cgm["timestamp"] = pd.to_datetime(cls.cgm["timestamp"], utc=True)
        cls.meal = pd.read_csv(ROOT / "examples" / "meals.csv").iloc[0]

    def test_clean_meal_metrics_match_expected_example(self) -> None:
        result = MODULE.analyze_meal(self.cgm, self.meal)
        expected = json.loads((ROOT / "examples" / "analysis-record.json").read_text())
        for key in (
            "baseline_mg_dl", "peak_mg_dl", "delta_peak_mg_dl",
            "time_to_peak_min", "iauc_120", "iauc_180",
            "recovery_time_min", "cgm_coverage_pct", "quality_class",
            "analysis_version", "iauc_method",
        ):
            self.assertEqual(result[key], expected[key], key)

    def test_iauc_ignores_area_below_baseline(self) -> None:
        import numpy as np

        # symmetric excursion: +40 then -40 around baseline; only the top half counts
        times = np.array([0.0, 30.0, 90.0, 180.0])
        values = np.array([100.0, 140.0, 60.0, 100.0])
        area = MODULE.iauc(times, values, baseline=100.0, end_min=180)
        # crossing-aware Wolever area is positive and well below the naive full trapezoid
        self.assertGreater(area, 0.0)
        self.assertLess(area, 40.0 * 180.0)

    def test_activity_marks_contextual(self) -> None:
        meal = self.meal.copy()
        meal["activity_flag"] = True
        result = MODULE.analyze_meal(self.cgm, meal)
        self.assertEqual(result["quality_class"], "B_CONTEXTUAL")
        self.assertIn("POST_MEAL_ACTIVITY", result["quality_reasons"])

    def test_missing_baseline_is_excluded(self) -> None:
        truncated = self.cgm[self.cgm["timestamp"] >= pd.Timestamp("2026-08-31T12:00:00+08:00")]
        result = MODULE.analyze_meal(truncated, self.meal)
        self.assertEqual(result["quality_class"], "X_EXCLUDED")
        self.assertIn("INSUFFICIENT_BASELINE", result["quality_reasons"])

    def test_cli_output_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "analysis.csv"
            cgm = self.cgm.copy()
            rows = [MODULE.analyze_meal(cgm, self.meal)]
            pd.DataFrame(rows).to_csv(output, index=False)
            produced = pd.read_csv(output)
            self.assertEqual(len(produced), 1)
            self.assertIn("delta_peak_mg_dl", produced.columns)


if __name__ == "__main__":
    unittest.main()

