# STRATUM — Mobility Barrier Index

> *"The gap was never data. It was a tool that combined the data usefully and made it accessible to non-experts."*

An open-source Python tool that computes a county-level **Mobility Barrier Index (MBI)** across all 3,000+ U.S. counties by fusing six structural socioeconomic dimensions, using PCA to derive data-driven weights rather than arbitrary assumptions, and rendering an interactive geospatial dashboard that lets anyone drill down into the specific factors driving barriers in any county.

```bash
python stratum.py              # fetch data, compute MBI, launch dashboard
python stratum.py --report     # terminal summary only
python stratum.py --no-dashboard  # save results to CSV without launching
```

**Full project writeup and lab documentation:** [thexiulab.org](https://thexiulab.org)

---

## What It Does

Mobility researchers and policy organizations publish data. They rarely publish tools that make the data actionable for a county commissioner, a nonprofit director, or a researcher who wants to understand the factor structure of barriers across regions.

STRATUM fills that gap. It pulls from four free public data sources, constructs six structural barrier dimensions, uses Principal Component Analysis to weight them by their co-variation patterns across counties rather than by arbitrary assignment, and computes a composite score from 0 to 100. It then renders an interactive choropleth map where you can click any county and see exactly which factors are driving its barrier score.

The decomposition is the point. A county with a high MBI driven primarily by broadband exclusion needs a different intervention than one driven by housing cost burden. Average national scores hide this. STRATUM surfaces it.

---

## Data Sources (All Free, All Public)

| Source | What We Pull | Key Required? |
|--------|-------------|------|
| U.S. Census Bureau ACS 5-Year | Income, education, housing burden, broadband, poverty | Yes (free, instant at api.census.gov) |
| Opportunity Insights (Harvard) | Intergenerational upward mobility by county | No |

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

Rather than assigning weights arbitrarily, STRATUM uses the first principal component of the six-dimensional feature matrix to derive weights from the data. PC1 captures the dominant pattern of co-variation across counties. Its loadings become the dimension weights. This is more defensible than hand-picked weights because it is consistent with the data's own structure.

PC1 explains approximately 58% of cross-county variance, validating that the six dimensions share real underlying structure.

### MBI Scoring

```
MBI_i = 100 × (w · x_i - min(w · X)) / (max(w · X) - min(w · X))
```

where `w` is the PC1 weight vector, `x_i` is the normalized feature vector for county i.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/axshoe/stratum
cd stratum

# 2. Install dependencies
pip install -r requirements.txt

# 3. Get your free Census API key (takes 2 minutes)
# https://api.census.gov/data/key_signup.html
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
  wsgi.py               Gunicorn entry point (for Render deployment)
  requirements.txt
  render.yaml
  env.example
  docs/
    README.md           Full lab writeup (thexiulab.org)
```

---

## Deploying to Render

```bash
# Just push to GitHub — render.yaml handles the rest.
# Add your CENSUS_API_KEY as an environment variable in Render dashboard.
```

---

## Full Writeup

The complete project documentation, all six phases, methodology decisions, and reflection is available at **[thexiulab.org](https://thexiulab.org)**.

---

**MIT License · Built by A. Xiu · 2026 · [thexiulab.org](https://thexiulab.org)**
