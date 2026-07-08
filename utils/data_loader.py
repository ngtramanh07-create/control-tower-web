from pathlib import Path
from functools import lru_cache
import pandas as pd
import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT_DIR / "data" / "SLC26C02_post_control_tower_500_orders_dataset.xlsx"
ORDER_SHEET = "Post_CT_500_Orders"
SESSION_KEY = "control_tower_orders_df"


@lru_cache(maxsize=1)
def load_base_orders() -> pd.DataFrame:
    """Load the original 500 post-Control Tower orders from Excel."""
    df = pd.read_excel(DATA_PATH, sheet_name=ORDER_SHEET)
    return prepare_orders(df)


def load_orders() -> pd.DataFrame:
    """Load orders from session state so newly entered orders stay active across pages."""
    if SESSION_KEY not in st.session_state:
        st.session_state[SESSION_KEY] = load_base_orders().copy()
    return prepare_orders(st.session_state[SESSION_KEY].copy())


@lru_cache(maxsize=16)
def load_sheet(sheet_name: str) -> pd.DataFrame:
    return pd.read_excel(DATA_PATH, sheet_name=sheet_name)


def append_order(order_row: dict) -> pd.DataFrame:
    """Append a new order to the active Streamlit session dataset."""
    current = load_orders().copy()
    new_row = pd.DataFrame([order_row])
    combined = pd.concat([current, new_row], ignore_index=True)
    st.session_state[SESSION_KEY] = prepare_orders(combined)
    return st.session_state[SESSION_KEY]


def reset_orders() -> None:
    """Reset active orders back to the original Excel dataset."""
    st.session_state[SESSION_KEY] = load_base_orders().copy()


def get_added_order_count() -> int:
    """Return how many orders have been added in the current session."""
    if SESSION_KEY not in st.session_state:
        return 0
    return max(0, len(st.session_state[SESSION_KEY]) - len(load_base_orders()))


def prepare_orders(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    date_cols = [
        "Required_Delivery_Time",
        "Planned_ETA",
        "Predicted_ETA",
        "Last_Update_Time",
        "Incident_Time",
    ]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    numeric_cols = [
        "Weight_Ton",
        "ETA_Variance_Hours",
        "Recovery_Time_Hours",
        "Truck_Utilization_pct",
        "Warehouse_Utilization_pct",
        "Carbon_Emission_kgCO2_tonkm",
        "Carbon_Emission_Total_kgCO2e",
        "Distance_km",
        "Emission_Factor",
        "Total_Risk_Score",
        "Required_Temperature_C",
        "Actual_Temperature_C",
        "Fill_Rate_Value",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    flag_cols = [
        "On_Time_Flag",
        "In_Full_Flag",
        "OTIF_Flag",
        "Order_Accuracy_Flag",
        "Late_Delivery_Flag",
        "Cold_Damage_Flag",
        "Incident_Flag",
        "Customer_Notified",
    ]
    for col in flag_cols:
        if col in df.columns:
            df[col] = df[col].map(_to_flag).astype("float")

    if "Display_ID" not in df.columns:
        if "Unified_Shipment_ID" in df.columns:
            df["Display_ID"] = df["Unified_Shipment_ID"].astype(str)
        elif "Order_ID" in df.columns:
            df["Display_ID"] = df["Order_ID"].astype(str)
        else:
            df["Display_ID"] = [f"ORDER-{i:04d}" for i in range(1, len(df) + 1)]

    return df


def _to_flag(value):
    if pd.isna(value):
        return 0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"yes", "y", "true", "delivered", "completed", "on time", "1"}:
            return 1
        if normalized in {"no", "n", "false", "late", "pending", "issue", "0"}:
            return 0
    try:
        return 1 if float(value) >= 1 else 0
    except Exception:
        return 0


def filter_orders(
    df: pd.DataFrame,
    customers=None,
    cargo_types=None,
    destinations=None,
    modes=None,
    delay_risks=None,
    temp_status=None,
    doc_risks=None,
    shipment_status=None,
):
    filtered = df.copy()
    filters = [
        ("Customer", customers),
        ("Cargo_Type", cargo_types),
        ("Destination", destinations),
        ("Transport_Mode", modes),
        ("Delay_Risk", delay_risks),
        ("Temperature_Status", temp_status),
        ("Document_Risk", doc_risks),
        ("Shipment_Status", shipment_status),
    ]
    for col, values in filters:
        if values and col in filtered.columns:
            filtered = filtered[filtered[col].isin(values)]
    return filtered


def safe_unique(df: pd.DataFrame, column: str):
    if column not in df.columns:
        return []
    values = df[column].dropna().astype(str).sort_values().unique().tolist()
    return values
