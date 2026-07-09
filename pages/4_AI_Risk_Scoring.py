import streamlit as st
import plotly.express as px
from utils.ui import inject_css, title, section, blue_table
from utils.data_loader import load_orders
from utils.rules import severity_from_score

st.set_page_config(page_title="AI & Risk Scoring", page_icon="AI", layout="wide")
inject_css()

title("AI & Risk Scoring", "Predictive ETA, risk scoring and what-if simulation")

df = load_orders()

section("Risk scoring logic")
st.markdown(
    """
    Simulated risk score formula:  
    **Risk Score = 30% Delay Risk + 25% Temperature Risk + 20% Document Risk + 15% Route Risk + 10% Capacity Risk**
    """
)

col1, col2, col3 = st.columns(3)
col1.metric("Average risk score", f"{df['Total_Risk_Score'].mean():.1f}" if "Total_Risk_Score" in df.columns else "N/A")
col2.metric("High risk orders", f"{(df['Total_Risk_Score'] >= 61).sum():,}" if "Total_Risk_Score" in df.columns else "N/A")
col3.metric("Critical risk orders", f"{(df['Total_Risk_Score'] >= 81).sum():,}" if "Total_Risk_Score" in df.columns else "N/A")

left, right = st.columns(2)
with left:
    if "Total_Risk_Score" in df.columns:
        fig = px.histogram(df, x="Total_Risk_Score", nbins=20, title="Risk score distribution")
        st.plotly_chart(fig, use_container_width=True)
with right:
    if "ETA_Variance_Hours" in df.columns and "Total_Risk_Score" in df.columns:
        fig = px.scatter(
            df,
            x="ETA_Variance_Hours",
            y="Total_Risk_Score",
            color="Delay_Risk" if "Delay_Risk" in df.columns else None,
            hover_data=["Unified_Shipment_ID", "Customer", "Destination"] if "Unified_Shipment_ID" in df.columns else None,
            title="ETA variance vs risk score",
        )
        st.plotly_chart(fig, use_container_width=True)

section("Top risk orders")
cols = [
    "Unified_Shipment_ID", "Customer", "Cargo_Type", "Destination", "ETA_Variance_Hours",
    "Delay_Risk", "Temperature_Risk", "Document_Risk", "Route_Risk", "Capacity_Risk",
    "Total_Risk_Score", "Recommended_Action",
]
cols = [c for c in cols if c in df.columns]
blue_table(df.sort_values("Total_Risk_Score", ascending=False)[cols].head(30), max_height=430)

section("What-if risk simulation")
st.caption("Use this simple simulation to explain how the Control Tower converts operational signals into a decision priority.")
col_a, col_b, col_c, col_d, col_e = st.columns(5)
with col_a:
    delay = st.slider("Delay risk", 0, 100, 50)
with col_b:
    temperature = st.slider("Temperature risk", 0, 100, 40)
with col_c:
    document = st.slider("Document risk", 0, 100, 35)
with col_d:
    route = st.slider("Route risk", 0, 100, 30)
with col_e:
    capacity = st.slider("Capacity risk", 0, 100, 25)
score = delay * 0.30 + temperature * 0.25 + document * 0.20 + route * 0.15 + capacity * 0.10
severity = severity_from_score(score)
st.metric("Simulated total risk score", f"{score:.1f}", severity)
