#!/usr/bin/env python3
"""Deterministic CGM variability and range panel for Ai-to-Agent-CGM-v3.

Input cgm.csv: timestamp,glucose_mg_dl  (timezone-aware ISO 8601)

Outputs a JSON panel of consensus CGM metrics (mean glucose, GMI, CV%,
Time in / below / above Range, overnight stability) and, optionally, a CSV
of hypoglycaemia events. Metric definitions follow the 2019 International
Consensus on Time in Range. This is not a diagnostic tool.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

PANEL_VERSION = "1.0.0"

TIR_LOW_MG_DL = 70
TIR_HIGH_MG_DL = 180
TBR_LEVEL1_MG_DL = 70
TBR_LEVEL2_MG_DL = 54
TAR_LEVEL1_MG_DL = 180
TAR_LEVEL2_MG_DL = 250
CV_STABLE_THRESHOLD_PCT = 36.0
OVERNIGHT_START_HOUR = 0
OVERNIGHT_END_HOUR = 6


def gmi_percent(mean_glucose_mg_dl: float) -> float:
    """Glucose Management Indicator, estimated A1c in percent (Bergenstal 2018)."""
    return round(3.31 + 0.02392 * mean_glucose_mg_dl, 2)


def _pct(mask: np.ndarray) -> float:
    return round(100.0 * float(np.mean(mask)), 1) if mask.size else 0.0


def build_panel(cgm: pd.DataFrame, tz: str) -> dict[str, object]:
    df = cgm.dropna(subset=["glucose_mg_dl"]).sort_values("timestamp")
    g = df["glucose_mg_dl"].to_numpy(dtype=float)
    if g.size == 0:
        return {"panel_version": PANEL_VERSION, "n_readings": 0, "error": "NO_DATA"}

    mean_g = float(np.mean(g))
    sd = float(np.std(g, ddof=1)) if g.size > 1 else 0.0
    cv = round(100.0 * sd / mean_g, 1) if mean_g else None

    local_hour = df["timestamp"].dt.tz_convert(tz).dt.hour
    overnight = df.loc[
        (local_hour >= OVERNIGHT_START_HOUR) & (local_hour < OVERNIGHT_END_HOUR),
        "glucose_mg_dl",
    ].to_numpy(dtype=float)
    span_hours = round(
        (df["timestamp"].max() - df["timestamp"].min()).total_seconds() / 3600.0, 1
    )

    return {
        "panel_version": PANEL_VERSION,
        "n_readings": int(g.size),
        "span_hours": span_hours,
        "mean_glucose_mg_dl": round(mean_g, 1),
        "gmi_pct": gmi_percent(mean_g),
        "sd_mg_dl": round(sd, 1),
        "cv_pct": cv,
        "cv_stable": cv is not None and cv < CV_STABLE_THRESHOLD_PCT,
        "tir_70_180_pct": _pct((g >= TIR_LOW_MG_DL) & (g <= TIR_HIGH_MG_DL)),
        "tbr_lt70_pct": _pct(g < TBR_LEVEL1_MG_DL),
        "tbr_lt54_pct": _pct(g < TBR_LEVEL2_MG_DL),
        "tar_gt180_pct": _pct(g > TAR_LEVEL1_MG_DL),
        "tar_gt250_pct": _pct(g > TAR_LEVEL2_MG_DL),
        "overnight_mean_mg_dl": round(float(np.mean(overnight)), 1) if overnight.size else None,
        "overnight_cv_pct": (
            round(100.0 * np.std(overnight, ddof=1) / np.mean(overnight), 1)
            if overnight.size > 1 and np.mean(overnight)
            else None
        ),
    }


def hypo_events(cgm: pd.DataFrame) -> pd.DataFrame:
    """Rows below 70 mg/dL, tagged Level 1 (<70) or Level 2 (<54)."""
    df = cgm.dropna(subset=["glucose_mg_dl"]).sort_values("timestamp").copy()
    g = df["glucose_mg_dl"].astype(float)
    df["level"] = np.select(
        [g < TBR_LEVEL2_MG_DL, g < TBR_LEVEL1_MG_DL],
        ["level2_lt54", "level1_lt70"],
        default="",
    )
    return df.loc[df["level"] != "", ["timestamp", "glucose_mg_dl", "level"]].reset_index(drop=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cgm", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--events", type=Path, help="optional CSV of hypoglycaemia events")
    parser.add_argument("--tz", default="Asia/Taipei", help="IANA tz for the overnight window")
    args = parser.parse_args()

    cgm = pd.read_csv(args.cgm)
    if not {"timestamp", "glucose_mg_dl"}.issubset(cgm.columns):
        raise ValueError("CGM CSV must have columns: timestamp, glucose_mg_dl")
    cgm["timestamp"] = pd.to_datetime(cgm["timestamp"], utc=True)
    cgm["glucose_mg_dl"] = pd.to_numeric(cgm["glucose_mg_dl"], errors="coerce")
    cgm = cgm.sort_values("timestamp").drop_duplicates("timestamp")

    panel = build_panel(cgm, args.tz)
    args.output.write_text(json.dumps(panel, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote panel to {args.output}")

    if args.events:
        events = hypo_events(cgm)
        events.to_csv(args.events, index=False)
        print(f"Wrote {len(events)} hypo event(s) to {args.events}")


if __name__ == "__main__":
    main()
