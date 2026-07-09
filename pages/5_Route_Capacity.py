import streamlit as st
import pandas as pd
import plotly.express as px

from utils.data_loader import load_orders
from utils.ui import inject_css, title, section, dataframe_download, blue_table


st.set_page_config(
    page_title="Route & Capacity",
    page_icon="🚚",
    layout="wide",
)

inject_css()


WAREHOUSE_THRESHOLD = 90.0


def show_blue_table(df: pd.DataFrame, max_height: int = 430):
    """Use blue_table when available. Fallback is kept for compatibility."""
    try:
        blue_table(df, max_height=max_height)
    except TypeError:
        blue_table(df)


def ensure_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    df = df.copy()
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def build_capacity_candidates(
    df: pd.DataFrame,
    truck_threshold: float = 85.0,
    warehouse_threshold: float = WAREHOUSE_THRESHOLD,
    carbon_baseline: float = 0.54,
) -> pd.DataFrame:
    """
    Build a practical watchlist for load consolidation and warehouse rebalancing.

    Logic:
    - Low truck utilization means there is room to consolidate shipments.
    - Warehouse utilization above 90% means warehouse flow should be rebalanced.
    - High carbon intensity means the route should be reviewed.
    - High risk score or ETA delay raises priority.
    - If no order triggers the strict rules, the page still shows a top watchlist
      so the dashboard is useful during demo.
    """
    candidates = df.copy()

    numeric_cols = [
        "Truck_Utilization_pct",
        "Warehouse_Utilization_pct",
        "Carbon_Emission_kgCO2_tonkm",
        "Total_Risk_Score",
        "ETA_Variance_Hours",
        "Weight_Ton",
    ]
    candidates = ensure_numeric(candidates, numeric_cols)

    for col in numeric_cols:
        if col not in candidates.columns:
            candidates[col] = 0

    truck_gap = (truck_threshold - candidates["Truck_Utilization_pct"]).clip(lower=0)
    warehouse_gap = (candidates["Warehouse_Utilization_pct"] - warehouse_threshold).clip(lower=0)
    carbon_gap = (candidates["Carbon_Emission_kgCO2_tonkm"] - carbon_baseline).clip(lower=0)
    eta_delay = candidates["ETA_Variance_Hours"].clip(lower=0)
    risk_score = candidates["Total_Risk_Score"].fillna(0)

    candidates["Capacity_Action"] = "Monitor"

    candidates.loc[
        truck_gap > 0,
        "Capacity_Action",
    ] = "Consolidate load with same-route shipments"

    candidates.loc[
        warehouse_gap > 0,
        "Capacity_Action",
    ] = "Rebalance warehouse flow or accelerate cross-dock"

    candidates.loc[
        (truck_gap > 0) & (warehouse_gap > 0),
        "Capacity_Action",
    ] = "Consolidate load and rebalance warehouse flow"

    candidates.loc[
        (truck_gap == 0) & (warehouse_gap == 0) & (carbon_gap > 0),
        "Capacity_Action",
    ] = "Review lower-emission multimodal route"

    candidates.loc[
        (truck_gap == 0)
        & (warehouse_gap == 0)
        & (carbon_gap == 0)
        & ((risk_score >= 45) | (eta_delay > 0)),
        "Capacity_Action",
    ] = "Dynamic routing watchlist"

    candidates["Capacity_Priority_Score"] = (
        truck_gap * 0.35
        + warehouse_gap * 0.35
        + carbon_gap * 25
        + eta_delay * 0.8
        + risk_score * 0.15
    ).round(2)

    strict_candidates = candidates[candidates["Capacity_Action"] != "Monitor"].copy()

    if strict_candidates.empty:
        strict_candidates = candidates.sort_values(
            "Capacity_Priority_Score",
            ascending=False,
        ).head(30).copy()
        strict_candidates["Capacity_Action"] = "Watchlist for capacity optimization"

    return strict_candidates.sort_values(
        "Capacity_Priority_Score",
        ascending=False,
    )


title(
    "Route & Capacity Optimization",
    "Dynamic routing, load consolidation and warehouse utilization control after Control Tower",
)

df = load_orders()

df = ensure_numeric(
    df,
    [
        "Truck_Utilization_pct",
        "Warehouse_Utilization_pct",
        "Carbon_Emission_kgCO2_tonkm",
        "Total_Risk_Score",
        "ETA_Variance_Hours",
        "Weight_Ton",
    ],
)

with st.sidebar:
    st.markdown("### Capacity rules")

    truck_threshold = st.slider(
        "Under-utilized truck threshold (%)",
        min_value=70,
        max_value=95,
        value=85,
        step=1,
    )

    st.info(
        "Warehouse rebalancing rule: trigger when Warehouse Utilization is above 90%."
    )

    carbon_baseline = st.number_input(
        "Carbon baseline (kg CO2/ton-km)",
        min_value=0.00,
        max_value=2.00,
        value=0.54,
        step=0.01,
    )

candidates = build_capacity_candidates(
    df,
    truck_threshold=float(truck_threshold),
    warehouse_threshold=WAREHOUSE_THRESHOLD,
    carbon_baseline=float(carbon_baseline),
)

col1, col2, col3 = st.columns(3)

