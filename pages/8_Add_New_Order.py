import io
from datetime import datetime, time, timedelta

import pandas as pd
import streamlit as st

from utils.ui import inject_css, title, section, dataframe_download, blue_table
from utils.data_loader import load_orders, append_order, reset_orders, get_added_order_count
from utils.kpi_utils import calculate_kpis, kpi_comparison_frame
from utils.rules import calculate_risk_score, severity_from_score, recommend_action



def select_or_custom(label, options, default_index=0, key_prefix=None):
    """Select from common values or type a custom value for new cargo, destination or incident cases."""
    key_prefix = key_prefix or label.lower().replace(" ", "_")
    extended = list(options)
    if "Other / custom input" not in extended:
        extended.append("Other / custom input")
    choice = st.selectbox(label, extended, index=default_index, key=f"{key_prefix}_select")
    if choice == "Other / custom input":
        custom = st.text_input(f"Type custom {label.lower()}", key=f"{key_prefix}_custom")
        return custom.strip() if custom.strip() else f"Custom {label}"
    return choice


CARGO_OPTIONS = [
    "Frozen durian",
    "Fresh mango",
    "Fresh fruit",
    "Fresh dragon fruit",
    "Fresh longan",
    "Fresh rambutan",
    "Fresh lychee",
    "Fresh coconut",
    "Fresh banana",
    "Fresh avocado",
    "Chilled vegetables",
    "Frozen seafood",
    "Frozen shrimp",
    "Frozen pangasius fillet",
    "Frozen squid",
    "Frozen passion fruit puree",
    "Frozen vegetables",
    "Processed fruit",
    "Electronic components",
    "High-value electronics",
    "Mixed cold-chain cargo",
    "Pharmaceutical cold-chain cargo",
]

ORIGIN_OPTIONS = [
    "Tien Giang Cold Storage",
    "Long An Cold Storage",
    "Binh Duong Consolidation Hub",
    "Dong Thap Collection Point",
    "Can Tho Coordination Center",
    "Vinh Long Collection Point",
    "Ben Tre Collection Point",
    "An Giang Collection Point",
    "HCMC Export Hub",
    "Mekong Supplier Site",
]

DESTINATION_OPTIONS = [
    "Shanghai, China",
    "Shenzhen, China",
    "Guangzhou, China",
    "Hong Kong, China",
    "Tokyo, Japan",
    "Osaka, Japan",
    "Nagoya, Japan",
    "Yokohama, Japan",
    "Fukuoka, Japan",
    "Incheon, South Korea",
    "Busan, South Korea",
    "Seoul, South Korea",
    "Rotterdam, Netherlands",
    "Amsterdam, Netherlands",
    "Frankfurt, Germany",
    "Hamburg, Germany",
    "Munich, Germany",
    "Paris, France",
    "Lyon, France",
    "Milan, Italy",
    "Madrid, Spain",
    "Singapore",
    "Bangkok, Thailand",
    "Kuala Lumpur, Malaysia",
    "Sydney, Australia",
    "Melbourne, Australia",
]

INCIDENT_OPTIONS = [
    "None",
    "Road congestion",
    "Traffic accident",
    "Late document confirmation",
    "Customs clearance delay",
    "Container shortage",
    "Reefer malfunction",
    "Temperature excursion",
    "Abnormal temperature rise",
    "Sensor offline",
    "GPS signal lost",
    "Port cut-off change",
    "Port congestion",
    "Airport cargo delay",
    "Carrier booking change",
    "Vessel schedule change",
    "Flight cancellation",
    "Warehouse congestion",
    "Labor shortage",
    "Fuel price surge",
    "Driver unavailable",
    "Truck breakdown",
    "Seal issue",
    "Packaging damage",
    "Customer change request",
    "Supplier delay",
    "Weather disruption",
    "Power outage",
    "System downtime",
    "Cybersecurity alert",
    "Other operational exception",
    "Other / custom input",
]


DOCUMENT_STATUS_OPTIONS = ["Completed", "Pending", "Issue", "Not required"]

