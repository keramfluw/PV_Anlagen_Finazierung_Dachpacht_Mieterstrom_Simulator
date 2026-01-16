from __future__ import annotations

from dataclasses import dataclass
import numpy as np
import pandas as pd

from finance import Loan, irr, npv


@dataclass
class ProjectInputs:
    # Investment
    pv_capex_eur: float
    meter_upgrade_capex_eur: float
    loan_amount_eur: float

    # PV and customers
    pv_yield_kwh_a: float
    customers_100pct: int
    participation_rate: float  # 0..1

    # Baseline revenues (given)
    baseline_sales_revenue_eur_a: float  # annual revenue from PV-strom sale to tenants at current assumptions

    # OPEX
    software_lic_eur_a: float
    roof_lease_eur_a: float
    other_opex_eur_a: float
    o_and_m_pct_of_pv_capex: float  # e.g. 0.012

    # Prices / levers
    delta_ct_per_kwh: float  # change vs baseline
    base_fee_eur_per_customer_month: float

    # Grid export and residual
    export_share_of_yield: float  # 0..1 of PV yield exported (not sold as tenant PV)
    export_price_ct_per_kwh: float

    # Financial
    loan_interest: float
    loan_term_years: int
    grace_years: int
    discount_rate: float  # for NPV
    analysis_years: int = 25


def compute_baseline_price_ct_per_kwh(pv_yield_kwh_a: float, baseline_sales_revenue_eur_a: float, export_share: float) -> float:
    sold_kwh = pv_yield_kwh_a * max(0.0, min(1.0, 1.0 - export_share))
    if sold_kwh <= 0:
        return 0.0
    return (baseline_sales_revenue_eur_a / sold_kwh) * 100.0


def run_project(p: ProjectInputs) -> tuple[pd.DataFrame, dict]:
    """Return yearly cashflow table and summary metrics."""

    years = int(p.analysis_years)
    idx = np.arange(0, years + 1)  # include year 0

    capex_total = float(p.pv_capex_eur) + float(p.meter_upgrade_capex_eur)
    loan_amount = float(p.loan_amount_eur)
    equity = capex_total - loan_amount

    participation = max(0.0, min(1.0, float(p.participation_rate)))
    customers = int(round(p.customers_100pct * participation))

    export_share = max(0.0, min(1.0, float(p.export_share_of_yield)))
    sold_share = 1.0 - export_share

    # Baseline price derived from baseline tenant sales revenue
    baseline_price_ct = compute_baseline_price_ct_per_kwh(p.pv_yield_kwh_a, p.baseline_sales_revenue_eur_a, export_share)
    price_ct = max(0.0, baseline_price_ct + float(p.delta_ct_per_kwh))

    # Energy volumes
    sold_kwh = float(p.pv_yield_kwh_a) * sold_share
    export_kwh = float(p.pv_yield_kwh_a) * export_share

    # Revenues
    tenant_energy_revenue = sold_kwh * (price_ct / 100.0)
    base_fees = customers * float(p.base_fee_eur_per_customer_month) * 12.0
    export_revenue = export_kwh * (float(p.export_price_ct_per_kwh) / 100.0)

    annual_revenue = tenant_energy_revenue + base_fees + export_revenue

    # OPEX
    o_and_m = float(p.pv_capex_eur) * float(p.o_and_m_pct_of_pv_capex)
    annual_opex = float(p.software_lic_eur_a) + float(p.roof_lease_eur_a) + float(p.other_opex_eur_a) + o_and_m

    # Loan schedule (capped to analysis horizon)
    loan = Loan(principal=loan_amount, annual_interest=float(p.loan_interest), term_years=int(p.loan_term_years), grace_years=int(p.grace_years))
    sch = loan.schedule()
    debt_payment = np.zeros(years)
    debt_interest = np.zeros(years)
    debt_principal = np.zeros(years)
    for i in range(min(years, len(sch["payment"]))):
        debt_payment[i] = sch["payment"][i]
        debt_interest[i] = sch["interest"][i]
        debt_principal[i] = sch["principal"][i]

    # Build table
    df = pd.DataFrame({
        "year": idx,
        "revenue_eur": 0.0,
        "tenant_energy_revenue_eur": 0.0,
        "base_fees_eur": 0.0,
        "export_revenue_eur": 0.0,
        "opex_eur": 0.0,
        "ebitda_eur": 0.0,
        "debt_payment_eur": 0.0,
        "debt_interest_eur": 0.0,
        "debt_principal_eur": 0.0,
        "free_cashflow_to_equity_eur": 0.0,
    })

    # Year 0 equity outflow
    df.loc[0, "free_cashflow_to_equity_eur"] = -equity

    for y in range(1, years + 1):
        df.loc[y, "revenue_eur"] = annual_revenue
        df.loc[y, "tenant_energy_revenue_eur"] = tenant_energy_revenue
        df.loc[y, "base_fees_eur"] = base_fees
        df.loc[y, "export_revenue_eur"] = export_revenue
        df.loc[y, "opex_eur"] = annual_opex
        df.loc[y, "ebitda_eur"] = annual_revenue - annual_opex
        dp = debt_payment[y - 1] if y - 1 < years else 0.0
        di = debt_interest[y - 1] if y - 1 < years else 0.0
        dpr = debt_principal[y - 1] if y - 1 < years else 0.0
        df.loc[y, "debt_payment_eur"] = dp
        df.loc[y, "debt_interest_eur"] = di
        df.loc[y, "debt_principal_eur"] = dpr
        df.loc[y, "free_cashflow_to_equity_eur"] = (annual_revenue - annual_opex) - dp

    cashflows = df["free_cashflow_to_equity_eur"].tolist()

    metrics = {
        "capex_total_eur": capex_total,
        "equity_eur": equity,
        "baseline_price_ct_per_kwh": baseline_price_ct,
        "price_ct_per_kwh": price_ct,
        "customers": customers,
        "sold_kwh": sold_kwh,
        "export_kwh": export_kwh,
        "annual_revenue_eur": annual_revenue,
        "annual_opex_eur": annual_opex,
        "annual_ebitda_eur": annual_revenue - annual_opex,
        "irr_equity": irr(cashflows),
        "npv_equity_eur": npv(float(p.discount_rate), cashflows),
    }

    # DSCR for years where debt exists
    dscr_list = []
    for y in range(1, years + 1):
        dp = df.loc[y, "debt_payment_eur"]
        if dp > 1e-9:
            dscr_list.append(df.loc[y, "ebitda_eur"] / dp)
    metrics["dscr_min"] = float(min(dscr_list)) if dscr_list else None

    return df, metrics
