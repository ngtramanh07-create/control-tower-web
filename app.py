import streamlit as st
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

st.set_page_config(
    page_title="MFL Control Tower",
    page_icon="CT",
    layout="wide",
)
inject_css()

title(
    "MFL Multimodal Logistics Control Tower",
    "Web prototype for post-Control Tower export operations",
)

orders = load_orders()
kpis = calculate_kpis(orders)
comparison = kpi_comparison_frame(kpis)

st.markdown(
    """
    <div class='info-box'>
    This web prototype demonstrates how Mekong Fresh Logistics can move from fragmented operations to a centralized Control Tower.
    The simulated post-implementation orders are processed through the 8-layer architecture: physical logistics network,
    operational data sources, enterprise systems, integration platform, single source of truth, AI and analytics,
    decision orchestration, and experience layer.
    </div>
    """,
    unsafe_allow_html=True,
)

section("Post-Control Tower KPI snapshot")


def render_metric(column, kpi_name: str):
    unit = KPI_UNITS.get(kpi_name, "")
    value = kpis[kpi_name]
    display_value = f"{value:.2f}{unit}" if kpi_name == "Carbon Emission" else f"{value:.1f}{unit}"
    column.metric(
        display_kpi_name(kpi_name),
        display_value,
        f"{kpi_delta_text(kpi_name, value)} vs baseline",
        delta_color="inverse" if kpi_name in LOWER_IS_BETTER else "normal",
    )

col1, col2, col3, col4 = st.columns(4)
for col, kpi_name in zip([col1, col2, col3, col4], ["OTIF", "Fill Rate", "Order Accuracy", "Carbon Emission"]):
    render_metric(col, kpi_name)

col5, col6, col7, col8 = st.columns(4)
for col, kpi_name in zip([col5, col6, col7, col8], ["Late Delivery Rate", "Cold Damage Rate", "Truck Utilization", "Warehouse Utilization"]):
    render_metric(col, kpi_name)

st.caption("Warehouse Utilization is managed against a target range of around 80-85% to avoid congestion while still using capacity efficiently.")

section("How to use this web prototype")
st.markdown(
    """
    Use the pages in the left sidebar:

    - **Executive Dashboard**: before-after KPI comparison for management.
    - **Shipment Monitoring**: filter and inspect the post-Control Tower orders.
    - **Alert Center**: monitor delay, cold-chain, document, capacity and carbon exceptions.
    - **AI & Risk Scoring**: see risk scores and what-if simulation.
    - **Route & Capacity**: review utilization and optimization opportunities.
    - **ESG & Carbon**: review carbon footprint and ESG data completeness.
    - **Control Tower Architecture**: show the 8-layer model and operating logic.
    - **Add New Order**: input additional shipments and immediately recalculate KPI, alerts and recommended actions.
    """
)

section("Control Tower logic")
st.markdown(
    """
    **Sense**: collect GPS, IoT, WMS, TMS, document and customer data.  
    **Think**: predict ETA, score risk, analyze carbon and detect disruptions.  
    **Decide**: recommend route changes, capacity actions, document escalation and cold-chain response.  
    **Act**: assign workflow owners and notify customers.  
    **Learn**: use KPI results from active orders to improve future planning.
    """
)

with st.expander("Dataset overview"):
    st.write(f"Number of active orders: **{len(orders):,}**")
    st.write("Main dataset file: `data/SLC26C02_post_control_tower_500_orders_dataset.xlsx`")
    st.dataframe(orders.head(20), use_container_width=True)

with st.expander("KPI comparison table"):
    st.dataframe(comparison, use_container_width=True)
