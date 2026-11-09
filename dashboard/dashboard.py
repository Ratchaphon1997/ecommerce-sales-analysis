"""
dashboard.py
Interactive Plotly-Dash dashboard for the E-Commerce Sales Analysis portfolio.

Usage:
    python dashboard/dashboard.py
Then open http://localhost:8050 in your browser.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

try:
    import dash
    from dash import dcc, html, Input, Output, callback
except ImportError:
    print("Please install dash: pip install dash")
    raise

from eda import load_data, compute_kpis, monthly_revenue, category_revenue, rfm_segmentation

# ─── Load & preprocess ────────────────────────────────────────────────────────
DATA    = load_data()
orders  = DATA["orders"]
items   = DATA["order_items"]
prods   = DATA["products"]
custs   = DATA["customers"]
KPI     = compute_kpis(orders)
REV     = monthly_revenue(orders)
CAT_REV = category_revenue(orders, items, prods)
RFM     = rfm_segmentation(orders)

# ─── Colour scheme ────────────────────────────────────────────────────────────
COLORS  = px.colors.qualitative.Bold
BG      = "#F8F9FA"
CARD_BG = "#FFFFFF"
ACCENT  = "#4361EE"

# ─── App ──────────────────────────────────────────────────────────────────────
app = dash.Dash(__name__, title="E-Commerce Analytics Dashboard")

def kpi_card(label: str, value: str, delta: str = "", color: str = ACCENT):
    return html.Div([
        html.P(label, style={"margin": "0", "color": "#6C757D", "fontSize": "13px"}),
        html.H3(value, style={"margin": "4px 0", "color": color, "fontWeight": "700"}),
        html.P(delta, style={"margin": "0", "color": "#28A745", "fontSize": "12px"}),
    ], style={
        "background": CARD_BG, "borderRadius": "12px",
        "padding": "16px 20px", "flex": "1",
        "boxShadow": "0 2px 8px rgba(0,0,0,.08)",
        "minWidth": "160px",
    })


def build_layout():
    rev_m    = KPI["total_revenue"]
    orders_n = KPI["total_orders"]
    aov      = KPI["avg_order_value"]
    custs_n  = KPI["unique_customers"]
    ret_r    = KPI["return_rate"]
    can_r    = KPI["cancellation_rate"]

    return html.Div(style={"fontFamily": "Inter, sans-serif", "background": BG,
                            "minHeight": "100vh", "padding": "24px"}, children=[
        # ── Header
        html.Div([
            html.H1("🛒 E-Commerce Sales Dashboard", style={"margin": "0", "color": "#212529"}),
            html.P("2023–2024 · Portfolio Project · Data Analysis",
                   style={"margin": "4px 0 0", "color": "#6C757D"}),
        ], style={"marginBottom": "24px"}),

        # ── KPI Row
        html.Div([
            kpi_card("Total Revenue",    f"฿{rev_m:,.0f}"),
            kpi_card("Total Orders",     f"{orders_n:,}"),
            kpi_card("Avg Order Value",  f"฿{aov:,.0f}"),
            kpi_card("Unique Customers", f"{custs_n:,}"),
            kpi_card("Return Rate",      f"{ret_r:.1f}%",  color="#DC3545"),
            kpi_card("Cancellation",     f"{can_r:.1f}%",  color="#FD7E14"),
        ], style={"display": "flex", "gap": "16px", "marginBottom": "24px", "flexWrap": "wrap"}),

        # ── Trend chart
        html.Div([
            html.H5("Monthly Revenue Trend", style={"margin": "0 0 12px", "color": "#495057"}),
            dcc.Graph(id="monthly-trend", style={"height": "340px"}),
        ], style={"background": CARD_BG, "borderRadius": "12px",
                  "padding": "20px", "marginBottom": "20px",
                  "boxShadow": "0 2px 8px rgba(0,0,0,.08)"}),

        # ── Category + Channel side-by-side
        html.Div([
            html.Div([
                html.H5("Revenue by Category", style={"margin": "0 0 12px", "color": "#495057"}),
                dcc.Graph(id="cat-chart", style={"height": "320px"}),
            ], style={"background": CARD_BG, "borderRadius": "12px",
                      "padding": "20px", "flex": "1",
                      "boxShadow": "0 2px 8px rgba(0,0,0,.08)"}),
            html.Div([
                html.H5("Sales Channel Mix", style={"margin": "0 0 12px", "color": "#495057"}),
                dcc.Graph(id="channel-chart", style={"height": "320px"}),
            ], style={"background": CARD_BG, "borderRadius": "12px",
                      "padding": "20px", "flex": "1",
                      "boxShadow": "0 2px 8px rgba(0,0,0,.08)"}),
        ], style={"display": "flex", "gap": "20px", "marginBottom": "20px"}),

        # ── RFM scatter
        html.Div([
            html.H5("RFM Customer Segmentation", style={"margin": "0 0 12px", "color": "#495057"}),
            dcc.Graph(id="rfm-scatter", style={"height": "420px"}),
        ], style={"background": CARD_BG, "borderRadius": "12px",
                  "padding": "20px", "boxShadow": "0 2px 8px rgba(0,0,0,.08)"}),
    ])


app.layout = build_layout()


# ─── Callbacks ────────────────────────────────────────────────────────────────
@app.callback(Output("monthly-trend", "figure"), Input("monthly-trend", "id"))
def update_trend(_):
    df = REV.copy()
    df["year_month"] = df["year_month"].astype(str)
    df["MA3"] = df["revenue"].rolling(3).mean()

    fig = make_subplots()
    fig.add_trace(go.Bar(x=df["year_month"], y=df["revenue"],
                         name="Revenue", marker_color=ACCENT, opacity=0.75))
    fig.add_trace(go.Scatter(x=df["year_month"], y=df["MA3"],
                              name="3-Month MA", line=dict(color="#F72585", width=2.5)))
    fig.update_layout(paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
                      legend=dict(orientation="h", y=1.1),
                      yaxis_tickprefix="฿", yaxis_tickformat=",.0f",
                      margin=dict(l=10, r=10, t=10, b=40))
    return fig


@app.callback(Output("cat-chart", "figure"), Input("cat-chart", "id"))
def update_cat(_):
    fig = px.bar(CAT_REV.sort_values("revenue"), x="revenue", y="category",
                 orientation="h", color="category",
                 color_discrete_sequence=COLORS)
    fig.update_layout(paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
                      showlegend=False, yaxis_title="",
                      xaxis_tickprefix="฿", xaxis_tickformat=",.0f",
                      margin=dict(l=10, r=10, t=10, b=10))
    return fig


@app.callback(Output("channel-chart", "figure"), Input("channel-chart", "id"))
def update_channel(_):
    ch = (orders[orders["status"] == "Completed"]
          .groupby("channel")["total_amount"].sum()
          .reset_index())
    fig = px.pie(ch, names="channel", values="total_amount",
                 color_discrete_sequence=COLORS, hole=0.45)
    fig.update_layout(paper_bgcolor=CARD_BG, margin=dict(l=10, r=10, t=10, b=10))
    return fig


@app.callback(Output("rfm-scatter", "figure"), Input("rfm-scatter", "id"))
def update_rfm(_):
    fig = px.scatter(RFM, x="Frequency", y="Monetary", color="Segment",
                     size="Monetary", size_max=25,
                     hover_data=["customer_id", "Recency"],
                     color_discrete_sequence=COLORS, opacity=0.7)
    fig.update_layout(paper_bgcolor=CARD_BG, plot_bgcolor=CARD_BG,
                      yaxis_tickprefix="฿", yaxis_tickformat=",.0f",
                      margin=dict(l=10, r=10, t=10, b=10))
    return fig


if __name__ == "__main__":
    app.run(debug=True, port=8050)