PLANT_ORIGIN_KEYWORDS = [
    "fruit", "mango", "durian", "dragon fruit", "longan", "rambutan", "lychee",
    "coconut", "banana", "avocado", "vegetable", "passion fruit",
]
SEAFOOD_KEYWORDS = ["seafood", "shrimp", "pangasius", "squid", "fish"]
ELECTRONICS_KEYWORDS = ["electronic", "electronics", "component"]
PHARMA_KEYWORDS = ["pharmaceutical", "pharma", "medicine", "vaccine"]
EU_MARKET_KEYWORDS = [
    "netherlands", "germany", "france", "italy", "spain", "rotterdam", "amsterdam",
    "frankfurt", "hamburg", "munich", "paris", "lyon", "milan", "madrid",
]


def contains_any(text, keywords):
    text = str(text).lower()
    return any(keyword in text for keyword in keywords)


DEFAULT_EMISSION_FACTOR = {
    "Road-Sea": 0.080,
    "Road-ICD-Sea": 0.060,
    "Sea-Air": 0.250,
    "Road-Air": 0.600,
    "Road only": 0.120,
}


def default_temperature(cargo_type):
    cargo = str(cargo_type).lower()
    if "frozen" in cargo:
        return -18.0, -17.5, "Online"
    if "fresh mango" in cargo or "fresh" in cargo:
        return 10.0, 10.5, "Online"
    if "chilled" in cargo:
        return 4.0, 4.5, "Online"
    if contains_any(cargo, ELECTRONICS_KEYWORDS):
        return 22.0, 22.0, "Not required"
    if contains_any(cargo, PHARMA_KEYWORDS):
        return 2.0, 2.5, "Online"
    return 15.0, 15.0, "Online"


def transport_document_label(transport_mode):
    mode = str(transport_mode).lower()
    if "air" in mode and "sea" in mode:
        return "B/L + AWB / multimodal transport document"
    if "air" in mode:
        return "Air Waybill / e-AWB"
    if "sea" in mode or "icd" in mode:
        return "Bill of Lading / Sea Waybill"
    return "Truck waybill / delivery note"


def document_requirements(
    cargo_type,
    transport_mode,
    destination,
    sla_level,
    co_required=False,
    wooden_packaging=False,
    dg_or_battery=False,
    controlled_cargo=False,
):
    """Return required/not-required logic for the compact document checklist.

    Core export documents are kept for every shipment. Conditional certificates are
    suggested based on cargo, transport mode, destination market and customer/legal
    requirements. Not-required documents are excluded from document risk.
    """
    cargo = str(cargo_type).lower()
    mode = str(transport_mode).lower()
    dest = str(destination).lower()
    sla = str(sla_level).lower()

    is_plant_origin = contains_any(cargo, PLANT_ORIGIN_KEYWORDS)
    is_seafood = contains_any(cargo, SEAFOOD_KEYWORDS)
    is_electronics = contains_any(cargo, ELECTRONICS_KEYWORDS)
    is_pharma = contains_any(cargo, PHARMA_KEYWORDS)
    is_food = is_plant_origin or is_seafood or "food" in cargo or "cold-chain" in cargo
    is_cold_chain = is_food or is_pharma or any(word in cargo for word in ["fresh", "frozen", "chilled"])
    is_eu = contains_any(dest, EU_MARKET_KEYWORDS)
    is_sea_mode = "sea" in mode or "icd" in mode
    is_air_mode = "air" in mode
    is_high_value = "high value" in sla or "high-value" in cargo or "high value" in cargo

    return {
        "Invoice_Status": True,
        "Packing_List_Status": True,
        "AWB_BL_Status": True,
        "Customs_Status": True,
        "CO_Status": co_required,
        "Phytosanitary_Status": is_plant_origin,
        "Health_Certificate_Status": is_seafood or is_pharma,
        "Fumigation_Certificate_Status": wooden_packaging,
        "Temperature_Log_Status": is_cold_chain,
        "Sensor_Report_Status": is_cold_chain,
        "VGM_Status": is_sea_mode,
        "Insurance_Certificate_Status": is_high_value or is_air_mode,
        "MSDS_Status": dg_or_battery,
        "Export_License_Status": controlled_cargo,
        "ESG_Report_Status": is_eu,
        "Traceability_Status": is_food or is_eu,
        "Electronics_Quality_Dossier_Status": is_electronics,
    }


