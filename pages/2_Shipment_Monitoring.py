import streamlit as st
import plotly.express as px
from utils.ui import inject_css, title, section, dataframe_download, blue_table
from utils.data_loader import load_orders, filter_orders, safe_unique

st.set_page_config(page_title="Shipment Monitoring", page_icon="SHIP", layout="wide")
inject_css()

title("Shipment Monitoring", "Filter and monitor 500 post-Control Tower orders")

df = load_orders()

with st.sidebar:
    st.header("Filters")
    customers = st.multiselect("Customer", safe_unique(df, "Customer"))
    cargo_types = st.multiselect("Cargo type", safe_unique(df, "Cargo_Type"))
    destinations = st.multiselect("Destination", safe_unique(df, "Destination"))
    modes = st.multiselect("Transport mode", safe_unique(df, "Transport_Mode"))
    delay_risks = st.multiselect("Delay risk", safe_unique(df, "Delay_Risk"))
    temp_status = st.multiselect("Temperature status", safe_unique(df, "Temperature_Status"))
    doc_risks = st.multiselect("Document risk", safe_unique(df, "Document_Risk"))
    shipment_status = st.multiselect("Shipment status", safe_unique(df, "Shipment_Status"))

filtered = filter_orders(df, customers, cargo_types, destinations, modes, delay_risks, temp_status, doc_risks, shipment_status)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Filtered orders", f"{len(filtered):,}")
col2.metric("Total weight", f"{filtered.get('Weight_Ton', 0).sum():,.1f} tons" if "Weight_Ton" in filtered else "N/A")
col3.metric("Average risk score", f"{filtered.get('Total_Risk_Score', 0).mean():.1f}" if "Total_Risk_Score" in filtered else "N/A")
col4.metric("Average carbon", f"{filtered.get('Carbon_Emission_kgCO2_tonkm', 0).mean():.2f}" if "Carbon_Emission_kgCO2_tonkm" in filtered else "N/A")

section("Tracking table")
columns = [
    "Unified_Shipment_ID", "Customer", "Cargo_Type", "Weight_Ton", "Origin", "Destination",
    "Transport_Mode", "Route", "Planned_ETA", "Predicted_ETA", "ETA_Variance_Hours",
    "Delay_Risk", "Temperature_Status", "Document_Risk", "Shipment_Status", "Recommended_Action",
]
columns = [c for c in columns if c in filtered.columns]
blue_table(filtered[columns], max_height=520)
dataframe_download(filtered[columns], "Download filtered shipments", "filtered_shipments.csv")

section("Shipment distribution")
left, right = st.columns(2)
with left:
    if "Destination" in filtered.columns and not filtered.empty:
        dest = filtered["Destination"].value_counts().head(12).reset_index()
        dest.columns = ["Destination", "Orders"]
        fig = px.bar(dest, x="Destination", y="Orders", title="Top destinations", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
with right:
    if "Transport_Mode" in filtered.columns and not filtered.empty:
        mode = filtered["Transport_Mode"].value_counts().reset_index()
        mode.columns = ["Transport Mode", "Orders"]
        fig = px.pie(mode, names="Transport Mode", values="Orders", title="Orders by transport mode")
        st.plotly_chart(fig, use_container_width=True)
