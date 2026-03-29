# src/analysis/mbi.py
# ─────────────────────────────────────────────────────────────────────────────
# Mobility Barrier Index (MBI) — Core Computation Engine
#
# The MBI is a composite index (0-100) measuring structural barriers to
# socioeconomic mobility at the county level. Higher score = more barriers.
#
# Six input dimensions:
#   1. Income deprivation     — median household income (inverted)
#   2. Education access       — bachelor's degree attainment rate (inverted)
#   3. Housing cost burden    — % paying >50% income on housing
#   4. Broadband exclusion    — lack of broadband internet access (inverted rate)
#   5. Poverty exposure       — poverty rate
#   6. Mobility deficit       — low intergenerational upward mobility (inverted)
#
# Weighting method: Principal Component Analysis (PCA)
#   Rather than assigning weights arbitrarily, we use PCA to let the data
#   determine which factors co-vary and how much variance each explains.
#   PC1 loadings (after sign correction) become the dimension weights.
#   This is the same methodology used in the UNDP Human Development Index
#   research tradition and is more defensible than hand-picked weights.
#
# All dimensions are first normalized to [0,1] using min-max scaling,
# then oriented so that 1.0 = maximum barrier (makes PCA loadings interpretable).
# ─────────────────────────────────────────────────────────────────────────────

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sklearn.decomposition import PCA
from typing import Tuple, Dict


DIMENSIONS = {
    "income_barrier":   "Income deprivation",
    "edu_barrier":      "Education access gap",
    "housing_barrier":  "Housing cost burden",
    "broadband_barrier":"Broadband exclusion",
    "poverty_barrier":  "Poverty exposure",
    "mobility_deficit": "Mobility deficit",
}


def build_barrier_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Construct the six barrier dimensions from raw census/mobility variables.
    All dimensions are oriented so 1.0 = maximum barrier.
    """
    out = df.copy()

    # Income: invert (low income = high barrier)
    inc = pd.to_numeric(out["median_income"], errors="coerce")
    out["income_barrier"] = 1 - MinMaxScaler().fit_transform(
        inc.values.reshape(-1, 1)
    ).flatten()

    # Education: invert (low attainment = high barrier)
    out["edu_barrier"] = 1 - out["edu_rate"].fillna(out["edu_rate"].median())

    # Housing: already oriented (high burden = high barrier)
    out["housing_barrier"] = out["housing_burden_rate"].fillna(
        out["housing_burden_rate"].median()
    )

    # Broadband: invert (low access = high barrier)
    out["broadband_barrier"] = 1 - out["broadband_rate"].fillna(
        out["broadband_rate"].median()
    )

    # Poverty: already oriented
    out["poverty_barrier"] = out["poverty_rate"].fillna(out["poverty_rate"].median())

    # Mobility: invert (low mobility = high barrier)
    if "upward_mobility" in out.columns and out["upward_mobility"].notna().sum() > 0:
        out["mobility_deficit"] = 1 - out["upward_mobility"].fillna(
            out["upward_mobility"].median()
        )
    else:
        # Proxy with poverty + income average when OI data unavailable
        out["mobility_deficit"] = (out["poverty_barrier"] + out["income_barrier"]) / 2
    return out


def compute_pca_weights(feature_matrix: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Run PCA on the six barrier dimensions.
    Returns PC1 loadings (as weights) and explained variance ratio.

    The loadings represent how much each dimension contributes to the
    dominant pattern of co-variation across counties. Dimensions with
    higher loadings drive the MBI more strongly.
    """
    pca = PCA(n_components=6)
    pca.fit(feature_matrix)

    # PC1 loadings
    loadings = pca.components_[0]

    # Ensure loadings are positive (flip sign if majority are negative)
    if np.sum(loadings) < 0:
        loadings = -loadings

    # Normalize to sum to 1.0 (weights)
    weights = np.abs(loadings) / np.abs(loadings).sum()

    explained_var = pca.explained_variance_ratio_[0]
    return weights, explained_var


def compute_mbi(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
    """
    Main entry point. Computes MBI for all counties.

    Returns:
        df_out: DataFrame with MBI score and all intermediate columns
        meta:   Dict with PCA weights, explained variance, and stats
    """
    print("  Building barrier feature dimensions...")
    df_feat = build_barrier_features(df)

    dim_cols = list(DIMENSIONS.keys())

    # Drop rows where any dimension is missing
    valid = df_feat[dim_cols].notna().all(axis=1)
    df_valid = df_feat[valid].copy()
    print(f"  Computing MBI for {len(df_valid)} counties (dropped {(~valid).sum()} with missing data)...")

    # Min-max scale each dimension to [0,1]
    scaler = MinMaxScaler()
    X = scaler.fit_transform(df_valid[dim_cols].values)

    # PCA weights
    weights, explained_var = compute_pca_weights(X)
    print(f"  PCA: PC1 explains {explained_var*100:.1f}% of variance across dimensions.")

    # Weighted composite score
    raw_mbi = X @ weights  # dot product: each county gets a weighted sum

    # Scale to 0-100
    mn, mx = raw_mbi.min(), raw_mbi.max()
    mbi_scaled = (raw_mbi - mn) / (mx - mn) * 100

    df_valid["mbi"] = mbi_scaled

    # Factor contributions (each dimension's weighted contribution to MBI)
    for i, col in enumerate(dim_cols):
        df_valid[f"contrib_{col}"] = X[:, i] * weights[i]

    # MBI category
    df_valid["mbi_category"] = pd.cut(
        df_valid["mbi"],
        bins=[0, 20, 40, 60, 80, 100],
        labels=["Very Low", "Low", "Moderate", "High", "Very High"],
        include_lowest=True,
    )

    meta = {
        "weights": dict(zip(dim_cols, weights.tolist())),
        "explained_variance": float(explained_var),
        "n_counties": len(df_valid),
        "mbi_mean": float(mbi_scaled.mean()),
        "mbi_std":  float(mbi_scaled.std()),
        "mbi_min":  float(mbi_scaled.min()),
        "mbi_max":  float(mbi_scaled.max()),
        "top_barrier_counties": df_valid.nlargest(10, "mbi")[["fips","county_name","state","mbi"]].to_dict("records"),
        "lowest_barrier_counties": df_valid.nsmallest(10, "mbi")[["fips","county_name","state","mbi"]].to_dict("records"),
    }

    print(f"  MBI computed. Mean: {meta['mbi_mean']:.1f}, Std: {meta['mbi_std']:.1f}")
    return df_valid, meta


def factor_regression(df: pd.DataFrame) -> pd.DataFrame:
    """
    Run OLS regression of MBI on each individual factor to get
    partial R-squared — how much unique variance each factor explains.
    Returns a summary DataFrame sorted by explanatory power.
    """
    from sklearn.linear_model import LinearRegression

    dim_cols = list(DIMENSIONS.keys())
    results = []

    for col in dim_cols:
        if col not in df.columns:
            continue
        X = df[[col]].dropna()
        y = df.loc[X.index, "mbi"]
        model = LinearRegression().fit(X, y)
        r2 = model.score(X, y)
        results.append({
            "dimension": DIMENSIONS[col],
            "column": col,
            "partial_r2": round(r2, 4),
            "coefficient": round(float(model.coef_[0]), 4),
        })

    return pd.DataFrame(results).sort_values("partial_r2", ascending=False)
