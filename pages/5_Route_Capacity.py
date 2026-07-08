import streamlit as st
import plotly.express as px
from utils.ui import inject_css, title, section, dataframe_download
from utils.data_loader import load_orders

st.set_page_config(page_title="Route & Capacity", page_icon="ROUTE", layout="wide")
inject_css()

title("Route & Capacity Optimization", "Dynamic routing, consolidation and asset utilization after Control Tower")

df = load_orders()

col1, col2, col3 = st.columns(3)
col1.metric("Avg truck utilization", f"{df['Truck_Utilization_pct'].mean():.1f}%" if "Truck_Utilization_pct" in df.columns else "N/A")
col2.metric("Avg warehouse load level", f"{df['Warehouse_Utilization_pct'].mean():.1f}%" if "Warehouse_Utilization_pct" in df.columns else "N/A")
col3.metric("Consolidation candidates", f"{(df['Truck_Utilization_pct'] < 75).sum():,}" if "Truck_Utilization_pct" in df.columns else "N/A")
st.caption("Warehouse load level is treated as a pressure KPI. Target range: approximately 80-85% to avoid congestion while maintaining capacity efficiency.")

left, right = st.columns(2)
with left:
    if {"Route", "Truck_Utilization_pct"}.issubset(df.columns):
        route_util = df.groupby("Route", as_index=False)["Truck_Utilization_pct"].mean().sort_values("Truck_Utilization_pct", ascending=False)
        fig = px.bar(route_util, x="Route", y="Truck_Utilization_pct", title="Average truck utilization by route", text_auto=".1f")
        st.plotly_chart(fig, use_container_width=True)
with right:
    if {"Origin", "Warehouse_Utilization_pct"}.issubset(df.columns):
        wh = df.groupby("Origin", as_index=False)["Warehouse_Utilization_pct"].mean().sort_values("Warehouse_Utilization_pct", ascending=False)
        fig = px.bar(wh, x="Origin", y="Warehouse_Utilization_pct", title="Average warehouse load level by origin", text_auto=".1f")
        st.plotly_chart(fig, use_container_width=True)

section("Route performance")
if {"Route", "Carbon_Emission_kgCO2_tonkm", "Total_Risk_Score"}.issubset(df.columns):
    perf = df.groupby("Route", as_index=False).agg(
        Orders=("Unified_Shipment_ID", "count"),
        Avg_Carbon=("Carbon_Emission_kgCO2_tonkm", "mean"),
        Avg_Risk=("Total_Risk_Score", "mean"),
        Avg_Truck_Util=("Truck_Utilization_pct", "mean"),
    )
    st.dataframe(perf.round(2), use_container_width=True)

section("Consolidation and rebalancing candidates")
candidates = df.copy()
if "Truck_Utilization_pct" in candidates.columns:
    candidates = candidates[candidates["Truck_Utilization_pct"] < 75]
cols = [
    "Unified_Shipment_ID", "Customer", "Cargo_Type", "Origin", "Destination", "Route",
    "Truck_Utilization_pct", "Warehouse_Utilization_pct", "Capacity_Risk", "Recommended_Action",
]
cols = [c for c in cols if c in candidates.columns]
st.dataframe(candidates[cols].head(80), use_container_width=True, height=430)
dataframe_download(candidates[cols], "Download consolidation candidates", "consolidation_candidates.csv")

section("Decision logic")
st.markdown(
    """
    - If truck utilization is below 75%, the Control Tower recommends shipment consolidation by route and deadline.  
    - If warehouse utilization exceeds 85%, the Control Tower recommends cross-dock acceleration or inventory rebalancing.  
    - If route carbon exceeds the baseline, the Control Tower suggests a lower-emission multimodal option.  
    - If ETA risk becomes high, the Control Tower triggers dynamic routing and customer notification.
    """
)
