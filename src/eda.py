"""
eda.py
Exploratory Data Analysis utilities for the e-commerce portfolio project.
Shared helper functions used by both Jupyter notebooks and the dashboard.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path

# ─── Style ────────────────────────────────────────────────────────────────────
PALETTE = ["#4361EE", "#F72585", "#7209B7", "#3A0CA3", "#4CC9F0", "#F77F00"]
SECONDARY = "#E9ECEF"

def set_style():
    sns.set_theme(style="whitegrid", palette=PALETTE)
    plt.rcParams.update({
        "figure.dpi":       120,
        "axes.spines.top":  False,
        "axes.spines.right": False,
        "font.family":      "DejaVu Sans",
    })


# ─── Data Loaders ─────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent.parent / "data" / "raw"

def load_data() -> dict[str, pd.DataFrame]:
    """Load all raw CSVs and apply basic type casting."""
    customers  = pd.read_csv(DATA_DIR / "customers.csv", parse_dates=["signup_date"])
    products   = pd.read_csv(DATA_DIR / "products.csv")
    orders     = pd.read_csv(DATA_DIR / "orders.csv",    parse_dates=["order_date"])
    order_items = pd.read_csv(DATA_DIR / "order_items.csv")
    return {
        "customers":   customers,
        "products":    products,
        "orders":      orders,
        "order_items": order_items,
    }


# ─── KPI helpers ──────────────────────────────────────────────────────────────
def compute_kpis(orders: pd.DataFrame) -> dict:
    completed = orders[orders["status"] == "Completed"]
    return {
        "total_revenue":     completed["total_amount"].sum(),
        "total_orders":      len(completed),
        "avg_order_value":   completed["total_amount"].mean(),
        "unique_customers":  completed["customer_id"].nunique(),
        "return_rate":       (orders["status"] == "Returned").mean() * 100,
        "cancellation_rate": (orders["status"] == "Cancelled").mean() * 100,
    }


def monthly_revenue(orders: pd.DataFrame) -> pd.DataFrame:
    df = orders[orders["status"] == "Completed"].copy()
    df["year_month"] = df["order_date"].dt.to_period("M")
    return (
        df.groupby("year_month")["total_amount"]
        .sum()
        .reset_index()
        .rename(columns={"total_amount": "revenue"})
    )


def category_revenue(orders: pd.DataFrame, order_items: pd.DataFrame,
                     products: pd.DataFrame) -> pd.DataFrame:
    merged = (
        order_items
        .merge(orders[orders["status"] == "Completed"][["order_id"]], on="order_id")
        .merge(products[["product_id", "category"]], on="product_id")
    )
    return (
        merged.groupby("category")["subtotal"]
        .sum()
        .reset_index()
        .rename(columns={"subtotal": "revenue"})
        .sort_values("revenue", ascending=False)
    )


def rfm_segmentation(orders: pd.DataFrame) -> pd.DataFrame:
    """Classic RFM analysis — returns labelled customer segments."""
    snapshot = orders["order_date"].max() + pd.Timedelta(days=1)
    completed = orders[orders["status"] == "Completed"]

    rfm = (
        completed.groupby("customer_id")
        .agg(
            Recency  = ("order_date", lambda x: (snapshot - x.max()).days),
            Frequency= ("order_id",   "count"),
            Monetary = ("total_amount","sum"),
        )
        .reset_index()
    )

    rfm["R_score"] = pd.qcut(rfm["Recency"],   q=4, labels=[4, 3, 2, 1], duplicates="drop").astype(int)
    rfm["F_score"] = pd.qcut(rfm["Frequency"], q=4, labels=[1, 2, 3, 4], duplicates="drop").astype(int)
    rfm["M_score"] = pd.qcut(rfm["Monetary"],  q=4, labels=[1, 2, 3, 4], duplicates="drop").astype(int)
    rfm["RFM_sum"] = rfm["R_score"] + rfm["F_score"] + rfm["M_score"]

    def segment(row):
        if row["RFM_sum"] >= 10:
            return "Champions"
        elif row["R_score"] >= 3 and row["F_score"] >= 3:
            return "Loyal Customers"
        elif row["R_score"] >= 3:
            return "Potential Loyalists"
        elif row["R_score"] <= 2 and row["F_score"] >= 3:
            return "At Risk"
        elif row["RFM_sum"] <= 5:
            return "Lost / Churned"
        else:
            return "Need Attention"

    rfm["Segment"] = rfm.apply(segment, axis=1)
    return rfm


# ─── Plot helpers ─────────────────────────────────────────────────────────────
def fmt_thb(x, pos=None):
    """Matplotlib formatter — formats large numbers with ฿ prefix."""
    if x >= 1_000_000:
        return f"฿{x/1_000_000:.1f}M"
    elif x >= 1_000:
        return f"฿{x/1_000:.0f}K"
    return f"฿{x:.0f}"


def plot_monthly_revenue(rev_df: pd.DataFrame, ax: plt.Axes = None) -> plt.Axes:
    if ax is None:
        _, ax = plt.subplots(figsize=(14, 5))
    xs = rev_df["year_month"].astype(str)
    ax.bar(xs, rev_df["revenue"], color=PALETTE[0], alpha=0.75, label="Revenue")
    ax.plot(xs, rev_df["revenue"].rolling(3).mean(),
            color=PALETTE[1], linewidth=2.5, label="3-month MA")
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_thb))
    ax.set_xticklabels(xs, rotation=45, ha="right", fontsize=8)
    ax.set_title("Monthly Revenue with 3-Month Moving Average", fontsize=14, fontweight="bold")
    ax.legend()
    return ax


def plot_rfm_scatter(rfm: pd.DataFrame, ax: plt.Axes = None) -> plt.Axes:
    if ax is None:
        _, ax = plt.subplots(figsize=(10, 7))
    segments = rfm["Segment"].unique()
    colors   = dict(zip(segments, PALETTE))
    for seg in segments:
        subset = rfm[rfm["Segment"] == seg]
        ax.scatter(subset["Frequency"], subset["Monetary"],
                   c=colors[seg], label=seg, alpha=0.6, edgecolors="none", s=40)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_thb))
    ax.set_xlabel("Purchase Frequency")
    ax.set_ylabel("Total Spend (฿)")
    ax.set_title("RFM Customer Segmentation", fontsize=14, fontweight="bold")
    ax.legend(loc="upper left", framealpha=0.8)
    return ax
