# src/visualization/dashboard.py
# ─────────────────────────────────────────────────────────────────────────────
# Stratum Interactive Dashboard
# Built with Plotly Dash + Bootstrap
#
# Panels:
#   1. Choropleth map — MBI by county, color-coded
#   2. Factor breakdown bar — click any county to see its dimension scores
#   3. Distribution histogram — national MBI distribution
#   4. Regional comparison — bar chart by Census region
#   5. Factor importance — PCA weight visualization
#   6. Top/bottom counties table
# ─────────────────────────────────────────────────────────────────────────────

import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash
from dash import dcc, html, Input, Output, dash_table
import dash_bootstrap_components as dbc

from ..analysis.mbi import DIMENSIONS
from ..analysis.spatial import regional_summary


def create_app(df: pd.DataFrame, meta: dict, regression_df: pd.DataFrame) -> dash.Dash:
    """
    Create and configure the Stratum Dash application.

    Args:
        df:             DataFrame with MBI scores for all counties
        meta:           Dict with PCA weights and summary stats
        regression_df:  Factor importance DataFrame from factor_regression()

    Returns:
        Configured Dash app instance (call app.run_server() to launch)
    """
    app = dash.Dash(
        __name__,
        external_stylesheets=[dbc.themes.FLATLY],
        title="Stratum — Mobility Barrier Index",
        meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
    )

    # ── Color palette ─────────────────────────────────────────────────────────
    COLOR_SCALE = [
        [0.0,  "#2C7BB6"],   # Low barrier — blue
        [0.25, "#ABD9E9"],
        [0.5,  "#FFFFBF"],   # Moderate — yellow
        [0.75, "#FDAE61"],
        [1.0,  "#D7191C"],   # High barrier — red
    ]
    ACCENT = "#2C7BB6"
    BG = "#F8F9FA"
    CARD_STYLE = {"borderRadius": "8px", "boxShadow": "0 1px 4px rgba(0,0,0,0.08)", "padding": "16px"}

    # ── Choropleth map ────────────────────────────────────────────────────────
    fig_map = px.choropleth(
        df,
        geojson="https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json",
        locations="fips",
        color="mbi",
        color_continuous_scale=COLOR_SCALE,
        range_color=[0, 100],
        scope="usa",
        hover_name="county_name",
        hover_data={
            "fips": False,
            "state": True,
            "mbi": ":.1f",
            "mbi_category": True,
            "poverty_rate": ":.1%",
            "broadband_rate": ":.1%",
            "edu_rate": ":.1%",
        },
        labels={
            "mbi": "MBI Score",
            "mbi_category": "Barrier Level",
            "poverty_rate": "Poverty Rate",
            "broadband_rate": "Broadband Access",
            "edu_rate": "Bachelor's Attainment",
        },
        title=None,
    )
    fig_map.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        paper_bgcolor=BG,
        coloraxis_colorbar=dict(
            title="MBI",
            thickness=14,
            len=0.8,
            tickvals=[0, 20, 40, 60, 80, 100],
            ticktext=["0", "20", "40", "60", "80", "100"],
        ),
    )

    # ── Distribution histogram ────────────────────────────────────────────────
    fig_dist = px.histogram(
        df, x="mbi", nbins=50,
        color_discrete_sequence=[ACCENT],
        labels={"mbi": "MBI Score", "count": "Counties"},
        opacity=0.8,
    )
    fig_dist.update_layout(
        paper_bgcolor=BG, plot_bgcolor=BG,
        xaxis_title="MBI Score (0 = no barriers, 100 = maximum barriers)",
        yaxis_title="Number of counties",
        margin={"t": 10, "b": 40},
        bargap=0.02,
    )

    # ── Regional comparison ───────────────────────────────────────────────────
    reg_df = regional_summary(df)
    fig_regional = px.bar(
        reg_df, x="region", y="mean_mbi",
        error_y="std_mbi",
        color="mean_mbi",
        color_continuous_scale=COLOR_SCALE,
        range_color=[0, 100],
        labels={"region": "Census Region", "mean_mbi": "Mean MBI"},
        text="mean_mbi",
    )
    fig_regional.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig_regional.update_layout(
        paper_bgcolor=BG, plot_bgcolor=BG,
        showlegend=False, coloraxis_showscale=False,
        margin={"t": 10},
    )

    # ── PCA weights chart ─────────────────────────────────────────────────────
    weights_df = pd.DataFrame([
        {"Dimension": DIMENSIONS[k], "Weight": v * 100}
        for k, v in meta["weights"].items()
    ]).sort_values("Weight", ascending=True)

    fig_weights = px.bar(
        weights_df, x="Weight", y="Dimension", orientation="h",
        color="Weight",
        color_continuous_scale=[[0, "#ABD9E9"], [1, "#2C7BB6"]],
        labels={"Weight": "PCA Weight (%)", "Dimension": ""},
        text="Weight",
    )
    fig_weights.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    fig_weights.update_layout(
        paper_bgcolor=BG, plot_bgcolor=BG,
        coloraxis_showscale=False,
        margin={"t": 10, "l": 180},
        xaxis_range=[0, weights_df["Weight"].max() * 1.3],
    )

    # ── Layout ────────────────────────────────────────────────────────────────
    app.layout = dbc.Container(fluid=True, children=[

        # Header
        dbc.Row([
            dbc.Col([
                html.H2("STRATUM", style={"fontFamily": "monospace", "fontWeight": "900",
                                          "letterSpacing": "0.15em", "color": "#1a1a2e", "margin": "0"}),
                html.P("Mobility Barrier Index — U.S. County Level Analysis",
                       style={"color": "#666", "margin": "0 0 4px", "fontSize": "13px"}),
                html.P(
                    f"{meta['n_counties']:,} counties · "
                    f"Mean MBI: {meta['mbi_mean']:.1f} · "
                    f"PC1 explains {meta['explained_variance']*100:.1f}% of barrier variance",
                    style={"fontSize": "11px", "color": "#999", "margin": 0}
                ),
            ], width=8),
            dbc.Col([
                dbc.Row([
                    dbc.Col(dbc.Card([
                        html.P("Mean MBI", className="text-muted mb-0", style={"fontSize": "11px"}),
                        html.H4(f"{meta['mbi_mean']:.1f}", className="mb-0"),
                    ], body=True, style={"textAlign": "center", "padding": "8px"})),
                    dbc.Col(dbc.Card([
                        html.P("High Barrier Counties", className="text-muted mb-0", style={"fontSize": "11px"}),
                        html.H4(f"{(df['mbi'] >= 60).sum():,}", className="mb-0"),
                    ], body=True, style={"textAlign": "center", "padding": "8px"})),
                ])
            ], width=4),
        ], className="mb-3 mt-3 align-items-center"),

        # Map row
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    html.P("Click any county to see its factor breakdown below.",
                           style={"fontSize": "11px", "color": "#999", "margin": "0 0 8px"}),
                    dcc.Graph(id="choropleth", figure=fig_map,
                              style={"height": "460px"},
                              config={"scrollZoom": False}),
                ], body=True, style=CARD_STYLE),
            ], width=12),
        ], className="mb-3"),

        # County detail panel (appears on click)
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    html.Div(id="county-detail", children=[
                        html.P("Click any county on the map to see its factor breakdown.",
                               style={"color": "#999", "textAlign": "center", "padding": "20px 0"}),
                    ])
                ], body=True, style=CARD_STYLE),
            ], width=12),
        ], className="mb-3"),

        # Bottom charts row
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    html.H6("National MBI distribution", style={"fontSize": "13px", "fontWeight": "500"}),
                    dcc.Graph(figure=fig_dist, style={"height": "220px"},
                              config={"displayModeBar": False}),
                ], body=True, style=CARD_STYLE),
            ], width=4),

            dbc.Col([
                dbc.Card([
                    html.H6("Mean MBI by Census region", style={"fontSize": "13px", "fontWeight": "500"}),
                    dcc.Graph(figure=fig_regional, style={"height": "220px"},
                              config={"displayModeBar": False}),
                ], body=True, style=CARD_STYLE),
            ], width=4),

            dbc.Col([
                dbc.Card([
                    html.H6("PCA factor weights", style={"fontSize": "13px", "fontWeight": "500"}),
                    html.P(f"PC1 explains {meta['explained_variance']*100:.1f}% of cross-county variance",
                           style={"fontSize": "11px", "color": "#999", "margin": "0 0 4px"}),
                    dcc.Graph(figure=fig_weights, style={"height": "200px"},
                              config={"displayModeBar": False}),
                ], body=True, style=CARD_STYLE),
            ], width=4),
        ], className="mb-3"),

        # Top/bottom counties table
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    html.H6("10 highest barrier counties", style={"fontSize": "13px", "fontWeight": "500"}),
                    dash_table.DataTable(
                        data=df.nlargest(10, "mbi")[["county_name", "state", "mbi", "mbi_category",
                                                      "poverty_rate", "broadband_rate", "edu_rate"]].round(3).to_dict("records"),
                        columns=[
                            {"name": "County", "id": "county_name"},
                            {"name": "State", "id": "state"},
                            {"name": "MBI", "id": "mbi", "type": "numeric", "format": {"specifier": ".1f"}},
                            {"name": "Category", "id": "mbi_category"},
                            {"name": "Poverty", "id": "poverty_rate", "type": "numeric", "format": {"specifier": ".1%"}},
                            {"name": "Broadband", "id": "broadband_rate", "type": "numeric", "format": {"specifier": ".1%"}},
                            {"name": "BA Attain.", "id": "edu_rate", "type": "numeric", "format": {"specifier": ".1%"}},
                        ],
                        style_table={"overflowX": "auto"},
                        style_cell={"fontSize": "12px", "padding": "6px 10px", "fontFamily": "monospace"},
                        style_header={"fontWeight": "500", "backgroundColor": "#f0f4f8"},
                        style_data_conditional=[
                            {"if": {"filter_query": "{mbi} >= 80"},
                             "backgroundColor": "#fff0f0"}
                        ],
                        page_size=10,
                    ),
                ], body=True, style=CARD_STYLE),
            ], width=6),

            dbc.Col([
                dbc.Card([
                    html.H6("10 lowest barrier counties", style={"fontSize": "13px", "fontWeight": "500"}),
                    dash_table.DataTable(
                        data=df.nsmallest(10, "mbi")[["county_name", "state", "mbi", "mbi_category",
                                                       "poverty_rate", "broadband_rate", "edu_rate"]].round(3).to_dict("records"),
                        columns=[
                            {"name": "County", "id": "county_name"},
                            {"name": "State", "id": "state"},
                            {"name": "MBI", "id": "mbi", "type": "numeric", "format": {"specifier": ".1f"}},
                            {"name": "Category", "id": "mbi_category"},
                            {"name": "Poverty", "id": "poverty_rate", "type": "numeric", "format": {"specifier": ".1%"}},
                            {"name": "Broadband", "id": "broadband_rate", "type": "numeric", "format": {"specifier": ".1%"}},
                            {"name": "BA Attain.", "id": "edu_rate", "type": "numeric", "format": {"specifier": ".1%"}},
                        ],
                        style_table={"overflowX": "auto"},
                        style_cell={"fontSize": "12px", "padding": "6px 10px", "fontFamily": "monospace"},
                        style_header={"fontWeight": "500", "backgroundColor": "#f0f4f8"},
                        style_data_conditional=[
                            {"if": {"filter_query": "{mbi} < 20"},
                             "backgroundColor": "#f0fff4"}
                        ],
                        page_size=10,
                    ),
                ], body=True, style=CARD_STYLE),
            ], width=6),
        ], className="mb-4"),

        # Footer
        dbc.Row([
            dbc.Col(html.P(
                "STRATUM v1.0 · A. Xiu, 2026 · github.com/axshoe/stratum · "
                "Data: U.S. Census Bureau ACS 2021, Opportunity Insights, BLS · "
                "Not for clinical or policy use without independent validation.",
                style={"fontSize": "10px", "color": "#bbb", "textAlign": "center", "padding": "8px 0 16px"}
            ))
        ]),

    ], style={"backgroundColor": BG, "minHeight": "100vh"})

    # ── Callback: county click ────────────────────────────────────────────────
    @app.callback(
        Output("county-detail", "children"),
        Input("choropleth", "clickData"),
    )
    def update_county_detail(click_data):
        if not click_data:
            return html.P("Click any county on the map to see its factor breakdown.",
                          style={"color": "#999", "textAlign": "center", "padding": "20px 0"})

        try:
            fips = click_data["points"][0]["location"]
            row = df[df["fips"] == fips]
            if row.empty:
                return html.P("County data not available.")
            row = row.iloc[0]

            contrib_cols = [c for c in df.columns if c.startswith("contrib_")]
            contribs = [(DIMENSIONS.get(c.replace("contrib_", ""), c), row[c])
                        for c in contrib_cols if c in row.index]
            contribs.sort(key=lambda x: x[1], reverse=True)

            bar_fig = go.Figure(go.Bar(
                x=[v for _, v in contribs],
                y=[n for n, _ in contribs],
                orientation="h",
                marker_color=["#D7191C" if v > 0.05 else "#ABD9E9" for _, v in contribs],
            ))
            bar_fig.update_layout(
                margin={"t": 0, "b": 30, "l": 10},
                xaxis_title="Weighted contribution to MBI",
                paper_bgcolor=BG, plot_bgcolor=BG,
                height=200,
            )

            mbi_val = row["mbi"]
            color = "#D7191C" if mbi_val >= 60 else "#FDAE61" if mbi_val >= 40 else "#2C7BB6"

            return [
                dbc.Row([
                    dbc.Col([
                        html.H5(f"{row['county_name']}, State {row['state']}",
                                style={"marginBottom": "4px"}),
                        html.Span(f"MBI: {mbi_val:.1f} / 100",
                                  style={"fontSize": "22px", "fontWeight": "700",
                                         "color": color, "marginRight": "12px"}),
                        html.Span(str(row.get("mbi_category", "")),
                                  style={"fontSize": "13px", "color": "#666"}),
                    ], width=4),
                    dbc.Col([
                        dcc.Graph(figure=bar_fig, config={"displayModeBar": False},
                                  style={"height": "200px"}),
                    ], width=8),
                ]),
                dbc.Row([
                    dbc.Col(html.Small(
                        f"Poverty: {row['poverty_rate']:.1%}  |  "
                        f"Broadband: {row['broadband_rate']:.1%}  |  "
                        f"BA Attainment: {row['edu_rate']:.1%}  |  "
                        f"Housing burden: {row['housing_burden_rate']:.1%}  |  "
                        f"Median income: ${row['median_income']:,.0f}",
                        style={"color": "#888"}
                    ))
                ], className="mt-1"),
            ]
        except Exception as e:
            return html.P(f"Error loading county data: {e}", style={"color": "red"})

    return app

# src/visualization/dashboard.py

# Only add at the very bottom
if __name__ == "__main__":
    # Example: load some dummy data to run locally
    import pandas as pd

    # You can replace this with your real data load logic
    df = pd.DataFrame(columns=["fips", "county_name", "state", "mbi", "mbi_category"])
    meta = {"weights": {}, "n_counties": 0, "mbi_mean": 0, "explained_variance": 0.0}
    regression_df = pd.DataFrame()

    app = create_app(df, meta, regression_df)
    server = app.server  # This is what Render will use

    app.run_server(debug=True)