from __future__ import annotations

import io
import os
import sys

sys.path.append(os.path.dirname(__file__))
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

from model import ProjectInputs, run_project
from sensitivity import one_way_sensitivity


st.set_page_config(page_title="baetz energy Mieterstrom Business-Case", layout="wide")

st.title("baetz energy – Mieterstrom Wirtschaftlichkeits-App")
st.caption("Planungsrechnung fuer Mieterstrom (Dachpacht als OPEX) mit Hebel-Sensitivitaeten.")

with st.sidebar:
    st.header("Projektparameter")

    st.subheader("Invest")
    pv_capex = st.number_input("PV CAPEX (EUR)", min_value=0.0, value=1_400_000.0, step=10_000.0)
    meter_capex = st.number_input("Einmalkosten Zaehlerertuechtigung (EUR)", min_value=0.0, value=80_000.0, step=1_000.0)
    loan_amount = st.number_input("Kreditbetrag (EUR)", min_value=0.0, value=1_400_000.0, step=10_000.0)

    st.subheader("Ertrag & Teilnehmer")
    pv_yield = st.number_input("PV-Ertrag (kWh/a)", min_value=0.0, value=989_010.0, step=1_000.0)
    customers_100 = st.number_input("Kunden bei 100% Quote", min_value=0, value=386, step=1)
    participation = st.slider("Teilnehmerquote", min_value=0.0, max_value=1.0, value=1.0, step=0.01)

    st.subheader("Erlos")
    baseline_revenue = st.number_input("Erlos PV-Stromverkauf an Mieter (EUR/a)", min_value=0.0, value=255_319.0, step=1_000.0)

    st.subheader("OPEX")
    software = st.number_input("Softwarelizenz (EUR/a)", min_value=0.0, value=16_212.0, step=500.0)
    roof_lease = st.number_input("Dachpacht (EUR/a)", min_value=0.0, value=0.0, step=500.0)
    other_opex = st.number_input("Sonstige OPEX (EUR/a)", min_value=0.0, value=0.0, step=500.0)
    o_and_m_pct = st.number_input("O&M in % von PV-CAPEX", min_value=0.0, value=1.2, step=0.1) / 100.0

    st.subheader("Hebel")
    delta_ct = st.number_input("Preishebel: Delta ct/kWh", value=0.0, step=0.1)
    base_fee = st.number_input("Grundpreis je Kunde/Monat (EUR)", min_value=0.0, value=0.0, step=0.5)

    st.subheader("Export")
    export_share = st.slider("Exportanteil am PV-Ertrag", min_value=0.0, max_value=1.0, value=0.0, step=0.01)
    export_price = st.number_input("Exportpreis (ct/kWh)", min_value=0.0, value=8.0, step=0.5)

    st.subheader("Finanzierung")
    loan_interest = st.number_input("Zins (p.a., %)", min_value=0.0, value=4.0, step=0.1) / 100.0
    term = st.number_input("Laufzeit (Jahre)", min_value=1, value=20, step=1)
    grace = st.number_input("Tilgungsfreie Jahre", min_value=0, value=0, step=1)

    st.subheader("Bewertung")
    discount = st.number_input("Diskontsatz (NPV, %)", min_value=0.0, value=8.0, step=0.5) / 100.0
    horizon = st.number_input("Analysehorizont (Jahre)", min_value=5, value=25, step=1)

p = ProjectInputs(
    pv_capex_eur=pv_capex,
    meter_upgrade_capex_eur=meter_capex,
    loan_amount_eur=loan_amount,
    pv_yield_kwh_a=pv_yield,
    customers_100pct=int(customers_100),
    participation_rate=float(participation),
    baseline_sales_revenue_eur_a=baseline_revenue,
    software_lic_eur_a=software,
    roof_lease_eur_a=roof_lease,
    other_opex_eur_a=other_opex,
    o_and_m_pct_of_pv_capex=float(o_and_m_pct),
    delta_ct_per_kwh=float(delta_ct),
    base_fee_eur_per_customer_month=float(base_fee),
    export_share_of_yield=float(export_share),
    export_price_ct_per_kwh=float(export_price),
    loan_interest=float(loan_interest),
    loan_term_years=int(term),
    grace_years=int(grace),
    discount_rate=float(discount),
    analysis_years=int(horizon),
)

df, m = run_project(p)

