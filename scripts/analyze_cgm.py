#!/usr/bin/env python3
"""Deterministic meal-aligned CGM metrics for Ai-to-Agent-CGM-v1.

Input cgm.csv: timestamp,glucose_mg_dl
Input meals.csv: meal_id,meal_start_at,overlap_flag,activity_flag,sensor_issue_flag
All timestamps must be timezone-aware ISO 8601 values.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ANALYSIS_VERSION = "1.1.0"
IAUC_METHOD = "wolever_incremental"
BASELINE_START_MIN = -15
BASELINE_END_MIN = -5
WINDOW_MIN = 180
RECOVERY_TOLERANCE_MG_DL = 5.0
RECOVERY_HOLD_MIN = 15
MIN_COVERAGE_PCT = 80.0


def parse_bool(value: object) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def iauc(times_min: np.ndarray, values: np.ndarray, baseline: float, end_min: int) -> float:
    """Incremental AUC above baseline (Wolever method).

    Only area above the pre-meal baseline is counted. Where a segment crosses
    the baseline, only the triangular portion above baseline contributes; area
    below baseline is ignored, never subtracted. Units: mg/dL * min.
    """
    mask = (times_min >= 0) & (times_min <= end_min)
    x = times_min[mask].astype(float)
    g = values[mask].astype(float) - baseline
    if len(x) < 2:
        return float("nan")
    area = 0.0
    for i in range(len(x) - 1):
        dt = x[i + 1] - x[i]
        if dt <= 0:
            continue
        a, b = g[i], g[i + 1]
        if a >= 0 and b >= 0:
            area += 0.5 * (a + b) * dt
        elif a <= 0 and b <= 0:
            continue
        elif a > 0:  # positive -> negative crossing
            area += 0.5 * a * (dt * (a / (a - b)))
        else:  # negative -> positive crossing
            area += 0.5 * b * (dt * (b / (b - a)))
    return float(area)


def recovery_time(times_min: np.ndarray, values: np.ndarray, baseline: float) -> float | None:
    rose = values - baseline >= 10.0
    if not rose.any():
        return None
    first_rise = int(np.argmax(rose))
    for idx in range(first_rise + 1, len(times_min)):
        start = times_min[idx]
        end = start + RECOVERY_HOLD_MIN
        hold = (times_min >= start) & (times_min <= end)
        if hold.sum() < 2 or times_min[hold][-1] < end:
            continue
        if np.all(np.abs(values[hold] - baseline) <= RECOVERY_TOLERANCE_MG_DL):
            return float(start)
    return None


def analyze_meal(cgm: pd.DataFrame, meal: pd.Series) -> dict[str, object]:
    t0 = pd.Timestamp(meal["meal_start_at"])
    if t0.tzinfo is None:
        raise ValueError(f"meal_start_at must include timezone: {meal['meal_id']}")

    rel = (cgm["timestamp"] - t0).dt.total_seconds() / 60.0
    baseline_mask = (rel >= BASELINE_START_MIN) & (rel <= BASELINE_END_MIN)
    post_mask = (rel >= 0) & (rel <= WINDOW_MIN)
    baseline_values = cgm.loc[baseline_mask, "glucose_mg_dl"].dropna()
    post = cgm.loc[post_mask, ["timestamp", "glucose_mg_dl"]].dropna().copy()
    post["minutes"] = rel[post_mask][post.index]

    reasons: list[str] = []
    if len(baseline_values) < 2:
        reasons.append("INSUFFICIENT_BASELINE")
    if len(post) < 2:
        reasons.append("INSUFFICIENT_POST_MEAL_DATA")

    expected_points = WINDOW_MIN / 5 + 1
    coverage_pct = min(100.0, 100.0 * len(post) / expected_points)
    if coverage_pct < MIN_COVERAGE_PCT:
        reasons.append("LOW_CGM_COVERAGE")
    if parse_bool(meal.get("overlap_flag", False)):
        reasons.append("OVERLAPPING_INTAKE")
    if parse_bool(meal.get("activity_flag", False)):
        reasons.append("POST_MEAL_ACTIVITY")
    if parse_bool(meal.get("sensor_issue_flag", False)):
        reasons.append("SENSOR_ANOMALY")

    fatal = {"INSUFFICIENT_BASELINE", "INSUFFICIENT_POST_MEAL_DATA", "LOW_CGM_COVERAGE", "SENSOR_ANOMALY"}
    if fatal.intersection(reasons):
        quality = "X_EXCLUDED"
    elif reasons:
        quality = "B_CONTEXTUAL"
    else:
        quality = "A_CLEAN"

    result: dict[str, object] = {
        "meal_id": meal["meal_id"],
        "cgm_coverage_pct": round(coverage_pct, 1),
        "quality_class": quality,
        "quality_reasons": "|".join(reasons),
        "analysis_version": ANALYSIS_VERSION,
        "iauc_method": IAUC_METHOD,
    }
    if len(baseline_values) < 2 or len(post) < 2:
        result.update({
            "baseline_mg_dl": np.nan,
            "peak_mg_dl": np.nan,
            "delta_peak_mg_dl": np.nan,
            "time_to_peak_min": np.nan,
            "iauc_120": np.nan,
            "iauc_180": np.nan,
            "recovery_time_min": np.nan,
        })
        return result

    baseline = float(baseline_values.median())
    peak_idx = post["glucose_mg_dl"].idxmax()
    peak = float(post.loc[peak_idx, "glucose_mg_dl"])
    time_to_peak = float(post.loc[peak_idx, "minutes"])
    times = post["minutes"].to_numpy(dtype=float)
    values = post["glucose_mg_dl"].to_numpy(dtype=float)
    recovery = recovery_time(times, values, baseline)

    result.update({
        "baseline_mg_dl": round(baseline, 1),
        "peak_mg_dl": round(peak, 1),
        "delta_peak_mg_dl": round(peak - baseline, 1),
        "time_to_peak_min": round(time_to_peak, 1),
        "iauc_120": round(iauc(times, values, baseline, 120), 1),
        "iauc_180": round(iauc(times, values, baseline, 180), 1),
        "recovery_time_min": None if recovery is None else round(recovery, 1),
    })
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cgm", required=True, type=Path)
    parser.add_argument("--meals", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    cgm = pd.read_csv(args.cgm)
    meals = pd.read_csv(args.meals)
    required_cgm = {"timestamp", "glucose_mg_dl"}
    required_meals = {"meal_id", "meal_start_at"}
    if not required_cgm.issubset(cgm.columns):
        raise ValueError(f"CGM CSV missing: {sorted(required_cgm - set(cgm.columns))}")
    if not required_meals.issubset(meals.columns):
        raise ValueError(f"Meals CSV missing: {sorted(required_meals - set(meals.columns))}")

    cgm["timestamp"] = pd.to_datetime(cgm["timestamp"], utc=True)
    cgm["glucose_mg_dl"] = pd.to_numeric(cgm["glucose_mg_dl"], errors="coerce")
    cgm = cgm.sort_values("timestamp").drop_duplicates("timestamp")

    rows = [analyze_meal(cgm, meal) for _, meal in meals.iterrows()]
    pd.DataFrame(rows).to_csv(args.output, index=False)
    print(f"Wrote {len(rows)} analysis row(s) to {args.output}")


if __name__ == "__main__":
    main()

