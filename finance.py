from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass
class Loan:
    """Yearly amortizing loan with optional interest-only grace years."""

    principal: float
    annual_interest: float  # 0.045 = 4.5%
    term_years: int
    grace_years: int = 0

    def schedule(self) -> dict:
        """Return amortization schedule (yearly) as numpy arrays.

        Years are 1..term_years.
        During grace years, payment equals interest (no principal repayment).
        Afterwards, payments are annuity-style for remaining years.
        """
        P0 = float(self.principal)
        r = float(self.annual_interest)
        n = int(self.term_years)
        g = int(self.grace_years)
        g = max(0, min(g, n))

        years = np.arange(1, n + 1)
        balance = np.zeros(n + 1)
        balance[0] = P0

        interest = np.zeros(n)
        principal = np.zeros(n)
        payment = np.zeros(n)

        remaining_years = n - g
        annuity = 0.0
        if remaining_years > 0:
            if abs(r) < 1e-12:
                annuity = P0 / remaining_years
            else:
                annuity = P0 * (r * (1 + r) ** remaining_years) / ((1 + r) ** remaining_years - 1)

        for t in range(1, n + 1):
            i = balance[t - 1] * r
            interest[t - 1] = i
            if t <= g:
                payment[t - 1] = i
                principal[t - 1] = 0.0
            else:
                payment[t - 1] = annuity
                principal[t - 1] = max(0.0, payment[t - 1] - i)
            balance[t] = max(0.0, balance[t - 1] - principal[t - 1])

        return {
            "year": years,
            "balance_start": balance[:-1],
            "interest": interest,
            "principal": principal,
            "payment": payment,
            "balance_end": balance[1:],
        }


def npv(discount_rate: float, cashflows: list[float]) -> float:
    """NPV with cashflows[0] at t=0."""
    r = float(discount_rate)
    total = 0.0
    for t, cf in enumerate(cashflows):
        total += cf / ((1 + r) ** t)
    return total


def irr(cashflows: list[float]) -> float | None:
    """IRR via numpy. Returns None if not computable."""
    try:
        val = np.irr(cashflows)  # type: ignore[attr-defined]
    except Exception:
        # numpy removed np.irr in some versions; implement a fallback
        val = _irr_newton(cashflows)
    if val is None:
        return None
    if np.isnan(val):
        return None
    return float(val)


def _irr_newton(cashflows: list[float], guess: float = 0.08) -> float | None:
    """Newton-Raphson IRR fallback."""
    r = guess
    for _ in range(100):
        f = 0.0
        df = 0.0
        for t, cf in enumerate(cashflows):
            denom = (1 + r) ** t
            f += cf / denom
            if t > 0:
                df -= t * cf / ((1 + r) ** (t + 1))
        if abs(df) < 1e-12:
            return None
        step = f / df
        r -= step
        if abs(step) < 1e-10:
            return r
    return None
