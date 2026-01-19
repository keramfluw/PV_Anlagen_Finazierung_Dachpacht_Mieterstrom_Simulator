import streamlit as st
import numpy as np
import pandas as pd
import numpy_financial as npf

st.set_page_config(page_title="Mieterstrom Wirtschaftlichkeit", layout="wide")
st.title("baetz energy Mieterstrom – Wirtschaftlichkeits- & Hebel-Simulator")

# Defaultwerte aus deinen Parametern
DEFAULTS = {
    "kredit": 1_400_000.0,
    "zins_pct": 4.2,
    "laufzeit": 25,
    "tilgungsfrei": 0,
    "invest_zaehler": 80_000.0,
    "pv_kwh": 989_010.0,
    "teilnehmer_max": 386,
    "teilnehmerquote": 1.0,
    "umsatz": 255_319.0,
    "software": 16_212.0,
    "opex_sonstig": 0.0,
}

with st.sidebar:
    st.header("Eingaben")
    kredit = st.number_input("Kreditbedarf PV (€)", value=float(DEFAULTS["kredit"]), step=50_000.0)
    zins = st.number_input("Zins (% p.a.)", value=float(DEFAULTS["zins_pct"]), step=0.1) / 100.0
    laufzeit = st.number_input("Laufzeit (Jahre)", min_value=1, max_value=40, value=int(DEFAULTS["laufzeit"]))
    tilgungsfrei = st.number_input("Tilgungsfreie Jahre (nur Zins)", min_value=0, max_value=10, value=int(DEFAULTS["tilgungsfrei"]))

    st.subheader("Erzeugung & Vermarktung")
    pv_kwh = st.number_input("PV-Ertrag (kWh/a)", value=float(DEFAULTS["pv_kwh"]), step=10_000.0)
    umsatz = st.number_input("Erlöse PV-Stromverkauf (€ / a)", value=float(DEFAULTS["umsatz"]), step=5_000.0)

    st.subheader("Teilnahme")
    teilnehmer_max = st.number_input("Anzahl potenzieller Kunden (100% Quote)", min_value=1, value=int(DEFAULTS["teilnehmer_max"]))
    teilnehmerquote = st.slider("Teilnehmerquote", 0.0, 1.0, float(DEFAULTS["teilnehmerquote"]), 0.01)

    st.subheader("Kosten")
    invest_zaehler = st.number_input("Einmalkosten Zählerertüchtigung (€)", value=float(DEFAULTS["invest_zaehler"]), step=10_000.0)
    software = st.number_input("Softwarelizenz (€ / a)", value=float(DEFAULTS["software"]), step=1_000.0)
    opex_sonstig = st.number_input("Sonstige OPEX (€ / a)", value=float(DEFAULTS["opex_sonstig"]), step=1_000.0)

# Abgeleitete Größen
teilnehmer = teilnehmer_max * teilnehmerquote
preis_eur_per_kwh = umsatz / pv_kwh if pv_kwh > 0 else 0.0

# Finanzierung: Annuität nach tilgungsfreien Jahren
# In tilgungsfreien Jahren: nur Zinsen; danach Annuität über Restlaufzeit
cashflows = []

# Jahr 0: Eigenmittel/Invest (hier: Invest Zähler als Cash-out; Kredit als Cash-in wird separat nicht modelliert)
# Für eine Projekt-CF-Sicht betrachten wir: Capex (Kredit) als Investitionsauszahlung, Finanzierung über Annuität als Auszahlungen.
# Vereinfachung: Capex = kredit + invest_zaehler in Jahr 0.
capex0 = -(kredit + invest_zaehler)
cashflows.append(capex0)

annual_opex = software + opex_sonstig
annual_operating_cf = umsatz - annual_opex

# tilgungsfreie Jahre
for _ in range(int(tilgungsfrei)):
    interest_only = -(kredit * zins)
    cashflows.append(annual_operating_cf + interest_only)

# Annuität für verbleibende Jahre
remaining = int(laufzeit) - int(tilgungsfrei)
if remaining <= 0:
    remaining = 1
annuity = float(npf.pmt(zins, remaining, kredit))  # negativ (Auszahlung)
for _ in range(remaining):
    cashflows.append(annual_operating_cf + annuity)

# Kennzahlen
irr = float(npf.irr(cashflows)) if len(cashflows) > 2 else np.nan
npv = float(npf.npv(zins, cashflows))
payback = np.nan
cum = 0.0
for i, cf in enumerate(cashflows[1:], start=1):
    cum += cf
    if cum >= -capex0:
        payback = i
        break

# Ausgabe
c1, c2, c3, c4 = st.columns(4)
c1.metric("Ø Preis (€/kWh)", f"{preis_eur_per_kwh:.3f}")
c2.metric("Teilnehmer (Ø)", f"{teilnehmer:.1f}")
c3.metric("Operativer CF (€/a)", f"{annual_operating_cf:,.0f} €")
c4.metric("Annuität nach tilgungsfrei (€/a)", f"{-annuity:,.0f} €")

st.subheader("Projektkennzahlen (vereinfachte Projekt-Cashflows)")
k1, k2, k3 = st.columns(3)
k1.metric("IRR", "–" if np.isnan(irr) else f"{irr*100:.2f} %")
k2.metric("NPV (Diskont = Zins)", f"{npv:,.0f} €")
k3.metric("Payback (Jahre)", "–" if np.isnan(payback) else str(int(payback)))

df = pd.DataFrame({"Jahr": list(range(0, len(cashflows))), "Cashflow (€)": cashflows})
st.dataframe(df, use_container_width=True)

st.line_chart(df.set_index("Jahr")["Cashflow (€)"])

st.download_button(
    "Cashflows als CSV herunterladen",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="cashflows.csv",
    mime="text/csv",
)

st.caption("Hinweis: Das ist eine robuste Minimalversion ohne matplotlib (Cloud-sicher). Erweiterungen: DSCR, Dachpacht, Reststrom, Speicher, Sensitivitätsmatrix.")
