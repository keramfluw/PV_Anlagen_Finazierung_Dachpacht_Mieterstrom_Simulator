from __future__ import annotations

import copy
import pandas as pd

from model import ProjectInputs, run_project


def one_way_sensitivity(base: ProjectInputs, levers: dict[str, tuple[float, float]]) -> pd.DataFrame:
    """One-way sensitivity for simple scalar fields on ProjectInputs.

    levers: mapping of ProjectInputs field_name -> (low, high)
    Returns a table with base/low/high metrics.
    """
    _, base_m = run_project(base)
    base_irr = base_m.get("irr_equity")
    base_npv = base_m.get("npv_equity_eur")

    rows = []
    for field, (low, high) in levers.items():
        b = getattr(base, field)

        p_low = copy.deepcopy(base)
        setattr(p_low, field, low)
        _, m_low = run_project(p_low)

        p_high = copy.deepcopy(base)
        setattr(p_high, field, high)
        _, m_high = run_project(p_high)

        rows.append({
            "lever": field,
            "base": b,
            "low": low,
            "high": high,
            "irr_base": base_irr,
            "irr_low": m_low.get("irr_equity"),
            "irr_high": m_high.get("irr_equity"),
            "npv_base_eur": base_npv,
            "npv_low_eur": m_low.get("npv_equity_eur"),
            "npv_high_eur": m_high.get("npv_equity_eur"),
        })

    df = pd.DataFrame(rows)

    def _delta(a, b):
        if a is None or b is None:
            return None
        return a - b

    df["irr_low_delta"] = df.apply(lambda r: _delta(r["irr_low"], r["irr_base"]), axis=1)
    df["irr_high_delta"] = df.apply(lambda r: _delta(r["irr_high"], r["irr_base"]), axis=1)
    df["npv_low_delta_eur"] = df["npv_low_eur"] - df["npv_base_eur"]
    df["npv_high_delta_eur"] = df["npv_high_eur"] - df["npv_base_eur"]

    return df
