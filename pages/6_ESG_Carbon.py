import streamlit as st
import plotly.express as px
from utils.ui import inject_css, title, section, dataframe_download, blue_table
from utils.data_loader import load_orders

st.set_page_config(page_title="ESG & Carbon", page_icon="ESG", layout="wide")
inject_css()

title("ESG & Carbon Report", "Carbon footprint, traceability and ESG data completeness for 500 orders")

df = load_orders()


def required_completion_rate(df, column):
    if column not in df.columns:
        return None
    values = df[column].astype(str).str.strip().str.lower()
    required_values = values[~values.isin(["not required", "nan", "none", ""])]
    if required_values.empty:
        return None
    return (required_values == "completed").mean() * 100


avg_carbon = df["Carbon_Emission_kgCO2_tonkm"].mean() if "Carbon_Emission_kgCO2_tonkm" in df.columns else 0
baseline = 0.61
carbon_delta = avg_carbon - baseline
saving_pct = (baseline - avg_carbon) / baseline * 100 if baseline else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Avg carbon intensity", f"{avg_carbon:.2f}", f"{carbon_delta:+.2f} vs baseline", delta_color="inverse")
col2.metric("Carbon reduction", f"{saving_pct:.1f}%")
esg_rate = required_completion_rate(df, "ESG_Report_Status")
trace_rate = required_completion_rate(df, "Traceability_Status")
col3.metric("ESG report completed", f"{esg_rate:.1f}%" if esg_rate is not None else "N/A")
col4.metric("Traceability completed", f"{trace_rate:.1f}%" if trace_rate is not None else "N/A")

left, right = st.columns(2)
with left:
    if {"Transport_Mode", "Carbon_Emission_kgCO2_tonkm"}.issubset(df.columns):
        mode = df.groupby("Transport_Mode", as_index=False)["Carbon_Emission_kgCO2_tonkm"].mean()
        fig = px.bar(mode, x="Transport_Mode", y="Carbon_Emission_kgCO2_tonkm", title="Carbon intensity by transport mode", text_auto=".2f")
        st.plotly_chart(fig, use_container_width=True)
with right:
    if {"Destination", "Carbon_Emission_Total_kgCO2e"}.issubset(df.columns):
        dest = df.groupby("Destination", as_index=False)["Carbon_Emission_Total_kgCO2e"].sum().sort_values("Carbon_Emission_Total_kgCO2e", ascending=False).head(10)
        fig = px.bar(dest, x="Destination", y="Carbon_Emission_Total_kgCO2e", title="Total carbon by destination", text_auto=".0f")
        st.plotly_chart(fig, use_container_width=True)

section("ESG and traceability completeness")
completeness_rows = []
doc_columns = [
    "Invoice_Status",
    "Packing_List_Status",
    "Customs_Status",
    "CO_Status",
    "AWB_BL_Status",
    "Phytosanitary_Status",
    "Health_Certificate_Status",
    "Fumigation_Certificate_Status",
    "Temperature_Log_Status",
    "Sensor_Report_Status",
    "VGM_Status",
    "Insurance_Certificate_Status",
    "MSDS_Status",
    "Export_License_Status",
    "Electronics_Quality_Dossier_Status",
    "ESG_Report_Status",
    "Traceability_Status",
    "Other_Document_Status",
]
for col in doc_columns:
    completed = required_completion_rate(df, col)
    if completed is not None:
        completeness_rows.append({"Data Field": col, "Completion Rate": completed})
if completeness_rows:
    import pandas as pd
    comp = pd.DataFrame(completeness_rows)
    fig = px.bar(comp, x="Data Field", y="Completion Rate", title="Data completeness rate", text_auto=".1f")
    st.plotly_chart(fig, use_container_width=True)
    blue_table(comp.round(2))

section("High-carbon shipment watchlist")
watch = df[df["Carbon_Emission_kgCO2_tonkm"] > 0.61].copy() if "Carbon_Emission_kgCO2_tonkm" in df.columns else df.iloc[0:0].copy()
cols = [
    "Unified_Shipment_ID", "Customer", "Cargo_Type", "Destination", "Transport_Mode", "Route",
    "Carbon_Emission_kgCO2_tonkm", "Carbon_Emission_Total_kgCO2e", "Recommended_Action",
]
cols = [c for c in cols if c in watch.columns]
blue_table(watch[cols].head(100))
dataframe_download(watch[cols], "Download high-carbon watchlist", "high_carbon_watchlist.csv")
