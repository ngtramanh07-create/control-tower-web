import streamlit as st
import plotly.express as px
from utils.ui import inject_css, title, section, dataframe_download
from utils.data_loader import load_orders

st.set_page_config(page_title="Alert Center", page_icon="ALERT", layout="wide")
inject_css()

title("Alert Center", "Exception management for delay, cold-chain, document, capacity and carbon risks")

df = load_orders()

alert_conditions = []
if "Delay_Risk" in df.columns:
    alert_conditions.append(df["Delay_Risk"].isin(["High", "Critical"]))
if "Temperature_Status" in df.columns:
    alert_conditions.append(df["Temperature_Status"].isin(["Warning", "Critical"]))
if "Document_Risk" in df.columns:
    # Medium means at least one required document is still pending. It should be visible as a watchlist item.
    alert_conditions.append(df["Document_Risk"].isin(["Medium", "High", "Critical", "Issue"]))
if "Capacity_Risk" in df.columns:
    alert_conditions.append(df["Capacity_Risk"].isin(["High", "Critical"]))
if "Carbon_Emission_kgCO2_tonkm" in df.columns:
    alert_conditions.append(df["Carbon_Emission_kgCO2_tonkm"] > 0.61)
if "Incident_Flag" in df.columns:
    alert_conditions.append(df["Incident_Flag"] == 1)

if alert_conditions:
    mask = alert_conditions[0]
    for condition in alert_conditions[1:]:
        mask = mask | condition
    alerts = df[mask].copy()
else:
    alerts = df.iloc[0:0].copy()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Active alerts", f"{len(alerts):,}")
col2.metric("High/Critical delay", f"{df['Delay_Risk'].isin(['High','Critical']).sum():,}" if "Delay_Risk" in df.columns else "N/A")
col3.metric("Cold-chain warning", f"{df['Temperature_Status'].isin(['Warning','Critical']).sum():,}" if "Temperature_Status" in df.columns else "N/A")
col4.metric("Document watchlist", f"{df['Document_Risk'].isin(['Medium','High','Critical','Issue']).sum():,}" if "Document_Risk" in df.columns else "N/A")

if "Document_Risk" in df.columns:
    medium_docs = df[df["Document_Risk"].eq("Medium")].copy()
    with st.expander("Document Watchlist: required documents still pending"):
        if medium_docs.empty:
            st.write("No pending required document in the active dataset.")
        else:
            cols = [
                "Unified_Shipment_ID", "Customer", "Cargo_Type", "Destination", "Transport_Mode",
                "Document_Risk", "Required_Delivery_Time", "Recommended_Action",
            ]
            cols = [c for c in cols if c in medium_docs.columns]
            st.dataframe(medium_docs[cols].head(80), use_container_width=True)

section("Alert distribution")
left, right = st.columns(2)
with left:
    if "Impact_Level" in alerts.columns and not alerts.empty:
        impact = alerts["Impact_Level"].value_counts().reset_index()
        impact.columns = ["Impact Level", "Orders"]
        fig = px.bar(impact, x="Impact Level", y="Orders", title="Alerts by impact level", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)
with right:
    if "Incident_Type" in alerts.columns and not alerts.empty:
        inc = alerts["Incident_Type"].value_counts().head(10).reset_index()
        inc.columns = ["Incident Type", "Orders"]
        fig = px.bar(inc, x="Orders", y="Incident Type", orientation="h", title="Top incident types", text_auto=True)
        st.plotly_chart(fig, use_container_width=True)

section("Exception management table")
cols = [
    "Unified_Shipment_ID", "Customer", "Cargo_Type", "Destination", "Incident_Time", "Incident_Type",
    "Impact_Level", "Affected_Process", "Delay_Risk", "Temperature_Status", "Document_Risk",
    "Total_Risk_Score", "Escalation_Owner", "Recommended_Action", "Customer_Notified",
]
cols = [c for c in cols if c in alerts.columns]
st.dataframe(alerts[cols], use_container_width=True, height=520)
dataframe_download(alerts[cols], "Download active alerts", "active_alerts.csv")

section("Sense - Think - Decide - Act - Learn logic")
st.markdown(
    """
    - **Sense:** alerts are created from GPS, temperature, document, capacity and carbon signals.  
    - **Think:** each alert is scored by severity and operational impact.  
    - **Decide:** the Control Tower recommends rerouting, document escalation, cold-chain recovery or capacity rebalancing.  
    - **Act:** owners are assigned and customers are notified when needed.  
    - **Learn:** recovery results are stored to improve future rules and KPI performance.
    """
)
