#!/usr/bin/env python3
"""
Shell Eco-marathon World Ranking Engine
Updated C_k model:
  S_ontrack = 100 * (E_teambest / E_eventmax)
  turn_density =
  M_track = 1.0 + 0.08 * (turn_density - 4.0) / 4.0 + 0.06 * (elev_rate - 2.0) / 2.0 + 0.06 (v_avg - 25.0) / 25.0
  C_k       = (E_event_top3 / E_world_top3) * M_track
  W_points  = S_ontrack * C_k
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

    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype(int)
    df["rank"] = pd.to_numeric(df["rank"], errors="coerce")

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
# 2. TRACK DIFFICULTY MODIFIER (M_track from events.csv)
# -----------------------------------------------------------------------------
def load_track_modifiers(events_path: Path) -> dict:
    """
    Computes M_track for each event based on turn density, elevation, and speed.
    Baseline neutral circuit: 4.0 turns/km, 2.0 m/km elevation, 25 km/h.
    """
    if not events_path.exists():
        print(f"[!] Note: {events_path} not found. Defaulting M_track = 1.0 for all tracks.")
        return {}

    events_df = pd.read_csv(events_path)
    events_df.columns = events_df.columns.str.strip().str.lower()
    modifiers = {}

    print(f"[+] Loaded {len(events_df)} track record(s) from {events_path}:")
    for _, row in events_df.iterrows():
        ev_id = str(row["event_id"]).strip()
        laps = float(row.get("laps", 10))
        turns = float(row.get("turns", 8))
        elev = float(row.get("elevation_change", 0.0))
        dist = float(row.get("total_dist", 8.0))
        time_mins = float(row.get("time", 25.0))

        if dist <= 0 or time_mins <= 0:
            modifiers[ev_id] = 1.0
            continue

        # Physical track metrics
        turn_density = (turns * laps) / dist          # turns per km
        elev_rate = (elev * laps) / dist               # meters climb per km
        req_speed = dist / (time_mins / 60.0)          # target km/h

        # Physics-based difficulty index (centered at 1.0)
        # Turning losses (8%), Elevation resistance (6%), Speed drag (6%)
        m_track = (
            1.0
            + 0.08 * ((turn_density - 4.0) / 4.0)
            + 0.06 * ((elev_rate - 2.0) / 2.0)
            + 0.06 * ((req_speed - 25.0) / 25.0)
        )

        # Clamp between 0.80 and 1.25 to prevent extreme distortion
        m_track = round(float(np.clip(m_track, 0.80, 1.25)), 3)
        modifiers[ev_id] = m_track
        print(f"  • {ev_id:15} ({row.get('track', 'Unknown'):20}) -> M_track = {m_track:.3f} (Turns: {turn_density:.1f}/km, Speed: {req_speed:.1f} km/h)")

    return modifiers


# -----------------------------------------------------------------------------
# 3. CALCULATE EVENT SCORES WITH TOP-3 C_k & TRACK MODIFIERS
# -----------------------------------------------------------------------------
def calculate_event_points(df: pd.DataFrame, modifiers: dict) -> pd.DataFrame:
    df = df.copy()

    # 1. Event Max Efficiency (E_eventmax)
    df["e_eventmax"] = df.groupby(
        ["event_id", "vehicle_class", "propulsion_type"]
    )["best_efficiency"].transform("max")

    # 2. On-track score: S_ontrack = 100 * (E_teambest / E_eventmax)
    df["s_ontrack"] = np.where(
        df["e_eventmax"] > 0,
        100.0 * (df["best_efficiency"] / df["e_eventmax"]),
        0.0
    )

    # 3. Compute Top-3 Average per Event (E_event_top3)
    event_top3 = {}
    for (ev_id, v_class, p_type), grp in df.groupby(["event_id", "vehicle_class", "propulsion_type"]):
        valid = grp[grp["best_efficiency"] > 0]["best_efficiency"].sort_values(ascending=False)
        top3_sum = valid.head(3).sum()
        # Always divide by 3 so uncontested 1- or 2-car classes are not artificially inflated
        event_top3[(ev_id, v_class, p_type)] = float(top3_sum / 3.0) if not valid.empty else 0.0

    # 4. Compute Top-3 Average Globally per Year (E_world_top3)
    # Uses top 3 unique teams globally that season
    world_top3 = {}
    for (yr, v_class, p_type), grp in df.groupby(["year", "vehicle_class", "propulsion_type"]):
        team_bests = grp[grp["best_efficiency"] > 0].groupby("team_id")["best_efficiency"].max().sort_values(ascending=False)
        top3_vals = team_bests.head(3)
        world_top3[(yr, v_class, p_type)] = float(top3_vals.mean()) if not top3_vals.empty else 0.0

    # 5. Compute C_k = (E_event_top3 / E_world_top3) * M_track
    c_k_values = []
    m_track_values = []

    for row in df.itertuples():
        ev_top3 = event_top3.get((row.event_id, row.vehicle_class, row.propulsion_type), 0.0)
        wld_top3 = world_top3.get((row.year, row.vehicle_class, row.propulsion_type), 0.0)
        m_trk = modifiers.get(row.event_id, 1.0)

        if wld_top3 > 0 and ev_top3 > 0:
            c_k = (ev_top3 / wld_top3) * m_trk
        else:
            c_k = 0.0

        c_k_values.append(round(c_k, 4))
        m_track_values.append(m_trk)

    df["m_track"] = m_track_values
    df["c_k"] = c_k_values
    df["w_points"] = df["s_ontrack"] * df["c_k"]

    return df


# -----------------------------------------------------------------------------
# 4. AGGREGATE 3-SEASON WORLD RANKINGS
# -----------------------------------------------------------------------------
def build_world_rankings(df: pd.DataFrame, current_year: int) -> pd.DataFrame:
    valid_years = {current_year - i: w for i, w in SEASON_WEIGHTS.items()}
    window_df = df[df["year"].isin(valid_years.keys())].copy()
    window_df["season_weight"] = window_df["year"].map(valid_years)

    # Take highest W_points per season per team
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

    # Sum across 3 seasons
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
# 5. CLI ENTRYPOINT
# -----------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Generate Shell Eco-marathon World Rankings.")
    parser.add_argument("--data-dir", type=str, default="data/results", help="Folder containing CSV files")
    parser.add_argument("--events", type=str, default="data/events.csv", help="Path to events.csv track characteristics file")
    parser.add_argument("--output", type=str, default="world_rankings.csv", help="Output path for rankings CSV")
    parser.add_argument("--year", type=int, default=None, help="Reference season year (defaults to max in data)")

    args = parser.parse_args()
    data_path = Path(args.data_dir)
    events_path = Path(args.events)

    raw_df = load_data(data_path)
    track_mods = load_track_modifiers(events_path)

    ref_year = args.year if args.year else int(raw_df["year"].max())
    print(f"\n[+] Computing World Rankings for Window: {ref_year - 2} – {ref_year}")

    scored_df = calculate_event_points(raw_df, track_mods)
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