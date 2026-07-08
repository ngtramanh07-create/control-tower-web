# MFL Multimodal Logistics Control Tower Web Prototype

This folder contains a Streamlit web dashboard prototype for the Smart Logistics Challenge 2026 case.

The application uses a simulated post-Control Tower dataset of 500 export orders. It demonstrates how Mekong Fresh Logistics can process orders through a Control Tower architecture, monitor KPI improvement after implementation, input new shipments, detect exceptions and recommend recovery actions.

## Main functions

- Executive KPI dashboard: before vs after Control Tower KPI comparison
- Shipment monitoring: tracking table with filters
- Alert center: delay, cold-chain, document, capacity and carbon alerts
- AI and risk scoring: risk distribution, top-risk orders and what-if simulation
- Route and capacity optimization: truck utilization, warehouse load level and consolidation candidates
- ESG and carbon report: carbon intensity, ESG completeness and high-carbon routes
- Control Tower architecture: 8-layer model and Sense-Think-Decide-Act-Learn loop
- Add New Order: conditional documents, cargo-based temperature suggestion, mode-based carbon factor and incident recommendation

## Important fixes in this version

- Late Delivery Rate, Cold Damage Rate and Carbon Emission now treat reduction as positive improvement.
- KPI charts no longer mix percentage KPIs and carbon intensity on one axis.
- Home page KPI deltas are recalculated dynamically from the active dataset instead of being hard-coded.
- Warehouse Utilization is kept as the KPI name and interpreted against a target range of around 80-85% to reduce congestion pressure while keeping efficient capacity use.
- Document checklist is conditional by cargo type, transport mode, destination and customer/legal requirements.
- Phytosanitary is not required for electronics by default.
- Fumigation is only required when wooden packaging/fumigation is selected.
- MSDS / battery declaration is only required when battery, chemical or dangerous goods content is selected.
- Export license / permit is only required when controlled cargo is selected.
- Transport document label adapts to the selected mode: AWB/e-AWB, B/L/Sea Waybill, multimodal transport document or truck waybill.
- Temperature defaults adapt to cargo: frozen, fresh, chilled, electronics or pharma cold-chain cargo.
- Carbon factor defaults adapt to mode: Road-Sea, Road-ICD-Sea, Sea-Air, Road-Air or Road only.
- Alert Center includes pending required documents as a Document Watchlist item.
- Recommended actions now include specific recovery logic for port congestion, reefer malfunction, fuel price surge, flight cancellation to Tokyo, WMS downtime and ESG/carbon/traceability requests.

## How to run locally

1. Install Python 3.10 or newer.
2. Open Terminal or Command Prompt in this folder.
3. Run:

```bash
pip install -r requirements.txt
streamlit run app.py
```

On Windows, you can also double-click `run_local.bat`.

## Dataset

The file is located at:

```text
data/SLC26C02_post_control_tower_500_orders_dataset.xlsx
```

Main sheet:

```text
Post_CT_500_Orders
```

## Suggested deployment

Use Streamlit Community Cloud:

1. Upload this folder to a GitHub repository.
2. Go to Streamlit Community Cloud.
3. Connect the repository.
4. Select `app.py` as the main file.
5. Deploy and share the generated web link.

## New order input feature

The page **Add New Order** allows users to enter a new shipment directly in the web interface. After submission, the app appends the order to the active Streamlit session dataset and recalculates KPI, risk score, alert logic and recommended action.

Notes:
- New orders are stored in the current browser/session, not permanently written to the original Excel file.
- Use **Download active dataset as Excel** on the Add New Order page to save the updated dataset.
- Use **Reset to original 500 orders** to return to the original post-Control Tower dataset.
- If a certificate is marked **Not required**, it is excluded from document risk and data completeness scoring.

## Flexible incident input update

The Add New Order page supports a broader incident list and `Other / custom input` for incident type and affected process. This allows users to enter unexpected logistics exceptions such as abnormal temperature rise, reefer malfunction, IT downtime, supplier delay, weather disruption, or any custom operational issue.
