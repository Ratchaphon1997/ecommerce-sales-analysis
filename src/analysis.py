"""
analysis.py
Complete end-to-end analysis script — runs all analyses and saves charts to reports/.
Mirrors the Jupyter notebook 01_eda_full_analysis.ipynb in script form.
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from pathlib import Path

from eda import (
    load_data, compute_kpis, monthly_revenue,
    category_revenue, rfm_segmentation,
    set_style, PALETTE, fmt_thb,
    plot_monthly_revenue, plot_rfm_scatter,
)

REPORT_DIR = Path(__file__).parent.parent / "reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

set_style()


def save(fig: plt.Figure, name: str):
    path = REPORT_DIR / name
    fig.savefig(path, bbox_inches="tight", dpi=150)
    print(f"  Saved -> {path.name}")
    plt.close(fig)


def run():
    print("Loading data...")
    data       = load_data()
    orders     = data["orders"]
    items      = data["order_items"]
    prods      = data["products"]
    custs      = data["customers"]

    # ── KPIs ──────────────────────────────────────────────────────────────────
    kpis = compute_kpis(orders)
    print("\nKEY PERFORMANCE INDICATORS")
    print(f"  Total Revenue     : THB {kpis['total_revenue']:>15,.2f}")
    print(f"  Total Orders      : {kpis['total_orders']:>15,}")
    print(f"  Avg Order Value   : THB {kpis['avg_order_value']:>15,.2f}")
    print(f"  Unique Customers  : {kpis['unique_customers']:>15,}")
    print(f"  Return Rate       : {kpis['return_rate']:>14.2f}%")
    print(f"  Cancellation Rate : {kpis['cancellation_rate']:>14.2f}%")

    # ── 1. Monthly Revenue ────────────────────────────────────────────────────
    print("\n[1/6] Monthly revenue trend...")
    rev = monthly_revenue(orders)
    fig, ax = plt.subplots(figsize=(14, 5))
    plot_monthly_revenue(rev, ax)
    save(fig, "01_monthly_revenue.png")

    # ── 2. Category revenue ───────────────────────────────────────────────────
    print("[2/6] Category revenue breakdown...")
    cat_rev = category_revenue(orders, items, prods)
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Bar chart
    sns.barplot(data=cat_rev, x="revenue", y="category",
                palette=PALETTE, ax=axes[0])
    axes[0].xaxis.set_major_formatter(mticker.FuncFormatter(fmt_thb))
    axes[0].set_title("Revenue by Category", fontweight="bold")
    axes[0].set_xlabel("")

    # Pie chart
    axes[1].pie(cat_rev["revenue"], labels=cat_rev["category"],
                colors=PALETTE[:len(cat_rev)], autopct="%1.1f%%",
                startangle=140, pctdistance=0.82,
                wedgeprops=dict(width=0.6))
    axes[1].set_title("Revenue Share by Category", fontweight="bold")
    fig.suptitle("Product Category Analysis", fontsize=16, fontweight="bold", y=1.01)
    save(fig, "02_category_revenue.png")

    # ── 3. Regional performance ───────────────────────────────────────────────
    print("[3/6] Regional performance...")
    region_rev = (
        orders[orders["status"] == "Completed"]
        .groupby("region")["total_amount"]
        .agg(["sum", "count", "mean"])
        .rename(columns={"sum": "revenue", "count": "orders", "mean": "aov"})
        .reset_index()
        .sort_values("revenue", ascending=False)
    )
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    sns.barplot(data=region_rev, x="region", y="revenue",
                palette=PALETTE, ax=axes[0])
    axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(fmt_thb))
    axes[0].set_title("Revenue by Region", fontweight="bold")

    sns.barplot(data=region_rev, x="region", y="aov",
                palette=PALETTE, ax=axes[1])
    axes[1].yaxis.set_major_formatter(mticker.FuncFormatter(fmt_thb))
    axes[1].set_title("Avg Order Value by Region", fontweight="bold")
    save(fig, "03_regional_performance.png")

    # ── 4. Customer demographics ──────────────────────────────────────────────
    print("[4/6] Customer demographics...")
    fig, axes = plt.subplots(1, 3, figsize=(16, 5))

    # Age distribution
    axes[0].hist(custs["age"], bins=20, color=PALETTE[0], edgecolor="white")
    axes[0].set_title("Age Distribution", fontweight="bold")
    axes[0].set_xlabel("Age")

    # Gender
    gender_counts = custs["gender"].value_counts()
    axes[1].pie(gender_counts.values, labels=gender_counts.index,
                colors=PALETTE[:3], autopct="%1.1f%%", startangle=90,
                wedgeprops=dict(width=0.6))
    axes[1].set_title("Gender Mix", fontweight="bold")

    # Loyalty tier
    tier_counts = custs["loyalty_tier"].value_counts()
    sns.barplot(x=tier_counts.index, y=tier_counts.values,
                palette=PALETTE, ax=axes[2])
    axes[2].set_title("Loyalty Tier Distribution", fontweight="bold")
    axes[2].set_ylabel("Customers")
    fig.suptitle("Customer Demographics", fontsize=16, fontweight="bold", y=1.01)
    save(fig, "04_customer_demographics.png")

    # ── 5. RFM segmentation ───────────────────────────────────────────────────
    print("[5/6] RFM segmentation...")
    rfm = rfm_segmentation(orders)
    fig, axes = plt.subplots(1, 2, figsize=(16, 7))
    plot_rfm_scatter(rfm, axes[0])

    # Segment count
    seg_counts = rfm["Segment"].value_counts().reset_index()
    seg_counts.columns = ["Segment", "Count"]
    sns.barplot(data=seg_counts, x="Count", y="Segment",
                palette=PALETTE, ax=axes[1])
    axes[1].set_title("Customers per Segment", fontweight="bold")
    axes[1].set_xlabel("Number of Customers")
    fig.suptitle("RFM Customer Segmentation", fontsize=16, fontweight="bold", y=1.01)
    save(fig, "05_rfm_segmentation.png")

    # ── 6. Channel & payment mix ──────────────────────────────────────────────
    print("[6/6] Channel & payment analysis...")
    comp = orders[orders["status"] == "Completed"]
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    ch_data = comp.groupby("channel")["total_amount"].sum().sort_values(ascending=False)
    sns.barplot(x=ch_data.index, y=ch_data.values,
                palette=PALETTE, ax=axes[0])
    axes[0].yaxis.set_major_formatter(mticker.FuncFormatter(fmt_thb))
    axes[0].set_title("Revenue by Sales Channel", fontweight="bold")

    pay_data = comp["payment"].value_counts()
    axes[1].pie(pay_data.values, labels=pay_data.index,
                colors=PALETTE[:4], autopct="%1.1f%%", startangle=90,
                wedgeprops=dict(width=0.6))
    axes[1].set_title("Payment Method Distribution", fontweight="bold")
    fig.suptitle("Channel & Payment Analysis", fontsize=16, fontweight="bold", y=1.01)
    save(fig, "06_channel_payment.png")

    print("\nAll charts saved to reports/")


if __name__ == "__main__":
    run()
