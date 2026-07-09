import pandas as pd

BASELINE_KPIS = {
    "OTIF": 94.0,
    "Fill Rate": 96.0,
    "Order Accuracy": 98.5,
    "Warehouse Utilization": 88.0,
    "Truck Utilization": 81.0,
    "Carbon Emission": 0.61,
    "Late Delivery Rate": 6.0,
    "Cold Damage Rate": 1.8,
}

TARGET_KPIS = {
    "OTIF": 97.0,
    "Fill Rate": 97.0,
    "Order Accuracy": 99.2,
    "Warehouse Utilization": 84.0,
    "Truck Utilization": 87.0,
    "Carbon Emission": 0.54,
    "Late Delivery Rate": 3.0,
    "Cold Damage Rate": 1.2,
}

KPI_UNITS = {
    "OTIF": "%",
    "Fill Rate": "%",
    "Order Accuracy": "%",
    "Warehouse Utilization": "%",
    "Truck Utilization": "%",
    "Carbon Emission": " kg CO2/ton-km",
    "Late Delivery Rate": "%",
    "Cold Damage Rate": "%",
}

KPI_DISPLAY_NAMES = {}

LOWER_IS_BETTER = {"Carbon Emission", "Late Delivery Rate", "Cold Damage Rate", "Warehouse Utilization"}


def display_kpi_name(kpi_name: str) -> str:
    return KPI_DISPLAY_NAMES.get(kpi_name, kpi_name)


def pct_mean(series: pd.Series) -> float:
    series = pd.to_numeric(series, errors="coerce").dropna()
    if series.empty:
        return 0.0
    value = series.mean()
    if value <= 1.0:
        value *= 100
    return float(value)


def calculate_kpis(df: pd.DataFrame) -> dict:
    kpis = {}

    if "OTIF_Flag" in df.columns:
        kpis["OTIF"] = pct_mean(df["OTIF_Flag"])
    elif {"On_Time_Flag", "In_Full_Flag"}.issubset(df.columns):
        kpis["OTIF"] = pct_mean(df["On_Time_Flag"] * df["In_Full_Flag"])
    else:
        kpis["OTIF"] = TARGET_KPIS["OTIF"]

    if "In_Full_Flag" in df.columns:
        kpis["Fill Rate"] = pct_mean(df["In_Full_Flag"])
    elif "Fill_Rate_Value" in df.columns:
        kpis["Fill Rate"] = pct_mean(df["Fill_Rate_Value"])
    else:
        kpis["Fill Rate"] = TARGET_KPIS["Fill Rate"]

    if "Order_Accuracy_Flag" in df.columns:
        kpis["Order Accuracy"] = pct_mean(df["Order_Accuracy_Flag"])
    else:
        kpis["Order Accuracy"] = TARGET_KPIS["Order Accuracy"]

    if "Warehouse_Utilization_pct" in df.columns:
        kpis["Warehouse Utilization"] = pct_mean(df["Warehouse_Utilization_pct"])
    else:
        kpis["Warehouse Utilization"] = TARGET_KPIS["Warehouse Utilization"]

    if "Truck_Utilization_pct" in df.columns:
        kpis["Truck Utilization"] = pct_mean(df["Truck_Utilization_pct"])
    else:
        kpis["Truck Utilization"] = TARGET_KPIS["Truck Utilization"]

    if "Carbon_Emission_kgCO2_tonkm" in df.columns:
        kpis["Carbon Emission"] = float(pd.to_numeric(df["Carbon_Emission_kgCO2_tonkm"], errors="coerce").mean())
    else:
        kpis["Carbon Emission"] = TARGET_KPIS["Carbon Emission"]

    if "Late_Delivery_Flag" in df.columns:
        kpis["Late Delivery Rate"] = pct_mean(df["Late_Delivery_Flag"])
    elif "On_Time_Flag" in df.columns:
        kpis["Late Delivery Rate"] = 100 - pct_mean(df["On_Time_Flag"])
    else:
        kpis["Late Delivery Rate"] = TARGET_KPIS["Late Delivery Rate"]

    if "Cold_Damage_Flag" in df.columns:
        kpis["Cold Damage Rate"] = pct_mean(df["Cold_Damage_Flag"])
    else:
        kpis["Cold Damage Rate"] = TARGET_KPIS["Cold Damage Rate"]

    return {key: round(value, 2) for key, value in kpis.items()}


def kpi_delta_text(kpi_name: str, current_value: float) -> str:
    baseline = BASELINE_KPIS[kpi_name]
    diff = current_value - baseline
    sign = "+" if diff >= 0 else ""
    suffix = KPI_UNITS.get(kpi_name, "")
    if kpi_name == "Carbon Emission":
        return f"{sign}{diff:.2f}{suffix}"
    return f"{sign}{diff:.1f}{suffix}"


def kpi_status(kpi_name: str, current_value: float) -> str:
    target = TARGET_KPIS[kpi_name]
    if kpi_name in LOWER_IS_BETTER:
        if current_value <= target:
            return "On target"
        if current_value <= BASELINE_KPIS[kpi_name]:
            return "Improved"
        return "Needs attention"
    if current_value >= target:
        return "On target"
    if current_value >= BASELINE_KPIS[kpi_name]:
        return "Improved"
    return "Needs attention"


def kpi_comparison_frame(current_kpis: dict) -> pd.DataFrame:
    rows = []
    for kpi, baseline in BASELINE_KPIS.items():
        current = current_kpis.get(kpi, TARGET_KPIS[kpi])
        rows.append(
            {
                "KPI Key": kpi,
                "KPI": display_kpi_name(kpi),
                "Before Control Tower": baseline,
                "After Control Tower": current,
                "Target": TARGET_KPIS[kpi],
                "Unit": KPI_UNITS.get(kpi, ""),
                "Direction": "Lower is better" if kpi in LOWER_IS_BETTER else "Higher is better",
                "Status": kpi_status(kpi, current),
            }
        )
    return pd.DataFrame(rows)