col1, col2, col3, col4 = st.columns(4)
col1.metric("CAPEX gesamt", f"{m['capex_total_eur']:,.0f} EUR")
col2.metric("Eigenkapital", f"{m['equity_eur']:,.0f} EUR")
col3.metric("Preis (ct/kWh)", f"{m['price_ct_per_kwh']:.2f}")
col4.metric("EBITDA (a)", f"{m['annual_ebitda_eur']:,.0f} EUR")

col5, col6, col7, col8 = st.columns(4)
irr_val = m.get("irr_equity")
col5.metric("IRR (Equity)", "n/a" if irr_val is None else f"{irr_val*100:.2f}%")
col6.metric("NPV (Equity)", f"{m['npv_equity_eur']:,.0f} EUR")
col7.metric("DSCR min", "n/a" if m.get("dscr_min") is None else f"{m['dscr_min']:.2f}")
col8.metric("Kunden aktiv", str(m["customers"]))

st.divider()

left, right = st.columns([1.2, 1])

with left:
    st.subheader("Cashflow-Tabelle")
    show_cols = [
        "year",
        "revenue_eur",
        "opex_eur",
        "ebitda_eur",
        "debt_payment_eur",
        "free_cashflow_to_equity_eur",
    ]
    st.dataframe(df[show_cols], use_container_width=True, height=420)

    csv = df.to_csv(index=False).encode("utf-8")
    st.download_button("Cashflow als CSV herunterladen", data=csv, file_name="cashflow.csv", mime="text/csv")

with right:
    st.subheader("Cashflow-Visualisierung")

    fig1 = plt.figure()
    plt.plot(df["year"], df["free_cashflow_to_equity_eur"])
    plt.xlabel("Jahr")
    plt.ylabel("Free Cashflow to Equity (EUR)")
    st.pyplot(fig1)

    cum = df["free_cashflow_to_equity_eur"].cumsum()
    fig2 = plt.figure()
    plt.plot(df["year"], cum)
    plt.xlabel("Jahr")
    plt.ylabel("Kumulierter Equity-Cashflow (EUR)")
    st.pyplot(fig2)

st.divider()

st.subheader("Hebel: One-way Sensitivitaet (konfigurierbar)")

with st.expander("Sensitivitaetsbereich einstellen"):
    c1, c2, c3 = st.columns(3)
    with c1:
        s_price = st.slider("Delta ct/kWh (low..high)", min_value=-10.0, max_value=10.0, value=(-2.0, 2.0), step=0.1)
        s_basefee = st.slider("Grundpreis EUR/Kunde/Monat (low..high)", min_value=0.0, max_value=15.0, value=(0.0, 5.0), step=0.5)
    with c2:
        s_interest = st.slider("Zins % (low..high)", min_value=0.0, max_value=10.0, value=(3.0, 6.0), step=0.1)
        s_software = st.slider("Software EUR/a (low..high)", min_value=0.0, max_value=60_000.0, value=(12_000.0, 25_000.0), step=500.0)
    with c3:
        s_part = st.slider("Teilnehmerquote (low..high)", min_value=0.0, max_value=1.0, value=(0.8, 1.0), step=0.01)
        s_export = st.slider("Exportanteil (low..high)", min_value=0.0, max_value=1.0, value=(0.0, 0.2), step=0.01)

levers = {
    "delta_ct_per_kwh": (float(s_price[0]), float(s_price[1])),
    "base_fee_eur_per_customer_month": (float(s_basefee[0]), float(s_basefee[1])),
    "loan_interest": (float(s_interest[0]) / 100.0, float(s_interest[1]) / 100.0),
    "software_lic_eur_a": (float(s_software[0]), float(s_software[1])),
    "participation_rate": (float(s_part[0]), float(s_part[1])),
    "export_share_of_yield": (float(s_export[0]), float(s_export[1])),
}

sens = one_way_sensitivity(p, levers)

# Pretty formatting
sens_show = sens[[
    "lever",
    "low",
    "high",
    "irr_low",
    "irr_base",
    "irr_high",
    "npv_low_eur",
    "npv_base_eur",
    "npv_high_eur",
    "irr_low_delta",
    "irr_high_delta",
    "npv_low_delta_eur",
    "npv_high_delta_eur",
]].copy()

st.dataframe(sens_show, use_container_width=True)

st.caption("Interpretation: Hoehere IRR/NPV-Werte sind besser. 'Delta' zeigt die Abweichung gegenueber dem Basisfall.")
