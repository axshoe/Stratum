# STRATUM — Mobility Barrier Index

> *"Most economic mobility data tells you how bad the problem is. Stratum tells you why, and where."*

An open-source Python tool that computes a county-level **Mobility Barrier Index (MBI)** across all 3,000+ U.S. counties by fusing six structural socioeconomic dimensions, using PCA to derive data-driven weights rather than arbitrary assumptions, and rendering an interactive geospatial dashboard that lets anyone drill down into the specific factors driving barriers in any county.

```bash
python stratum.py              # fetch data, compute MBI, launch dashboard
python stratum.py --report     # terminal summary only
python stratum.py --no-dashboard  # save results to CSV without launching
```

---

## What It Does

Mobility researchers and policy organizations publish data. They rarely publish tools that make the data actionable for a county commissioner, a nonprofit director, or a researcher who wants to understand the factor structure of barriers across regions.

Stratum fills that gap. It pulls from four free public data sources, constructs six structural barrier dimensions, uses Principal Component Analysis to weight them by their co-variation patterns across counties (not by hand), and computes a composite score from 0 to 100. It then renders an interactive choropleth map where you can click any county and see exactly which factors are driving its barrier score.

The decomposition is the point. A county with a high MBI driven primarily by broadband exclusion needs a different intervention than one driven by housing cost burden. Average national scores hide this. Stratum surfaces it.

---

## Data Sources (All Free, All Public)

| Source | What We Pull | Key? |
|--------|-------------|------|
| U.S. Census Bureau ACS 5-Year | Income, education, housing burden, broadband, poverty | Yes (free, instant) |
| Opportunity Insights (Harvard) | Intergenerational upward mobility by county | No |
| BLS LAUS | County unemployment rates | No |

---

## The Six Barrier Dimensions

| Dimension | Variable | Orientation |
|-----------|----------|-------------|
| Income deprivation | Median household income | Inverted (low = high barrier) |
| Education access gap | Bachelor's attainment rate (25+) | Inverted |
| Housing cost burden | % paying >50% income on housing | Direct |
| Broadband exclusion | Household broadband access rate | Inverted |
| Poverty exposure | Poverty rate | Direct |
| Mobility deficit | Upward mobility percentile rank (Chetty et al.) | Inverted |

---

## Methodology

### PCA Weighting

Rather than assigning weights arbitrarily (which requires defending subjective choices), Stratum uses the first principal component of the six-dimensional feature matrix to derive weights from the data.

The logic: PC1 captures the dominant pattern of co-variation across counties. Counties that score high on one barrier dimension tend to score high on others — the weights represent how much each dimension contributes to this dominant pattern. This is more defensible than "I decided income should be 25% of the score."

PC1 typically explains 55-65% of cross-county variance in the barrier dimensions.

### Normalization

All six dimensions are min-max normalized to [0,1] before PCA, oriented so 1.0 = maximum barrier. This ensures no single dimension dominates due to scale differences (income is in thousands of dollars; rates are in [0,1]).

### MBI Scoring

```
MBI_i = 100 × (w · x_i - min(w · X)) / (max(w · X) - min(w · X))
```

where `w` is the PC1 weight vector, `x_i` is the feature vector for county i, and `X` is the full feature matrix.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/axshoe/stratum
cd stratum

# 2. Install dependencies
pip install -r requirements.txt

# 3. Get your free Census API key
# https://api.census.gov/data/key_signup.html (instant)
cp env.example .env
# paste your key into .env

# 4. Run
python stratum.py
# Open http://localhost:8050
```

---

## Architecture

```
stratum/
  src/
    data/
      census.py         ACS 5-year estimates fetcher + cache
      opportunity.py    Opportunity Insights mobility loader
    analysis/
      mbi.py            PCA weighting + MBI computation + regression
      spatial.py        Moran's I autocorrelation + regional summary
    visualization/
      dashboard.py      Plotly Dash interactive dashboard
  stratum.py            Entry point CLI
  requirements.txt
  env.example
  docs/
    README.md           Full lab writeup
    concepts.md         Technical reference document
```

---

## What I Learned Building This

Full writeup at [docs/README.md](docs/README.md).

---

**Not financial or policy advice. Built for research and education.**

MIT License · Built by A. Xiu · 2026
