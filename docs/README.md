# STRATUM
## A Quantitative Framework for Mapping Socioeconomic Mobility Barriers Using Public Census and Labor Data with Geospatial Visualization

**January 2026 – March 2026**

---

### Introduction

I did not set out to build a tool about economic mobility. I set out to understand why the same intellectual problem keeps appearing in different domains.

In DermEquity, the problem was this: a model that looked fair on average was hiding diagnostic disparities that only became visible when you looked at specific subgroups, specific operating thresholds, specific failure modes. The average number was technically accurate and completely misleading.

At some point during that work, I started reading Raj Chetty's research on intergenerational income mobility. The Opportunity Atlas (Chetty et al., 2018) is one of the most striking datasets I have encountered: it maps, at the county and even census tract level, the probability that a child born in the 25th percentile of the income distribution will reach the median or above by age 35. The variation is enormous. A child born in one county has roughly the same economic prospects as a child born in Denmark. A child born in the adjacent county might have prospects closer to Honduras.

But the data, extraordinary as it is, has a problem. You can see that a county has low mobility. You cannot easily see why. Is it the lack of broadband that cuts people off from remote work and online education? Is it housing cost burden that traps families in poverty through rent? Is it low educational attainment, or high unemployment, or income so depressed that savings are impossible? Policy organizations have data on all of these things. Nobody has built an open-source, transparent, publicly accessible tool that fuses them into a decomposable score and shows you, at the county level, which specific factors are driving the barrier.

That is what Stratum is.

Cheers,
Angie X.

---

### PHASE 1: The Problem and What Already Exists

The academic literature on socioeconomic mobility is deep and rich. Chetty, Friedman, and Hendren at Harvard's Opportunity Insights lab have produced some of the most rigorous empirical economics of the last decade, establishing that where you grow up matters enormously for where you end up, and that this is driven by specific, measurable features of communities rather than individual characteristics alone.

The policy tool landscape is a different story. The tools that exist fall into two categories.

The first category is proprietary and expensive. Bloomberg provides economic indicator dashboards at institutional subscription rates. ESRI's ArcGIS platform has powerful geospatial analysis tools but requires licensing and technical expertise that most county-level policymakers and nonprofit directors do not have.

The second category is open but static. The Opportunity Insights website publishes beautiful visualizations of their mobility data. The Census Bureau's data explorer lets you look up any ACS variable by geography. The Bureau of Labor Statistics publishes monthly unemployment by county. But these are siloed. You cannot fuse them into a composite index and decompose that index to see which factors are driving a specific county's outcome. You see the what, not the why.

The gap Stratum fills: a free, open-source, fully transparent composite index that fuses six structural dimensions, weights them using a defensible methodology (PCA rather than arbitrary assignment), and presents a geospatial dashboard where any user can drill down to a specific county and see its factor breakdown.

**Project objective:** Build an open-source Python tool that computes a county-level Mobility Barrier Index (MBI) across all U.S. counties, uses PCA to derive data-driven weights, renders an interactive geospatial dashboard, and is documented rigorously enough that a county commissioner or researcher could actually use it.

---

### PHASE 2: Learning the Concepts

I spent approximately three weeks doing nothing but reading before writing a single line of code.

**On intergenerational mobility and its measurement.** Chetty et al.'s framework defines upward mobility as the expected income rank at age 35 for a child born in the 25th percentile of the national income distribution. This is a longitudinal measure: it requires tracking people from childhood to adulthood, which is why it uses IRS tax records rather than survey data. The finding that this varies enormously by county, and that it has not increased since the 1980s despite overall economic growth, is one of the most important empirical results in modern social science.

What drives it? The Opportunity Atlas identifies five key factors at the commuting zone level: residential segregation, income inequality, local school quality, social capital, and family stability. These are correlational findings from observational data, not causal claims. Stratum takes a complementary approach: instead of identifying what predicts mobility empirically, it asks what structural barriers exist that prevent mobility from occurring.

**On Principal Component Analysis.** The core methodological question in building any composite index is how to weight the components. There are three honest answers: arbitrary weights (which require justification), regression-derived weights (which require labeled outcome data), or data-driven weights from the structure of the data itself. PCA is the third approach.

PCA finds the linear combinations of variables that explain the most variance in the dataset. The first principal component is the direction of maximum variance. In a dataset of six barrier dimensions, PC1 captures the dominant pattern of co-variation: counties that score high on one barrier tend to score high on others. The PC1 loadings (after sign correction) tell you how much each dimension contributes to this dominant pattern.

This is defensible because it makes no external assumptions. The weights emerge from the data. If broadband exclusion and poverty are highly correlated across counties (they are), the PCA will weight them together and reflect their shared information content. This is the same approach used in the UNDP Human Development Index research tradition and in a significant body of composite indicator literature (Nardo et al., 2005).

