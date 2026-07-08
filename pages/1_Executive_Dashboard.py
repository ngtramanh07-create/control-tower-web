import streamlit as st
import plotly.express as px
import pandas as pd
from utils.ui import inject_css, title, section
from utils.data_loader import load_orders
from utils.kpi_utils import (
    calculate_kpis,
    kpi_comparison_frame,
    kpi_delta_text,
    KPI_UNITS,
    LOWER_IS_BETTER,
    display_kpi_name,
)

st.set_page_config(page_title="Executive Dashboard", page_icon="KPI", layout="wide")
inject_css()

title("Executive KPI Dashboard", "Before vs after Control Tower implementation for simulated export orders")

df = load_orders()
kpis = calculate_kpis(df)
comparison = kpi_comparison_frame(kpis)


def metric_display_value(kpi_name: str, value: float) -> str:
    unit = KPI_UNITS.get(kpi_name, "")
    return f"{value:.2f}{unit}" if kpi_name == "Carbon Emission" else f"{value:.1f}{unit}"


def render_metric(column, kpi_name: str):
    value = kpis[kpi_name]
    column.metric(
        display_kpi_name(kpi_name),
        metric_display_value(kpi_name, value),
        kpi_delta_text(kpi_name, value),
        delta_color="inverse" if kpi_name in LOWER_IS_BETTER else "normal",
    )

col1, col2, col3, col4 = st.columns(4)
for col, kpi_name in zip([col1, col2, col3, col4], ["OTIF", "Fill Rate", "Order Accuracy", "Carbon Emission"]):
    render_metric(col, kpi_name)

col5, col6, col7, col8 = st.columns(4)
for col, kpi_name in zip([col5, col6, col7, col8], ["Late Delivery Rate", "Cold Damage Rate", "Truck Utilization", "Warehouse Utilization"]):
    render_metric(col, kpi_name)

st.caption("For delay, cold damage and carbon intensity, lower is better. Warehouse Utilization is managed against a target range of around 80-85% to avoid congestion.")

section("Operational KPI comparison (%)")
percent_kpis = comparison[comparison["Unit"].eq("%")].copy()
percent_plot = percent_kpis.melt(
    id_vars=["KPI", "Unit"],
    value_vars=["Before Control Tower", "After Control Tower"],
    var_name="Period",
    value_name="Value",
)
fig = px.bar(percent_plot, x="KPI", y="Value", color="Period", barmode="group", text_auto=".1f")
fig.update_layout(height=430, xaxis_title="", yaxis_title="Percent (%)", legend_title="")
st.plotly_chart(fig, use_container_width=True)

section("Carbon intensity comparison")
carbon_row = comparison[comparison["KPI Key"].eq("Carbon Emission")].copy()
if not carbon_row.empty:
    carbon_plot = carbon_row.melt(
        id_vars=["KPI", "Unit"],
        value_vars=["Before Control Tower", "After Control Tower"],
        var_name="Period",
        value_name="Value",
    )
    fig = px.bar(carbon_plot, x="Period", y="Value", text_auto=".2f", title="Carbon emission intensity")
    fig.update_layout(height=330, xaxis_title="", yaxis_title="kg CO2/ton-km")
    st.plotly_chart(fig, use_container_width=True)

section("Improvement vs baseline")
improvement_rows = []
for _, row in comparison.iterrows():
    baseline = row["Before Control Tower"]
    current = row["After Control Tower"]
    if baseline == 0:
        continue
    if row["KPI Key"] in LOWER_IS_BETTER:
        improvement = (baseline - current) / baseline * 100
    else:
        improvement = (current - baseline) / baseline * 100
    improvement_rows.append({"KPI": row["KPI"], "Improvement vs baseline (%)": improvement})
if improvement_rows:
    improvement_df = pd.DataFrame(improvement_rows)
    fig = px.bar(improvement_df, x="KPI", y="Improvement vs baseline (%)", text_auto=".1f")
    fig.update_layout(height=360, xaxis_title="", yaxis_title="Improvement (%)")
    st.plotly_chart(fig, use_container_width=True)

section("Operational health")
left, right = st.columns(2)
with left:
    if "Shipment_Status" in df.columns:
        status = df["Shipment_Status"].value_counts().reset_index()
        status.columns = ["Shipment Status", "Orders"]
        fig = px.pie(status, names="Shipment Status", values="Orders", title="Shipment status distribution")
        st.plotly_chart(fig, use_container_width=True)
with right:
    if "Delay_Risk" in df.columns:
        risk = df["Delay_Risk"].value_counts().reset_index()
        risk.columns = ["Delay Risk", "Orders"]
        fig = px.bar(risk, x="Delay Risk", y="Orders", title="Delay risk distribution", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

section("KPI details")
st.dataframe(comparison, use_container_width=True)
