import pandas as pd

RISK_MAP = {
    "Low": 20,
    "Medium": 50,
    "High": 75,
    "Critical": 95,
    "Normal": 10,
    "Stable": 10,
    "Warning": 65,
    "Issue": 85,
}


def risk_value(value) -> int:
    if pd.isna(value):
        return 0
    text = str(value).strip()
    return RISK_MAP.get(text, 0)


def calculate_risk_score(row) -> float:
    delay = risk_value(row.get("Delay_Risk"))
    temp = risk_value(row.get("Temperature_Risk", row.get("Temperature_Status")))
    doc = risk_value(row.get("Document_Risk"))
    route = risk_value(row.get("Route_Risk"))
    capacity = risk_value(row.get("Capacity_Risk"))
    score = delay * 0.30 + temp * 0.25 + doc * 0.20 + route * 0.15 + capacity * 0.10
    return round(score, 1)


def severity_from_score(score: float) -> str:
    if score >= 81:
        return "Critical"
    if score >= 61:
        return "High"
    if score >= 31:
        return "Medium"
    return "Low"


def _text(*values) -> str:
    return " ".join(str(v) for v in values if not pd.isna(v)).lower()


def recommend_action(row) -> str:
    context = _text(
        row.get("Incident_Type", ""),
        row.get("Affected_Process", ""),
        row.get("Route", ""),
        row.get("Destination", ""),
        row.get("Cargo_Type", ""),
    )
    incident = str(row.get("Incident_Type", "")).strip()
    impact = str(row.get("Impact_Level", "")).strip()

    if "cat lai" in context or ("port" in context and "congestion" in context):
        return "Switch non-gated cargo to Cai Mep or ICD route, update vessel cut-off, prioritize truck dispatch, and notify customers with revised ETA."

    if "reefer" in context or "temperature" in context or "cold chain" in context or "abnormal temperature" in context:
        return "Activate 12-hour cold-chain recovery: inspect reefer unit, verify sensor, prepare substitute container, and move cargo to nearest cold storage if stabilization fails."

    if "fuel" in context or "diesel" in context:
        return "Review fuel surcharge, consolidate same-route loads, reduce empty miles, and shift non-urgent shipments to lower-cost multimodal routes."

    if "flight cancellation" in context or ("tokyo" in context and ("air" in context or "flight" in context or "airport" in context)):
        return "Rebook cargo via alternative air route, maintain airport cold storage, revise AWB/e-AWB and update Tokyo customer ETA."

    if "wms" in context or "system downtime" in context or "system" in context or "it system" in context:
        return "Switch to offline inventory protocol, freeze stock movement records, reconcile WMS after recovery and flag inventory mismatch risk."

    if "esg" in context or "carbon" in context or "traceability" in context:
        return "Generate shipment-level carbon report, verify traceability dossier, and assign ESG analyst for customer compliance response."

    if incident not in {"", "None", "nan"} and impact in {"High", "Critical"}:
        return "Escalate incident to Control Tower owner, assess SLA impact, assign recovery workflow, and notify customer if ETA or quality is affected."

    if str(row.get("Delay_Risk", "")).strip() in {"High", "Critical"}:
        return "Check alternative route, activate rerouting plan, and update customer ETA."

    if str(row.get("Temperature_Status", "")).strip() in {"Warning", "Critical"}:
        return "Inspect reefer unit, verify sensor, and move cargo to nearest cold storage if needed."

    if str(row.get("Document_Risk", "")).strip() in {"Medium"}:
        return "Track pending required documents against cut-off time and assign Documentation Officer to close missing items."

    if str(row.get("Document_Risk", "")).strip() in {"High", "Critical", "Issue"}:
        return "Escalate to Documentation Officer before cut-off and verify export documents."

    if pd.notna(row.get("Truck_Utilization_pct")) and float(row.get("Truck_Utilization_pct")) < 75:
        return "Consolidate with same-route shipments to improve truck utilization."

    if pd.notna(row.get("Warehouse_Utilization_pct")) and float(row.get("Warehouse_Utilization_pct")) > 85:
        return "Rebalance inventory or accelerate outbound plan to reduce warehouse pressure."

    if pd.notna(row.get("Carbon_Emission_kgCO2_tonkm")) and float(row.get("Carbon_Emission_kgCO2_tonkm")) > 0.61:
        return "Recommend lower-emission route or multimodal option."

    return "Continue monitoring through Control Tower."


def ensure_decision_columns(df):
    df = df.copy()
    if "Total_Risk_Score" not in df.columns or df["Total_Risk_Score"].isna().all():
        df["Total_Risk_Score"] = df.apply(calculate_risk_score, axis=1)
    if "Recommended_Action" not in df.columns or df["Recommended_Action"].isna().all():
        df["Recommended_Action"] = df.apply(recommend_action, axis=1)
    if "Severity" not in df.columns:
        df["Severity"] = df["Total_Risk_Score"].apply(severity_from_score)
    return df
