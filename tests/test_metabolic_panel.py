from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "metabolic_panel", ROOT / "scripts" / "metabolic_panel.py"
)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _cgm(rows: list[tuple[str, float]]) -> pd.DataFrame:
    df = pd.DataFrame(rows, columns=["timestamp", "glucose_mg_dl"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df


class MetabolicPanelTest(unittest.TestCase):
    def test_gmi_formula(self) -> None:
        self.assertEqual(MODULE.gmi_percent(120.0), 6.18)

    def test_panel_basic_ranges_and_cv(self) -> None:
        rows = [
            (f"2026-08-31T{h:02d}:{m:02d}:00+08:00", g)
            for (h, m, g) in [
                (12, 0, 100), (12, 5, 110), (12, 10, 120),
                (12, 15, 130), (12, 20, 140), (12, 25, 120),
            ]
        ]
        panel = MODULE.build_panel(_cgm(rows), "Asia/Taipei")
        self.assertEqual(panel["n_readings"], 6)
        self.assertEqual(panel["mean_glucose_mg_dl"], 120.0)
        self.assertEqual(panel["tir_70_180_pct"], 100.0)
        self.assertEqual(panel["tbr_lt70_pct"], 0.0)
        self.assertTrue(panel["cv_stable"])
        self.assertLess(panel["cv_pct"], 36.0)

    def test_overnight_window_uses_local_tz(self) -> None:
        # 02:00–03:00 Asia/Taipei is inside the overnight window
        rows = [
            ("2026-08-31T02:00:00+08:00", 95),
            ("2026-08-31T02:30:00+08:00", 105),
            ("2026-08-31T12:00:00+08:00", 150),
        ]
        panel = MODULE.build_panel(_cgm(rows), "Asia/Taipei")
        self.assertEqual(panel["overnight_mean_mg_dl"], 100.0)

    def test_hypo_events_levels(self) -> None:
        rows = [
            ("2026-08-31T03:00:00+08:00", 88),
            ("2026-08-31T03:05:00+08:00", 65),
            ("2026-08-31T03:10:00+08:00", 50),
        ]
        events = MODULE.hypo_events(_cgm(rows))
        self.assertEqual(list(events["level"]), ["level1_lt70", "level2_lt54"])

    def test_no_data_returns_error(self) -> None:
        panel = MODULE.build_panel(_cgm([]).assign(glucose_mg_dl=pd.Series(dtype=float)), "Asia/Taipei")
        self.assertEqual(panel["error"], "NO_DATA")


if __name__ == "__main__":
    unittest.main()
