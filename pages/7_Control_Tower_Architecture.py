import streamlit as st
from utils.ui import inject_css, page_header, blue_table
from utils.data_loader import load_sheet

st.set_page_config(page_title="Control Tower Architecture", page_icon="ARCH", layout="wide")
inject_css()

title("Control Tower Architecture", "8-layer design and Sense-Think-Decide-Act-Learn operating model")

st.markdown(
    """
    <div class='info-box'>
    The Control Tower is not only a KPI dashboard. It is an integrated operating model that connects physical logistics,
    real-time data sources, enterprise systems, data integration, single source of truth, AI analytics, decision orchestration,
    and user-facing dashboards or portals.
    </div>
    """,
    unsafe_allow_html=True,
)

section("8-layer model")
try:
    layers = load_sheet("Control_Tower_Layers")
    blue_table(layer_df)
except Exception:
    st.warning("Control_Tower_Layers sheet is not available.")

section("Architecture flow")
st.code(
    """
CUSTOMERS / SUPPLIERS / PARTNERS
        |
        v
EXPERIENCE & VISUALIZATION LAYER
Executive Dashboard | Customer Portal | Mobile App | Alert Center | ESG Reports
        ^
        |
DECISION & ORCHESTRATION LAYER
Decision Support | Exception Management | Dynamic Routing | Automated Notification
        ^
        |
AI & ANALYTICS LAYER
Predictive ETA | Risk Scoring | Carbon Analytics | Root Cause Analysis | What-if Simulation
        ^
        |
SINGLE SOURCE OF TRUTH
Operational Data Hub | Master Data | Digital Twin | Data Lake | Real-time Database
        ^
        |
INTEGRATION PLATFORM
API Gateway | EDI | Webhook | MQTT | ETL/ELT | Event Streaming | Security
        ^
        |
ENTERPRISE SYSTEMS
ERP | WMS | TMS | OMS | CRM | Finance | Fleet Management | Customs
        ^
        |
OPERATIONAL DATA SOURCES
GPS | IoT Sensors | RFID | Barcode | Reefer Temperature | Driver App
        ^
        |
PHYSICAL LOGISTICS NETWORK
Warehouses | Trucks | Reefer Trucks | Ports | Airports | Shipping Lines | Airlines
    """
)

section("Sense - Think - Decide - Act - Learn")
st.markdown(
    """
    - **Sense:** collect GPS, IoT, WMS, TMS, weather, document and customer data.  
    - **Think:** predict ETA, predict disruption, score risk and run carbon analytics.  
    - **Decide:** recommend routing, capacity allocation, inventory actions and recovery plans.  
    - **Act:** trigger workflow, assign owners, call APIs and notify customers.  
    - **Learn:** compare KPI results and feed lessons back into planning rules and AI models.
    """
)

section("Decision rules")
try:
    rules = load_sheet("Decision_Rules")
    st.dataframe(rules, use_container_width=True, height=360)
except Exception:
    st.warning("Decision_Rules sheet is not available.")
