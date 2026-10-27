#!/usr/bin/env python3
"""
Shell Eco-marathon World Ranking Engine (Simplified Model)
Calculates:
  S_ontrack = 100 * (E_teambest / E_eventmax)
  C_k       = E_eventmax / E_worldmax
  W_points  = S_ontrack * C_k
Applies a 3-season sliding window (1.00, 0.65, 0.35) per vehicle class & propulsion type.
"""

import argparse
from pathlib import Path
import sys
import numpy as np
import pandas as pd

SEASON_WEIGHTS = {0: 1.00, 1: 0.65, 2: 0.35}  # s0 (current), s1 (year-1), s2 (year-2)


# -----------------------------------------------------------------------------
# 1. LOAD & CLEAN DATA
# -----------------------------------------------------------------------------
def load_data(data_dir: Path) -> pd.DataFrame:
    csv_files = list(data_dir.rglob("*.csv"))
    if not csv_files:
        sys.exit(f"[!] Error: No CSV files found in {data_dir.resolve()}")

    frames = []
    print(f"[+] Loading {len(csv_files)} event file(s) from {data_dir}:")
    for f in csv_files:
        df = pd.read_csv(f)
        df.columns = df.columns.str.strip().str.lower()
        print(f"  • {f.relative_to(data_dir)} ({len(df)} rows)")
        frames.append(df)

    df = pd.concat(frames, ignore_index=True)

    # Standardize types
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")

    # Clean numeric efficiency (handles strings like '1,101.7' -> 1101.7)
    df["best_efficiency"] = (
        df["best_efficiency"]
        .astype(str)
        .str.replace(",", "", regex=False)
        .pipe(pd.to_numeric, errors="coerce")
        .fillna(0.0)
    )

    str_cols = ["event_id", "vehicle_class", "propulsion_type", "team_id", 
                "country", "vehicle_number", "institution", "team_name"]
    for col in str_cols:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df["vehicle_class"] = df["vehicle_class"].str.title()
    df["propulsion_type"] = df["propulsion_type"].str.title()

    return df


