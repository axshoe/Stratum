import os
import sys

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

print("Loading Census data...")

from src.data.census import load_or_fetch as load_census
from src.data.opportunity import load_or_fetch as load_mobility
from src.analysis.mbi import compute_mbi, factor_regression
from src.visualization.dashboard import create_app

# Load data
census_df = load_census()
mobility_df = load_mobility()

# Merge datasets
df = census_df.merge(mobility_df, on="fips", how="left")

# Compute MBI
df_mbi, meta = compute_mbi(df)

# Regression analysis
reg_df = factor_regression(df_mbi)

print("MBI computed for {} counties. Launching server...".format(meta["n_counties"]))

# Create app
app = create_app(df_mbi, meta, reg_df)
server = app.server