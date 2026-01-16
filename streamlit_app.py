
import streamlit as st
import numpy as np
import pandas as pd
import numpy_financial as npf
import matplotlib.pyplot as plt

st.set_page_config(page_title="Mieterstrom Wirtschaftlichkeit", layout="wide")
st.title("Mieterstrom – Wirtschaftlichkeits- & Hebel-Simulator")

kredit = st.number_input("Kreditbedarf (€)", value=1_400_000.0, step=50_000.0)
zins = st.number_input("Zinssatz (%)", value=4.2) / 100
laufzeit = st.number_input("Laufzeit (Jahre)", value=25)

ertrag = st.number_input("PV-Ertrag (kWh/a)", value=989_010.0, step=10_000.0)
erloes = st.number_input("PV-Stromerlös (€ / a)", value=255_319.0, step=5_000.0)
opex = st.number_input("OPEX gesamt (€ / a)", value=16_212.0, step=1_000.0)

annuitaet = npf.pmt(zins, laufzeit, kredit)
cashflow = erloes - opex + annuitaet

st.metric("Annuität / Jahr", f"{-annuitaet:,.0f} €")
st.metric("Jährlicher Cashflow", f"{cashflow:,.0f} €")

years = np.arange(1, laufzeit + 1)
cfs = np.full(laufzeit, cashflow)

fig, ax = plt.subplots()
ax.plot(years, cfs)
ax.set_xlabel("Jahr")
ax.set_ylabel("Cashflow (€)")
st.pyplot(fig)