def required_status_selectbox(label, required, key):
    default_index = 0 if required else DOCUMENT_STATUS_OPTIONS.index("Not required")
    suffix = "required" if required else "not required for this order"
    state_key = f"{key}_{'required' if required else 'not_required'}"
    return st.selectbox(
        label,
        DOCUMENT_STATUS_OPTIONS,
        index=default_index,
        key=state_key,
        help=f"Auto suggestion: {suffix}. You can still change it manually if the customer or authority requires it.",
    )


def document_risk_from_statuses(statuses):
    relevant = [str(status) for status in statuses if str(status).strip().lower() != "not required"]
    if not relevant:
        return "Low"
    if "Issue" in relevant:
        return "Critical"
    if "Pending" in relevant:
        return "Medium"
    return "Low"

st.set_page_config(page_title="Add New Order", page_icon="ADD", layout="wide")
inject_css()

title("Add New Order", "Input a new shipment and let the Control Tower recalculate KPI, risk and actions")

orders = load_orders()
kpis_before = calculate_kpis(orders)

st.markdown(
    """
    <div class='info-box'>
    This page simulates the <b>Act + Learn</b> part of the Control Tower. When a new order is added,
    the web app appends it to the active 500-order dataset, recalculates KPI, updates alert logic,
    and shows the recommended operational response. Cargo type, origin and destination now support both
    common options and custom input for new markets or new product categories.
    </div>
    """,
    unsafe_allow_html=True,
)

col_a, col_b, col_c = st.columns(3)
col_a.metric("Active orders", f"{len(orders):,}")
col_b.metric("Orders added this session", f"{get_added_order_count():,}")
col_c.metric("Current OTIF", f"{kpis_before['OTIF']:.1f}%")

section("New order form")

