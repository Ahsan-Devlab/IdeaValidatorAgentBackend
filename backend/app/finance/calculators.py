import math
from app.models import FinanceInput, FinanceResult

def market_size(total_Customers, price_per_month, reach_pct, win_pct):
    """
    Calculate the market size (TAM, SAM, SOM) based on the provided inputs.

    Args:
        total_Customers (int): Total potential customers in the market.
        price_per_month (float): Price per month for the product/service.
        reach_pct (float): Percentage of the market that can be reached (0 to 1).
        win_pct (float): Percentage of the reachable market that can be won (0 to 1).

    Returns:
        tuple: A tuple containing TAM, SAM, and SOM values.
    """
    tam = total_Customers * price_per_month * 12  # Total Addressable Market
    sam = tam * reach_pct  # Serviceable Addressable Market
    som = sam * win_pct  # Serviceable Obtainable Market
    return tam, sam, som


def unit_economics(price_per_month, gross_margin, monthly_churn, cac):
    profit_per_month = price_per_month * gross_margin   # profit from one user each month
    # LTV = Customer lifetime value, total profit from one user. Average life = 1 / churn months.
    ltv = profit_per_month / monthly_churn
    ratio = ltv / cac if cac > 0 else None              # healthy SaaS is usually 3 or more
    #CAC (Customer Acquisition Cost): The total money spent on sales and marketing to win a single new customer. 
    payback = cac / profit_per_month if cac > 0 else None  # months to earn back CAC
    return ltv, ratio, payback

def break_even(fixed_costs_monthly, price_per_month, variable_cost_per_user):
    margin_per_user = price_per_month - variable_cost_per_user
    if margin_per_user <= 0:
        return None   # we lose money on every user, so break-even never happens
    return math.ceil(fixed_costs_monthly / margin_per_user)  # round up to whole users

#how many months your startup can survive before running out of money
def runway(cash, fixed_costs_monthly):
    if fixed_costs_monthly <= 0:
        return None
    # Simple version: assumes zero revenue, so burn = fixed costs
    return cash / fixed_costs_monthly

#it acts as the Orchestrator
def run_finance(f: FinanceInput) -> FinanceResult:
    # Calls every calculator and packs the answers into one result object.
    tam, sam, som = market_size(f.total_customers, f.price_per_month, f.reach_pct, f.win_pct)
    ltv, ratio, payback = unit_economics(f.price_per_month, f.gross_margin, f.monthly_churn, f.cac)
    return FinanceResult(
        tam=round(tam, 2), sam=round(sam, 2), som=round(som, 2),
        ltv=round(ltv, 2),
        ltv_cac_ratio=round(ratio, 2) if ratio is not None else None,
        payback_months=round(payback, 2) if payback is not None else None,
        break_even_users=break_even(f.fixed_costs_monthly, f.price_per_month, f.variable_cost_per_user),
        runway_months=round(r, 1) if (r := runway(f.cash, f.fixed_costs_monthly)) is not None else None,
    )