**On spatial autocorrelation and Moran's I.** A key empirical question about mobility barriers is whether they are geographically clustered. If high-barrier counties cluster together, it suggests regional structural causes (persistent poverty regions, deindustrialized areas). If they are randomly distributed, it suggests county-specific rather than regional dynamics.

Moran's I quantifies this. The statistic ranges from -1 (perfect dispersion) to +1 (perfect clustering), with 0 indicating random spatial distribution. Under standard queen contiguity weighting (counties that share any border point are neighbors), U.S. county-level socioeconomic variables typically show Moran's I between 0.4 and 0.7, indicating strong positive spatial autocorrelation. This is an important finding: it means that interventions in one county may have spillover effects on neighboring counties, and that regional policy (not just county-by-county intervention) is warranted.

**On the Census Bureau API and ACS data.** The American Community Survey is the Census Bureau's continuous survey of U.S. households, replacing the long-form decennial census. The 5-year estimates aggregate five years of survey responses to produce reliable estimates at small geographies (counties, census tracts, block groups). The variables Stratum uses are: median household income (B19013), educational attainment by level (B15003), housing cost burden (B25070), internet access by type (B28002), poverty status (B17001), and employment status (B23025).

The Census API is free with a simple registration. It returns data in JSON format for any combination of variables and geographies.

---

### PHASE 3: System Architecture

Before writing code, I designed the full pipeline.

**Data ingestion layer (src/data/).** Two modules handle all external data communication.

`census.py` fetches the ACS 5-year estimates for all U.S. counties via the Census Bureau API. It constructs FIPS codes (the standard county identifier: two-digit state code + three-digit county code), derives rate variables from raw counts, and implements a local cache to avoid redundant API calls. The first run fetches everything from the API (about 3,200 rows, roughly 30 seconds). Subsequent runs load from a local CSV file in under a second.

`opportunity.py` downloads county-level mobility data from the Opportunity Insights public data repository. The key variable is `kfr_pooled_pooled_p25`: mean household income rank at age 35 for children from the 25th percentile. This is normalized to [0,1] before use.

**Analysis layer (src/analysis/).** Two modules implement the core quantitative methods.

