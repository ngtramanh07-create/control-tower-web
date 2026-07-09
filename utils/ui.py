import streamlit as st
import pandas as pd


def inject_css():
    st.markdown(
        """
               .blue-table-wrap {
            border: 1px solid #D7E3F8;
            border-radius: 12px;
            overflow-x: auto;
            margin: 0.75rem 0 1.25rem 0;
            background: white;
        }

        .blue-table-wrap table {
            width: 100%;
            border-collapse: collapse;
            font-size: 0.92rem;
        }

        .blue-table-wrap thead tr {
            background: linear-gradient(90deg, #0B3D91, #2563EB);
        }

        .blue-table-wrap th {
            color: white !important;
            font-weight: 700;
            padding: 0.8rem 0.9rem;
            text-align: left;
            border: 1px solid #D7E3F8;
            white-space: nowrap;
        }

        .blue-table-wrap td {
            color: #0F172A;
            padding: 0.7rem 0.9rem;
            border: 1px solid #E5EAF3;
            vertical-align: top;
        }

        .blue-table-wrap tbody tr:nth-child(even) {
            background: #F8FBFF;
        }

        .blue-table-wrap tbody tr:hover {
            background: #EEF5FF;
        } <style>
        .block-container {padding-top: 3.2rem; padding-bottom: 2rem;}
        h1 {color: #0F2A5F; font-weight: 800; line-height: 1.15; margin-top: 0;}
        .subtitle {font-size: 1rem; color: #52616B; margin-top: -0.45rem; margin-bottom: 1.2rem;}
        .section-title {font-size: 1.3rem; font-weight: 750; color: #0B3D91; margin-top: 1rem;}
        .info-box {border-left: 5px solid #2563EB; background: #EFF6FF; padding: 1rem; border-radius: 0.5rem;}
        .warning-box {border-left: 5px solid #B7791F; background: #FFF8E5; padding: 1rem; border-radius: 0.5rem;}
        .danger-box {border-left: 5px solid #C53030; background: #FFF5F5; padding: 1rem; border-radius: 0.5rem;}
        div[data-testid="stMetricValue"] {font-size: 1.8rem;}
        div[data-testid="stMetricDelta"] {font-size: 0.9rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def title(text: str, subtitle: str = ""):
    """Render a Streamlit-native page title.

    Using st.title gives every page the standard Streamlit heading style and
    anchor icon, and the larger top padding prevents the title from being
    hidden by the app toolbar on different screen sizes.
    """
    st.title(text)
    if subtitle:
        st.markdown(f"<div class='subtitle'>{subtitle}</div>", unsafe_allow_html=True)


def section(text: str):
    st.markdown(f"<div class='section-title'>{text}</div>", unsafe_allow_html=True)


def dataframe_download(df: pd.DataFrame, label: str, file_name: str):
    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(label=label, data=csv, file_name=file_name, mime="text/csv")


def status_badge(status: str) -> str:
    status = str(status)
    color = "#718096"
    if status in {"Low", "On target", "Completed", "Stable", "Normal", "Delivered"}:
        color = "#2563EB"
    elif status in {"Medium", "Improved", "Warning", "Pending", "In Transit"}:
        color = "#B7791F"
    elif status in {"High", "Critical", "Issue", "Delayed"}:
        color = "#C53030"
    return f"<span style='background:{color};color:white;padding:0.18rem 0.45rem;border-radius:0.4rem;font-size:0.8rem;'>{status}</span>"


def safe_date_filter(df, column: str):
    if column not in df.columns or df[column].dropna().empty:
        return df
    min_date = df[column].min().date()
    max_date = df[column].max().date()
    selected = st.date_input(f"{column} range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    if isinstance(selected, tuple) and len(selected) == 2:                                                                            
    def blue_table(df, hide_index=True):
    html = df.to_html(index=not hide_index, escape=False)
    st.markdown(
        f"""
        <div class="blue-table-wrap">
            {html}
        </div>
        """,
        unsafe_allow_html=True,
    )
        start, end = selected
        return df[(df[column].dt.date >= start) & (df[column].dt.date <= end)]
    return df
