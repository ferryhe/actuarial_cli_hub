from cashflower import variable
from input import assumptions


@variable()
def premium(t):
    if t == 0:
        return assumptions["initial_premium"]
    return premium(t - 1) * (1 + assumptions["growth_rate"])


@variable()
def claims(t):
    return premium(t) * assumptions["claim_ratio"]


@variable()
def net_cashflow(t):
    return premium(t) - claims(t)