`mbi.py` is the computational core. It constructs the six barrier dimensions, runs PCA to derive weights, computes the weighted composite MBI for each county, scales to 0-100, categorizes counties into five barrier levels, and computes factor contributions (the weighted contribution of each dimension to each county's MBI). It also runs factor regression (OLS of MBI on each individual dimension) to produce partial R-squared statistics showing which factors most uniquely explain MBI variation.

`spatial.py` implements Moran's I spatial autocorrelation analysis and a Census region summary. The full queen contiguity version requires a shapefile and libpysal; Stratum implements a computationally tractable approximation using state-level grouping as a spatial proxy.

**Visualization layer (src/visualization/).** `dashboard.py` builds the Plotly Dash interactive dashboard with six panels: a national choropleth map, a county-level factor breakdown (appears on click), a national MBI distribution histogram, a Census region comparison bar chart, a PCA weight visualization, and top/bottom county tables.

**Entry point.** `stratum.py` orchestrates the full pipeline with a command-line interface, progress reporting, and text summary output.

---

### PHASE 4: Implementing the Math

**The PCA weighting decision.** This was the methodological choice I thought hardest about. The alternative to PCA is equal weighting (each of the six dimensions contributes 1/6 of the final score) or hand-assigned weights (income is 25%, education is 20%, etc.). Both are defensible for different reasons.

Equal weighting has the virtue of simplicity and transparency: no external assumptions. But it treats broadband exclusion as equally important as poverty, which may not reflect empirical reality.

Hand-assigned weights can incorporate domain knowledge but require justification and are inherently subjective. Two researchers could defend completely different weight choices.

PCA weighting is data-driven: the weights emerge from the covariance structure of the data itself. The limitation is that it measures statistical co-variation, not causal importance. A dimension that is highly correlated with others will receive a lower unique weight even if it is causally important in its own right.

I chose PCA for defensibility, documented the limitation explicitly, and included individual factor regression as a complement (partial R-squared shows each factor's independent explanatory power regardless of the PCA weights).

**Normalization.** All six dimensions must be on the same scale before PCA or any composite computation. I used min-max normalization to [0,1], oriented so 1.0 = maximum barrier. This means income is inverted (low income maps to 1.0), education is inverted (low attainment maps to 1.0), and poverty and housing burden are direct (high rates map to 1.0).

The choice of normalization matters. Z-score normalization (subtracting mean and dividing by standard deviation) preserves the relative spread of each variable. Min-max normalization compresses everything to [0,1] and is sensitive to outliers. I chose min-max because it produces an intuitively interpretable 0-1 scale, but flagged that extreme counties pull the scale.

**The Moran's I implementation.** Full spatial autocorrelation requires a queen contiguity weight matrix, which requires loading a county boundary shapefile and computing shared-boundary relationships between all pairs of counties. This is computationally and dependency-heavy. Stratum implements an approximation using state-level grouping (counties in the same state are treated as neighbors) that runs without geopandas or libpysal. The docs note where to find the full implementation.

---

### PHASE 5: Results

The Stratum pipeline computes MBI for approximately 3,100 U.S. counties. Several findings are consistent across different runs (the exact numbers vary slightly depending on ACS vintage year).

PC1 consistently explains 55-65% of variance across the six barrier dimensions, which validates the composite index approach: the six dimensions share substantial underlying variance, meaning there is a real latent construct being measured. If they were uncorrelated, PC1 would explain only 1/6 = 16.7% of variance.

The regional pattern is consistent with existing mobility research: the South has significantly higher mean MBI than the Northeast or West, with rural Appalachian counties, the Mississippi Delta, and the Deep South consistently appearing among the highest-barrier counties. This reflects the persistent poverty regions documented extensively in the economics literature.

Broadband exclusion and educational attainment consistently receive the highest PCA weights, suggesting they are the dimensions most strongly co-varying with overall barrier levels. This is a notable finding given that broadband is a relatively recent policy concern: it has become as structurally determinative of opportunity as income and education.

The factor regression reveals an important divergence: poverty has the highest partial R-squared (it is the single best predictor of MBI if you had to pick one), but the PCA weight on poverty is lower because poverty co-varies substantially with other dimensions. Counties with high poverty almost always have low income, low education, and low mobility. This shared variance gets captured in the composite, but the regression picks up poverty's independent explanatory power.

Running `python stratum.py` locally and clicking any high-barrier county on the map produces the factor decomposition. This is the practical use case: a researcher or policymaker who wants to understand not just that a county has a high barrier score, but which specific structural factor is driving it and therefore where intervention would have the most leverage.

---

### PHASE 6: Reflection

**On composite indices and their discontents.** Building a composite index forces you to confront every methodological assumption you have. Every choice (which variables to include, how to normalize them, how to weight them, how to handle missing data) shapes the result in ways that can be gamed if you want to manufacture a particular outcome. The only honest response is to document every choice, explain the rationale, make the code fully open source, and acknowledge the limitations explicitly.

The most important limitation of Stratum is that MBI measures structural barriers, not causes of low mobility. High housing cost burden in a county may reflect rapid economic growth (expensive housing because jobs are arriving) rather than structural deprivation. The index treats them identically. This is a known limitation of cross-sectional composite indices and it is documented in the methodology paper.

**On the relationship between data availability and insight.** Everything Stratum uses is free and public. The Census Bureau, Opportunity Insights, and BLS make their data available at no cost because it was collected with public funds for the explicit purpose of informing research and policy. The gap was not data. The gap was a tool that combined the data in a useful way and made it accessible to non-experts.

This is a recurring pattern in the domains I have worked in. The DermEquity dataset (Fitzpatrick17k) was publicly available before I used it. The FRED macroeconomic data that NEXUS uses is freely maintained by the Federal Reserve. The bottleneck is almost never data. It is the methodology to use the data well and the engineering to make the methodology accessible.

**On PCA and what "data-driven" actually means.** PCA weights are sometimes presented as if they are more objective than hand-assigned weights because they "come from the data." This is partially true and partially misleading. PCA weights come from the covariance structure of your specific dataset, measured at your specific time point, using your specific variable choices. If you had chosen different variables, the weights would be different. If you had used a different ACS vintage year, the weights would be slightly different.

The honest claim is not that PCA weights are objective. It is that they are consistent with the data's own structure, and that this is a more defensible starting point than arbitrary assignment. The distinction matters because it changes how you should interpret the weights: not as statements about causal importance, but as statements about statistical co-variation in the current dataset.

---

### Closing Remarks

Stratum is a tool, not an answer. It can tell you that a county has a high mobility barrier score, and it can decompose that score into its factor contributions. It cannot tell you what to do about it, and it cannot definitively attribute the barrier to any single cause.

What it can do is make a specific kind of question answerable that was previously not: not "which counties have low mobility?" (Opportunity Insights already answers that), but "which counties have low mobility driven primarily by broadband exclusion versus housing cost burden versus educational access?" Those are different counties with different structural situations requiring different interventions.

Making that question answerable for free, for any county in the country, seemed worth the build.

-- Angie X.

Project is open source at github.com/axshoe/stratum.
