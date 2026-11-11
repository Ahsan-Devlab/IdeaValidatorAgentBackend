# Builds FinanceInput from: user overrides > market search > starter assumptions.
from app.models import IdeaInput, MarketSizeReport, FinanceInput

# Starter assumptions in USD. NOT sourced facts. The report will show them as "assumed".
REACH, WIN, MARGIN, CHURN = 0.2, 0.02, 0.8, 0.05
CAC_MONTHS_OF_PRICE = 6   # we assume CAC = 6 x the monthly price
VARIABLE_SHARE = 0.15     # we assume 15% of price goes to serving one user
FIXED_COSTS, CASH = 300, 3000

def build_finance_input(inp: IdeaInput, market: MarketSizeReport | None):
    notes: dict[str, str] = {}

    # Customers: user value first, then the market search result
    customers, price = inp.total_customers, inp.price_per_month
    if customers:
        notes["total_customers"] = f"{customers} (given by user)"
    elif market and market.total_customers:
        customers = market.total_customers
        notes["total_customers"] = f"{customers} (from search: {market.customers_note})"
        # If the user's number overrides the search result, say so clearly in the report
    if inp.total_customers and market and market.total_customers:
        notes["market_search_customers"] = (
            f"{market.total_customers} found by search, NOT used in finance ({market.customers_note})")
    # Price: user value first, then search result, but only if it is already in USD
    if price:
        notes["price_per_month"] = f"{price} USD (given by user)"
    elif market and market.price_per_month and market.currency == "USD":
        price = market.price_per_month
        notes["price_per_month"] = f"{price} USD (from search)"

    # Without these two numbers any result would be a guess, so skip finance
    if not customers or not price:
        notes["finance"] = "Skipped: customer count or price missing. Provide total_customers and price_per_month."
        return None, notes

    notes.update({
        "reach_pct": f"{REACH} (assumed)", "win_pct": f"{WIN} (assumed)",
        "gross_margin": f"{MARGIN} (assumed)", "monthly_churn": f"{CHURN} (assumed)",
        "cac": f"{CAC_MONTHS_OF_PRICE * price} USD (assumed: 6x monthly price)",
        "variable_cost_per_user": f"{VARIABLE_SHARE * price} USD (assumed: 15% of price)",
        "fixed_costs_monthly": f"{FIXED_COSTS} USD (assumed)", "cash": f"{CASH} USD (assumed)",
    })
    return FinanceInput(
        total_customers=customers, price_per_month=price,
        reach_pct=REACH, win_pct=WIN, gross_margin=MARGIN, monthly_churn=CHURN,
        cac=CAC_MONTHS_OF_PRICE * price, variable_cost_per_user=VARIABLE_SHARE * price,
        fixed_costs_monthly=FIXED_COSTS, cash=CASH,
    ), notes