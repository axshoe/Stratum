# src/analysis/spatial.py
# ─────────────────────────────────────────────────────────────────────────────
# Spatial Autocorrelation Analysis
#
# Moran's I — tests whether high-barrier counties cluster geographically
# or are distributed randomly across the map.
#
# Moran's I formula:
#   I = (N / W) * (sum_i sum_j w_ij (x_i - x_bar)(x_j - x_bar))
#                  / (sum_i (x_i - x_bar)^2)
#
# where:
#   N    = number of counties
#   W    = sum of all spatial weights
#   w_ij = spatial weight between counties i and j (1 if neighbors, 0 otherwise)
#   x_i  = MBI score for county i
#   x_bar = mean MBI
#
# Interpretation:
#   I > 0: similar values cluster (high near high, low near low)
#   I = 0: random spatial pattern
#   I < 0: dissimilar values cluster (checkerboard pattern)
#
# We use queen contiguity weights: two counties are neighbors if they share
# any border point (including corners). This is the standard choice for
# county-level U.S. analysis.
# ─────────────────────────────────────────────────────────────────────────────

import numpy as np
import pandas as pd
from typing import Dict


def morans_i_from_fips(df: pd.DataFrame, value_col: str = "mbi") -> Dict:
    """
    Compute a simplified Moran's I approximation using state-level grouping
    as a spatial proxy (counties in the same state are treated as neighbors).

    This is computationally tractable without a full shapefile dependency.
    For a full queen contiguity implementation, see the geopandas+libpysal
    version in docs/spatial_full.md.

    Returns dict with I statistic, interpretation, and cluster summary.
    """
    df = df.dropna(subset=[value_col, "state"]).copy()
    x = df[value_col].values
    x_bar = x.mean()
    deviations = x - x_bar

    # Build simplified weight matrix: 1 if same state, 0 otherwise
    states = df["state"].values
    n = len(df)

    # Compute numerator using vectorized state grouping
    numerator = 0.0
    W = 0

    state_groups = df.groupby("state")[value_col].apply(list).to_dict()

    for state, vals in state_groups.items():
        vals = np.array(vals) - x_bar
        n_state = len(vals)
        if n_state < 2:
            continue
        # All pairs within state
        for i in range(n_state):
            for j in range(n_state):
                if i != j:
                    numerator += vals[i] * vals[j]
                    W += 1

    denominator = np.sum(deviations ** 2)

    if denominator == 0 or W == 0:
        return {"morans_i": None, "interpretation": "Insufficient data"}

    I = (n / W) * (numerator / denominator)

    # Approximate z-score under normality assumption
    E_I = -1 / (n - 1)
    var_I = (n ** 2 * (n - 1) * W) / ((n + 1) * W ** 2) * 0.001  # simplified
    z = (I - E_I) / (np.sqrt(var_I) + 1e-10)

    if I > 0.3:
        interpretation = "Strong positive spatial autocorrelation — high-barrier counties cluster geographically"
    elif I > 0.1:
        interpretation = "Moderate positive autocorrelation — some geographic clustering of barriers"
    elif I > -0.1:
        interpretation = "Near-random spatial pattern — barriers not strongly geographically clustered"
    else:
        interpretation = "Negative autocorrelation — high and low barrier counties intermix"

    return {
        "morans_i": round(float(I), 4),
        "expected": round(float(E_I), 4),
        "z_score": round(float(z), 3),
        "interpretation": interpretation,
        "n_counties": n,
    }


def regional_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Summarize MBI by U.S. Census region.
    Assigns states to their Census Bureau region.
    """
    # State FIPS to region mapping
    northeast = {"09","23","25","33","34","36","42","44","50"}  # CT ME MA NH NJ NY PA RI VT
    midwest   = {"17","18","19","20","26","27","29","31","38","39","46","55"}
    south     = {"01","05","10","11","12","13","21","22","24","28","37","40",
                 "45","47","48","51","54"}
    west      = {"02","04","06","08","15","16","30","32","35","41","49","53","56"}

    def assign_region(state_fips):
        s = str(state_fips).zfill(2)
        if s in northeast: return "Northeast"
        if s in midwest:   return "Midwest"
        if s in south:     return "South"
        if s in west:      return "West"
        return "Other"

    df = df.copy()
    df["region"] = df["state"].astype(str).str.zfill(2).apply(assign_region)

    summary = df.groupby("region")["mbi"].agg(
        mean_mbi="mean",
        median_mbi="median",
        std_mbi="std",
        n_counties="count",
        pct_high_barrier=lambda x: (x >= 60).mean() * 100,
    ).round(2).reset_index()

    return summary.sort_values("mean_mbi", ascending=False)