# -----------------------------------------------------------------------------
# 2. CALCULATE EVENT SCORES (S_ontrack, C_k, W_points)
# -----------------------------------------------------------------------------
def calculate_event_points(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    # E_worldmax: Maximum efficiency globally per year, class, and propulsion
    df["e_worldmax"] = df.groupby(
        ["year", "vehicle_class", "propulsion_type"]
    )["best_efficiency"].transform("max")

    # E_eventmax: Maximum efficiency at that event per class and propulsion
    df["e_eventmax"] = df.groupby(
        ["event_id", "vehicle_class", "propulsion_type"]
    )["best_efficiency"].transform("max")

    # S_ontrack = 100 * (E_teambest / E_eventmax)
    df["s_ontrack"] = np.where(
        df["e_eventmax"] > 0,
        100.0 * (df["best_efficiency"] / df["e_eventmax"]),
        0.0
    )

    # C_k = E_eventmax / E_worldmax
    df["c_k"] = np.where(
        df["e_worldmax"] > 0,
        df["e_eventmax"] / df["e_worldmax"],
        0.0
    )

    # W_points = S_ontrack * C_k
    df["w_points"] = df["s_ontrack"] * df["c_k"]

    return df


# -----------------------------------------------------------------------------
# 3. AGGREGATE 3-SEASON WORLD RANKINGS
# -----------------------------------------------------------------------------
def build_world_rankings(df: pd.DataFrame, current_year: int) -> pd.DataFrame:
    valid_years = {current_year - i: w for i, w in SEASON_WEIGHTS.items()}
    window_df = df[df["year"].isin(valid_years.keys())].copy()
    window_df["season_weight"] = window_df["year"].map(valid_years)

    # Optimal event rule: Take the best W_points per season per team
    season_bests = (
        window_df.groupby(["vehicle_class", "propulsion_type", "team_id", "year"], as_index=False)
        .agg(
            best_event_pts=("w_points", "max"),
            weight=("season_weight", "first"),
            team_name=("team_name", "last"),
            institution=("institution", "last"),
            country=("country", "last"),
            vehicle_number=("vehicle_number", "last")
        )
    )
    season_bests["season_pts"] = season_bests["best_event_pts"] * season_bests["weight"]

    # Sum across the 3-season sliding window
    ranked_categories = []
    for (v_class, p_type), grp in season_bests.groupby(["vehicle_class", "propulsion_type"]):
        teams_data = []

        for team_id, team_rows in grp.groupby("team_id"):
            meta = team_rows.iloc[-1]
            pts_by_year = team_rows.set_index("year")["season_pts"].to_dict()

            p0 = pts_by_year.get(current_year, 0.0)
            p1 = pts_by_year.get(current_year - 1, 0.0)
            p2 = pts_by_year.get(current_year - 2, 0.0)
            wrl_total = p0 + p1 + p2

            best_single = team_rows["best_event_pts"].max()
            events_count = len(window_df[
                (window_df["team_id"] == team_id) &
                (window_df["vehicle_class"] == v_class) &
                (window_df["propulsion_type"] == p_type)
            ])

            teams_data.append({
                "vehicle_class": v_class,
                "propulsion_type": p_type,
                "team_id": team_id,
                "team_name": meta["team_name"],
                "institution": meta["institution"],
                "country": meta["country"],
                "vehicle_number": meta["vehicle_number"],
                "wrl_points": round(wrl_total, 2),
                f"points_{current_year}": round(p0, 2),
                f"points_{current_year - 1}": round(p1, 2),
                f"points_{current_year - 2}": round(p2, 2),
                "best_single_score": round(best_single, 2),
                "events_attended": events_count
            })

        cat_df = pd.DataFrame(teams_data)
        if cat_df.empty:
            continue

        # Sort: 1) Total WRL Points -> 2) Peak Event Score -> 3) Current Season Points
        cat_df = cat_df.sort_values(
            by=["wrl_points", "best_single_score", f"points_{current_year}"],
            ascending=[False, False, False]
        ).reset_index(drop=True)

        cat_df.insert(0, "rank", np.arange(1, len(cat_df) + 1))
        ranked_categories.append(cat_df)

    if not ranked_categories:
        return pd.DataFrame()

    return pd.concat(ranked_categories, ignore_index=True)


# -----------------------------------------------------------------------------
# 4. CLI ENTRYPOINT
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate Shell Eco-marathon World Rankings.")
    parser.add_argument("--data-dir", type=str, default="data", help="Folder containing CSV files")
    parser.add_argument("--output", type=str, default="world_rankings.csv", help="Output path for rankings CSV")
    parser.add_argument("--year", type=int, default=None, help="Reference season year (defaults to max in data)")

    args = parser.parse_args()
    data_path = Path(args.data_dir)

    raw_df = load_data(data_path)
    ref_year = args.year if args.year else int(raw_df["year"].max())
    print(f"\n[+] Computing World Rankings for Window: {ref_year - 2} – {ref_year}")

    scored_df = calculate_event_points(raw_df)
    rankings_df = build_world_rankings(scored_df, current_year=ref_year)

    if rankings_df.empty:
        sys.exit("[!] No rankings could be generated. Check input data.")

    out_file = Path(args.output)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    rankings_df.to_csv(out_file, index=False, encoding="utf-8")
    print(f"[✓] World Rankings exported to: {out_file.resolve()}\n")

    # Console Summary Table
    print(f"{'Category':<40} | {'Teams':<5} | {'World Leader':<30} | {'Points'}")
    print("-" * 90)
    for (v_class, p_type), group in rankings_df.groupby(["vehicle_class", "propulsion_type"]):
        leader = group.iloc[0]
        cat_name = f"{v_class} | {p_type}"
        name = leader["team_name"] if leader["team_name"] else leader["institution"]
        print(f"{cat_name:<40} | {len(group):<5} | {name:<30} | {leader['wrl_points']}")


if __name__ == "__main__":
    main()