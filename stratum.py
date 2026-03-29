#!/usr/bin/env python3
# stratum.py
# ─────────────────────────────────────────────────────────────────────────────
# STRATUM — Mobility Barrier Index
# Entry point: fetches data, computes MBI, launches dashboard
#
# Usage:
#   python stratum.py                    # Full run, launch dashboard
#   python stratum.py --no-dashboard     # Compute only, save results to CSV
#   python stratum.py --clear-cache      # Force re-fetch all data
#   python stratum.py --report           # Print text summary to terminal
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
import argparse
import pandas as pd
from colorama import init, Fore, Style

init(autoreset=True)

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.data.census import load_or_fetch as load_census
from src.data.opportunity import load_or_fetch as load_mobility
from src.analysis.mbi import compute_mbi, factor_regression, DIMENSIONS
from src.analysis.spatial import morans_i_from_fips, regional_summary


def print_banner():
    print(f"\n{Fore.BLUE}{'='*60}")
    print(f"{Fore.BLUE}  STRATUM — Mobility Barrier Index v1.0")
    print(f"{Fore.BLUE}  A. Xiu · github.com/axshoe/stratum")
    print(f"{Fore.BLUE}{'='*60}{Style.RESET_ALL}\n")


def print_report(df: pd.DataFrame, meta: dict, regression_df: pd.DataFrame):
    """Print a text summary of the MBI analysis."""
    print(f"\n{Fore.CYAN}NATIONAL SUMMARY{Style.RESET_ALL}")
    print(f"  Counties analyzed: {meta['n_counties']:,}")
    print(f"  Mean MBI:          {meta['mbi_mean']:.1f} / 100")
    print(f"  Std deviation:     {meta['mbi_std']:.1f}")
    print(f"  Range:             {meta['mbi_min']:.1f} - {meta['mbi_max']:.1f}")

    cats = df["mbi_category"].value_counts()
    print(f"\n{Fore.CYAN}BARRIER LEVEL DISTRIBUTION{Style.RESET_ALL}")
    for cat in ["Very High", "High", "Moderate", "Low", "Very Low"]:
        count = cats.get(cat, 0)
        pct = count / meta["n_counties"] * 100
        bar = "█" * int(pct / 2)
        print(f"  {cat:<12} {bar:<25} {count:>5} counties ({pct:.1f}%)")

    print(f"\n{Fore.CYAN}PCA FACTOR WEIGHTS{Style.RESET_ALL}")
    print(f"  PC1 explains {meta['explained_variance']*100:.1f}% of variance across barrier dimensions.")
    for col, label in DIMENSIONS.items():
        w = meta["weights"].get(col, 0)
        bar = "█" * int(w * 50)
        print(f"  {label:<30} {bar:<15} {w*100:.1f}%")

    print(f"\n{Fore.CYAN}10 HIGHEST BARRIER COUNTIES{Style.RESET_ALL}")
    for r in meta["top_barrier_counties"]:
        print(f"  {r['county_name']:<30} State {r['state']}  MBI: {r['mbi']:.1f}")

    print(f"\n{Fore.CYAN}10 LOWEST BARRIER COUNTIES{Style.RESET_ALL}")
    for r in meta["lowest_barrier_counties"]:
        print(f"  {r['county_name']:<30} State {r['state']}  MBI: {r['mbi']:.1f}")

    reg = regional_summary(df)
    print(f"\n{Fore.CYAN}REGIONAL SUMMARY{Style.RESET_ALL}")
    for _, row in reg.iterrows():
        print(f"  {row['region']:<12} Mean MBI: {row['mean_mbi']:.1f}  "
              f"High-barrier counties: {row['pct_high_barrier']:.1f}%")

    print(f"\n{Fore.CYAN}FACTOR REGRESSION (partial R²){Style.RESET_ALL}")
    for _, row in regression_df.iterrows():
        print(f"  {row['dimension']:<35} R²: {row['partial_r2']:.4f}")

    print()


def main():
    parser = argparse.ArgumentParser(description="Stratum — Mobility Barrier Index")
    parser.add_argument("--no-dashboard", action="store_true",
                        help="Compute MBI without launching the dashboard")
    parser.add_argument("--clear-cache", action="store_true",
                        help="Delete cached data and re-fetch from APIs")
    parser.add_argument("--report", action="store_true",
                        help="Print text summary report to terminal")
    parser.add_argument("--port", type=int, default=8050,
                        help="Port for dashboard (default: 8050)")
    args = parser.parse_args()

    print_banner()

    # Clear cache if requested
    if args.clear_cache:
        for f in ["data/census_cache.csv", "data/mobility_cache.csv"]:
            if os.path.exists(f):
                os.remove(f)
                print(f"  Cleared cache: {f}")

    # Step 1: Load data
    print(f"{Fore.YELLOW}[1/4] Loading data...{Style.RESET_ALL}")
    census_df = load_census()
    mobility_df = load_mobility()

    # Step 2: Merge
    print(f"\n{Fore.YELLOW}[2/4] Merging datasets...{Style.RESET_ALL}")
    df = census_df.merge(mobility_df, on="fips", how="left")
    print(f"  Merged: {len(df):,} counties with {df.columns.tolist().__len__()} variables")

    # Step 3: Compute MBI
    print(f"\n{Fore.YELLOW}[3/4] Computing Mobility Barrier Index...{Style.RESET_ALL}")
    df_mbi, meta = compute_mbi(df)
    regression_df = factor_regression(df_mbi)

    # Spatial analysis
    morans = morans_i_from_fips(df_mbi)
    print(f"  Moran's I: {morans['morans_i']} — {morans['interpretation']}")

    # Save results
    os.makedirs("data", exist_ok=True)
    df_mbi.to_csv("data/mbi_results.csv", index=False)
    print(f"  Results saved to data/mbi_results.csv")

    if args.report or args.no_dashboard:
        print_report(df_mbi, meta, regression_df)

    if args.no_dashboard:
        print(f"{Fore.GREEN}Done. Results in data/mbi_results.csv{Style.RESET_ALL}\n")
        return

    # Step 4: Launch dashboard
    print(f"\n{Fore.YELLOW}[4/4] Launching dashboard...{Style.RESET_ALL}")
    print(f"  Open your browser to: {Fore.CYAN}http://localhost:{args.port}{Style.RESET_ALL}")
    print(f"  Press Ctrl+C to stop.\n")

    from src.visualization.dashboard import create_app
    app = create_app(df_mbi, meta, regression_df)
    app.run_server(debug=False, port=args.port, host="0.0.0.0")


if __name__ == "__main__":
    main()