if "Truck_Utilization_pct" in df.columns:
    col1.metric("Avg truck utilization", f"{df['Truck_Utilization_pct'].mean():.1f}%")
else:
    col1.metric("Avg truck utilization", "N/A")

if "Warehouse_Utilization_pct" in df.columns:
    col2.metric("Avg warehouse utilization", f"{df['Warehouse_Utilization_pct'].mean():.1f}%")
else:
    col2.metric("Avg warehouse utilization", "N/A")

col3.metric("Optimization watchlist", f"{len(candidates):,}")

st.caption(
    "Warehouse Utilization is monitored below 90% to avoid congestion while maintaining capacity efficiency."
)

left, right = st.columns(2)

with left:
    if {"Route", "Truck_Utilization_pct"}.issubset(df.columns):
        route_util = (
            df.groupby("Route", as_index=False)["Truck_Utilization_pct"]
            .mean()
            .sort_values("Truck_Utilization_pct", ascending=False)
        )
        fig = px.bar(
            route_util,
            x="Route",
            y="Truck_Utilization_pct",
            title="Average truck utilization by route",
            text_auto=".1f",
        )
        fig.update_layout(
            xaxis_title="Route",
            yaxis_title="Truck Utilization (%)",
            title_font_color="#0B3D91",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Route or truck utilization data is not available.")

with right:
    if {"Origin", "Warehouse_Utilization_pct"}.issubset(df.columns):
        wh = (
            df.groupby("Origin", as_index=False)["Warehouse_Utilization_pct"]
            .mean()
            .sort_values("Warehouse_Utilization_pct", ascending=False)
        )
        fig = px.bar(
            wh,
            x="Origin",
            y="Warehouse_Utilization_pct",
            title="Average warehouse utilization by origin",
            text_auto=".1f",
        )
        fig.update_layout(
            xaxis_title="Origin",
            yaxis_title="Warehouse Utilization (%)",
            title_font_color="#0B3D91",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Origin or warehouse utilization data is not available.")

section("Route performance")

required_for_perf = {
    "Route",
    "Unified_Shipment_ID",
    "Carbon_Emission_kgCO2_tonkm",
    "Total_Risk_Score",
    "Truck_Utilization_pct",
}

if required_for_perf.issubset(df.columns):
    agg_dict = {
        "Orders": ("Unified_Shipment_ID", "count"),
        "Avg_Carbon": ("Carbon_Emission_kgCO2_tonkm", "mean"),
        "Avg_Risk": ("Total_Risk_Score", "mean"),
        "Avg_Truck_Utilization": ("Truck_Utilization_pct", "mean"),
    }

    if "Warehouse_Utilization_pct" in df.columns:
        agg_dict["Avg_Warehouse_Utilization"] = ("Warehouse_Utilization_pct", "mean")

    if "Weight_Ton" in df.columns:
        agg_dict["Total_Weight_Ton"] = ("Weight_Ton", "sum")

    perf = (
        df.groupby("Route", as_index=False)
        .agg(**agg_dict)
        .sort_values(["Avg_Risk", "Avg_Carbon"], ascending=False)
        .round(2)
    )

    show_blue_table(perf, max_height=360)
else:
    st.info("Not enough fields to build route performance table.")

section("Capacity Optimization Watchlist")

st.markdown(
    """
    This table identifies shipments that should be reviewed for **load consolidation**, 
    **warehouse rebalancing**, **lower-emission routing**, or **dynamic routing watchlist**. 
    It helps the Control Tower prioritize orders that can improve truck utilization, 
    reduce warehouse pressure and support carbon reduction.
    """
)

action_options = ["All"] + sorted(candidates["Capacity_Action"].dropna().astype(str).unique().tolist())
selected_action = st.selectbox("Filter by recommended action", action_options)

display_candidates = candidates.copy()
if selected_action != "All":
    display_candidates = display_candidates[display_candidates["Capacity_Action"] == selected_action]

candidate_cols = [
    "Unified_Shipment_ID",
    "Customer",
    "Cargo_Type",
    "Origin",
    "Destination",
    "Route",
    "Truck_Utilization_pct",
    "Warehouse_Utilization_pct",
    "Carbon_Emission_kgCO2_tonkm",
    "Total_Risk_Score",
    "ETA_Variance_Hours",
    "Capacity_Action",
    "Capacity_Priority_Score",
]

candidate_cols = [col for col in candidate_cols if col in display_candidates.columns]

if display_candidates.empty:
    st.warning("No capacity optimization candidate is available under the current filter.")
else:
    show_blue_table(display_candidates[candidate_cols].head(80), max_height=430)
    dataframe_download(
        display_candidates[candidate_cols],
        "Download capacity optimization watchlist",
        "capacity_optimization_watchlist.csv",
    )

section("Decision logic")

st.markdown(
    f"""
    - If **Truck Utilization < {truck_threshold}%**, the Control Tower reviews the order for shipment consolidation by route, temperature requirement and delivery deadline.
    - If **Warehouse Utilization > 90%**, the Control Tower recommends warehouse flow rebalancing, cross-dock acceleration or temporary diversion to another node.
    - If carbon intensity is above **{carbon_baseline:.2f} kg CO2/ton-km**, the Control Tower reviews lower-emission multimodal alternatives.
    - If ETA delay or risk score increases, the Control Tower flags the order for dynamic routing and customer notification.
    """
)