with st.form("new_order_form", clear_on_submit=False):
    tab1, tab2, tab3, tab4 = st.tabs(["Order", "Tracking", "Cold chain & docs", "Capacity, carbon & incident"])

    with tab1:
        c1, c2, c3 = st.columns(3)
        with c1:
            customer = st.text_input("Customer", value="New Export Customer")
            customer_type = st.selectbox("Customer type", ["Retail Distributor", "Wholesale Market", "Food Service", "Manufacturer", "Importer"])
            cargo_type = select_or_custom("Cargo type", CARGO_OPTIONS, default_index=0, key_prefix="cargo_type")
        with c2:
            weight = st.number_input("Weight (tons)", min_value=0.1, max_value=100.0, value=18.0, step=0.1)
            origin = select_or_custom("Origin", ORIGIN_OPTIONS, default_index=0, key_prefix="origin")
            destination = select_or_custom("Destination", DESTINATION_OPTIONS, default_index=0, key_prefix="destination")
        with c3:
            sla_level = st.selectbox("SLA level", ["Standard", "Premium", "Cold Chain Critical", "High Value"])
            transport_mode = st.selectbox("Transport mode", ["Road-Sea", "Road-Air", "Sea-Air", "Road-ICD-Sea", "Road only"])
            route = st.text_input("Route", value="Origin Warehouse -> Main Hub -> Destination")

    with tab2:
        c1, c2, c3 = st.columns(3)
        with c1:
            deadline_date = st.date_input("Deadline date", value=datetime.now().date() + timedelta(days=3))
            deadline_time = st.time_input("Deadline time", value=time(18, 0))
            planned_date = st.date_input("Planned ETA date", value=datetime.now().date() + timedelta(days=3))
            planned_time = st.time_input("Planned ETA time", value=time(14, 0))
        with c2:
            predicted_date = st.date_input("Predicted ETA date", value=datetime.now().date() + timedelta(days=3))
            predicted_time = st.time_input("Predicted ETA time", value=time(15, 0))
            current_location = st.text_input("Current location", value="In transit")
            physical_node = st.selectbox("Physical node", ["Warehouse", "Reefer Truck", "Port", "Airport", "Airline", "Shipping Line", "Customer Site"])
        with c3:
            shipment_status = st.selectbox("Shipment status", ["On track", "In transit", "Delivered", "Delayed", "At risk"])
            gps_status = st.selectbox("GPS status", ["Normal", "Stopped", "Delayed", "Offline"])
            last_update = st.date_input("Last update date", value=datetime.now().date())
            last_update_time = st.time_input("Last update time", value=datetime.now().time().replace(second=0, microsecond=0))

    with tab3:
        default_required_temp, default_actual_temp, default_reefer_status = default_temperature(cargo_type)
        default_reefer_index = ["Online", "Warning", "Offline", "Not required"].index(default_reefer_status)
        transport_doc = transport_document_label(transport_mode)
        temp_context_key = "".join(ch if ch.isalnum() else "_" for ch in str(cargo_type).lower())[:50]

        st.caption(
            "Document checklist is conditional: core export documents stay visible, while certificates are suggested by cargo, transport mode, destination and customer/legal requirements."
        )
        c0a, c0b, c0c, c0d = st.columns(4)
        with c0a:
            co_required = st.checkbox("Customer requires C/O / FTA proof", value=True)
        with c0b:
            wooden_packaging = st.checkbox("Wooden packaging / fumigation requested", value=False)
        with c0c:
            dg_or_battery = st.checkbox("Battery, chemical or DG content", value=False)
        with c0d:
            controlled_cargo = st.checkbox("Controlled cargo / export permit needed", value=False)

        doc_required = document_requirements(
            cargo_type,
            transport_mode,
            destination,
            sla_level,
            co_required=co_required,
            wooden_packaging=wooden_packaging,
            dg_or_battery=dg_or_battery,
            controlled_cargo=controlled_cargo,
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            required_temp = st.number_input(
                "Required temperature (C)",
                min_value=-25.0,
                max_value=25.0,
                value=default_required_temp,
                step=0.5,
                help="Auto-suggested by cargo type. Frozen cargo is typically below 0C, fresh fruit is chilled, and electronics do not need reefer temperature control.",
                key=f"required_temp_{temp_context_key}",
            )
            actual_temp = st.number_input(
                "Actual temperature (C)",
                min_value=-30.0,
                max_value=35.0,
                value=default_actual_temp,
                step=0.5,
                key=f"actual_temp_{temp_context_key}",
            )
            reefer_status = st.selectbox(
                "Reefer status",
                ["Online", "Warning", "Offline", "Not required"],
                index=default_reefer_index,
                key=f"reefer_status_{temp_context_key}",
            )
            temperature_log_status = required_status_selectbox("Temperature log", doc_required["Temperature_Log_Status"], "temperature_log_status")
            sensor_report_status = required_status_selectbox("IoT sensor report", doc_required["Sensor_Report_Status"], "sensor_report_status")
        with c2:
            invoice_status = required_status_selectbox("Commercial invoice", doc_required["Invoice_Status"], "invoice_status")
            packing_status = required_status_selectbox("Packing list", doc_required["Packing_List_Status"], "packing_status")
            co_status = required_status_selectbox("C/O", doc_required["CO_Status"], "co_status")
            customs_status = required_status_selectbox("Customs declaration", doc_required["Customs_Status"], "customs_status")
            awb_status = required_status_selectbox(transport_doc, doc_required["AWB_BL_Status"], "awb_status")
            vgm_status = required_status_selectbox("VGM", doc_required["VGM_Status"], "vgm_status")
        with c3:
            phyto_status = required_status_selectbox("Phytosanitary certificate", doc_required["Phytosanitary_Status"], "phyto_status")
            health_status = required_status_selectbox("Health/Veterinary certificate", doc_required["Health_Certificate_Status"], "health_status")
            fumigation_status = required_status_selectbox("Fumigation certificate", doc_required["Fumigation_Certificate_Status"], "fumigation_status")
            insurance_status = required_status_selectbox("Insurance certificate", doc_required["Insurance_Certificate_Status"], "insurance_status")
            msds_status = required_status_selectbox("MSDS / battery declaration", doc_required["MSDS_Status"], "msds_status")
            export_license_status = required_status_selectbox("Export license / permit", doc_required["Export_License_Status"], "export_license_status")
            electronics_quality_status = required_status_selectbox("Electronics quality dossier / inspection report", doc_required["Electronics_Quality_Dossier_Status"], "electronics_quality_status")
            esg_status = required_status_selectbox("ESG / carbon report", doc_required["ESG_Report_Status"], "esg_status")
            trace_status = required_status_selectbox("Traceability dossier", doc_required["Traceability_Status"], "trace_status")
            other_doc_status = st.selectbox("Other document", DOCUMENT_STATUS_OPTIONS, index=DOCUMENT_STATUS_OPTIONS.index("Not required"))
            other_doc_name = st.text_input("Other document name", value="")

    with tab4:
        c1, c2, c3 = st.columns(3)
        with c1:
            in_full = st.checkbox("Delivered in full", value=True)
            order_accuracy = st.checkbox("Order accuracy OK", value=True)
            truck_util = st.number_input("Truck utilization (%)", min_value=0.0, max_value=100.0, value=87.0, step=0.5)
            warehouse_util = st.number_input("Warehouse utilization (%)", min_value=0.0, max_value=100.0, value=84.0, step=0.5)
        with c2:
            distance = st.number_input("Distance (km)", min_value=1.0, max_value=20000.0, value=1200.0, step=10.0)
            default_emission_factor = DEFAULT_EMISSION_FACTOR.get(transport_mode, 0.120)
            emission_key = "".join(ch if ch.isalnum() else "_" for ch in str(transport_mode).lower())
            emission_factor = st.number_input(
                "Carbon factor (kg CO2/ton-km)",
                min_value=0.001,
                max_value=1.5,
                value=default_emission_factor,
                step=0.001,
                format="%.3f",
                help="Auto-suggested by transport mode. Air is higher, sea or ICD-sea is lower; users can manually override for a specific carrier or route.",
                key=f"emission_factor_{emission_key}",
            )
            route_risk_manual = st.selectbox("Route risk", ["Low", "Medium", "High", "Critical"])
            capacity_risk_manual = st.selectbox("Capacity risk", ["Low", "Medium", "High", "Critical"])
        with c3:
            st.caption(
                "Select an incident type directly. In a Streamlit form, a checkbox cannot dynamically unlock hidden fields until the form is submitted, so this version keeps the incident fields active."
            )
            incident_type = select_or_custom(
                "Incident type",
                INCIDENT_OPTIONS,
                default_index=0,
                key_prefix="incident_type",
            )
            incident_flag = str(incident_type).strip().lower() != "none"
            affected_process = select_or_custom(
                "Affected process",
                [
                    "None",
                    "Shipment execution",
                    "Cold chain",
                    "Documentation",
                    "Customs clearance",
                    "Warehouse operation",
                    "Transport capacity",
                    "Carrier coordination",
                    "Customer communication",
                    "ESG / carbon reporting",
                    "IT system",
                ],
                default_index=0 if not incident_flag else 1,
                key_prefix="affected_process",
            )
            impact_level = st.selectbox("Impact level", ["Low", "Medium", "High", "Critical"])
            escalation_owner = st.selectbox("Escalation owner", ["Control Tower", "Transport Planner", "Cold Chain Coordinator", "Documentation Officer", "ESG Analyst", "Customer Service", "IT Support", "Warehouse Supervisor"])

    submitted = st.form_submit_button("Add order and recalculate KPI", type="primary")

if submitted:
    required_dt = datetime.combine(deadline_date, deadline_time)
    planned_dt = datetime.combine(planned_date, planned_time)
    predicted_dt = datetime.combine(predicted_date, predicted_time)
    last_update_dt = datetime.combine(last_update, last_update_time)

    eta_variance = round((predicted_dt - required_dt).total_seconds() / 3600, 1)
    if eta_variance > 12:
        delay_risk = "Critical"
    elif eta_variance > 6:
        delay_risk = "High"
    elif eta_variance > 0:
        delay_risk = "Medium"
    else:
        delay_risk = "Low"

    temp_diff = abs(actual_temp - required_temp)
    if reefer_status == "Not required":
        temp_status = "Stable"
    elif temp_diff > 5 or reefer_status == "Offline":
        temp_status = "Critical"
    elif temp_diff > 2 or reefer_status == "Warning":
        temp_status = "Warning"
    else:
        temp_status = "Stable"

    doc_values = [
        invoice_status,
        packing_status,
        co_status,
        phyto_status,
        awb_status,
        customs_status,
        esg_status,
        trace_status,
        temperature_log_status,
        sensor_report_status,
        health_status,
        fumigation_status,
        vgm_status,
        insurance_status,
        msds_status,
        export_license_status,
        electronics_quality_status,
        other_doc_status,
    ]
    document_risk = document_risk_from_statuses(doc_values)

    on_time = 1 if predicted_dt <= required_dt else 0
    in_full_flag = 1 if in_full else 0
    accuracy_flag = 1 if order_accuracy else 0
    late_flag = 1 - on_time
    cold_damage = 1 if temp_status == "Critical" else 0
    otif_flag = 1 if on_time and in_full_flag else 0
    incident_num = 1 if incident_flag else 0
    fill_rate_value = 100 if in_full else 0
    carbon_total = round(weight * distance * emission_factor, 1)

    next_number = len(orders) + 1
    row = {
        "Unified_Shipment_ID": f"USID-CT-2026-{next_number:05d}",
        "Order_ID": f"PCT-O-{next_number:05d}",
        "Customer": customer,
        "Customer_Type": customer_type,
        "Cargo_Type": cargo_type,
        "Weight_Ton": weight,
        "Origin": origin,
        "Destination": destination,
        "Required_Delivery_Time": required_dt,
        "SLA_Level": sla_level,
        "Transport_Mode": transport_mode,
        "Transport_Document_Type": transport_doc,
        "Route": route,
        "Physical_Node": physical_node,
        "Current_Location": current_location,
        "Planned_ETA": planned_dt,
        "Predicted_ETA": predicted_dt,
        "ETA_Variance_Hours": eta_variance,
        "Delay_Risk": delay_risk,
        "Shipment_Status": shipment_status,
        "GPS_Status": gps_status,
        "Last_Update_Time": last_update_dt,
        "Required_Temperature_C": required_temp,
        "Actual_Temperature_C": actual_temp,
        "Temperature_Status": temp_status,
        "Reefer_Status": reefer_status,
        "Cold_Damage_Flag": cold_damage,
        "Invoice_Status": invoice_status,
        "Packing_List_Status": packing_status,
        "CO_Status": co_status,
        "Phytosanitary_Status": phyto_status,
        "AWB_BL_Status": awb_status,
        "Customs_Status": customs_status,
        "ESG_Report_Status": esg_status,
        "Traceability_Status": trace_status,
        "Temperature_Log_Status": temperature_log_status,
        "Sensor_Report_Status": sensor_report_status,
        "Health_Certificate_Status": health_status,
        "Fumigation_Certificate_Status": fumigation_status,
        "VGM_Status": vgm_status,
        "Insurance_Certificate_Status": insurance_status,
        "MSDS_Status": msds_status,
        "Export_License_Status": export_license_status,
        "Electronics_Quality_Dossier_Status": electronics_quality_status,
        "CO_Required_Flag": 1 if co_required else 0,
        "Wooden_Packaging_or_Fumigation_Flag": 1 if wooden_packaging else 0,
        "DG_or_Battery_Flag": 1 if dg_or_battery else 0,
        "Controlled_Cargo_Flag": 1 if controlled_cargo else 0,
        "Other_Document_Name": other_doc_name.strip(),
        "Other_Document_Status": other_doc_status,
        "Document_Risk": document_risk,
        "Incident_Flag": incident_num,
        "Incident_Time": last_update_dt if incident_flag else pd.NaT,
        "Incident_Type": incident_type if incident_flag else "None",
        "Impact_Level": impact_level if incident_flag else "Low",
        "Affected_Process": affected_process if incident_flag else "None",
        "Response_Action": "Control Tower review and execute recommended action" if incident_flag else "Continue monitoring",
        "Recovery_Time_Hours": 4 if incident_flag else 0,
        "Escalation_Owner": escalation_owner,
        "On_Time_Flag": on_time,
        "In_Full_Flag": in_full_flag,
        "OTIF_Flag": otif_flag,
        "Order_Accuracy_Flag": accuracy_flag,
        "Late_Delivery_Flag": late_flag,
        "Fill_Rate_Value": fill_rate_value,
        "Truck_Utilization_pct": truck_util,
        "Warehouse_Utilization_pct": warehouse_util,
        "Carbon_Emission_kgCO2_tonkm": emission_factor,
        "Carbon_Emission_Total_kgCO2e": carbon_total,
        "Distance_km": distance,
        "Emission_Factor": emission_factor,
        "Route_Risk": route_risk_manual,
        "Capacity_Risk": capacity_risk_manual,
        "Temperature_Risk": temp_status if temp_status in ["Warning", "Critical"] else "Low",
        "CT_Loop_Status": "Sense-Think-Decide-Act-Learn",
        "Data_Source_Connected": "Manual input/WMS/TMS/GPS/IoT/Documents/Carbon",
        "Unified_Data_Status": "Synced",
        "Customer_Notified": 1 if delay_risk in ["High", "Critical"] or incident_flag else 0,
    }
    row["Total_Risk_Score"] = calculate_risk_score(row)
    row["Severity"] = severity_from_score(row["Total_Risk_Score"])
    row["Recommended_Action"] = recommend_action(row)

    updated = append_order(row)
    kpis_after = calculate_kpis(updated)

    st.success(f"Added {row['Order_ID']} successfully. KPI and alert pages will now use {len(updated):,} active orders.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("New OTIF", f"{kpis_after['OTIF']:.1f}%", f"{kpis_after['OTIF'] - kpis_before['OTIF']:+.2f}%")
    c2.metric("New Fill Rate", f"{kpis_after['Fill Rate']:.1f}%", f"{kpis_after['Fill Rate'] - kpis_before['Fill Rate']:+.2f}%")
    c3.metric("New Late Rate", f"{kpis_after['Late Delivery Rate']:.1f}%", f"{kpis_after['Late Delivery Rate'] - kpis_before['Late Delivery Rate']:+.2f}%", delta_color="inverse")
    c4.metric("New Carbon", f"{kpis_after['Carbon Emission']:.2f}", f"{kpis_after['Carbon Emission'] - kpis_before['Carbon Emission']:+.3f}", delta_color="inverse")

    section("New order decision output")
    blue_table(pd.DataFrame([row]), max_height=240)

section("Active dataset after new inputs")
active = load_orders()
st.caption("The added orders are stored in the current Streamlit session. Use Download if you want to save the updated dataset.")
blue_table(active.tail(20), max_height=340)

left, mid, right = st.columns(3)
with left:
    if st.button("Reset to original 500 orders"):
        reset_orders()
        st.success("Dataset reset to the original 500 orders. Refresh or switch pages to see the reset values.")
with mid:
    dataframe_download(active, "Download active dataset as CSV", "active_control_tower_orders.csv")
with right:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        active.to_excel(writer, index=False, sheet_name="Active_Orders")
        kpi_comparison_frame(calculate_kpis(active)).to_excel(writer, index=False, sheet_name="KPI_Check")
    st.download_button(
        label="Download active dataset as Excel",
        data=output.getvalue(),
        file_name="active_control_tower_orders.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

section("KPI after all active orders")
blue_table(kpi_comparison_frame(calculate_kpis(active)), max_height=360)
