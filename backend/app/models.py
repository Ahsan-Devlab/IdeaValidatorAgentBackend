from typing import Literal
from pydantic import BaseModel, Field

class IdeaInput(BaseModel):
    idea: str = Field(min_length = 20, description = "The idea to be evaluated, must be at least 20 characters long.")
    total_customers: int | None = Field(default=None, gt=0)
    price_per_month: float | None = Field(default=None, gt=0)

class StructuredIdea(BaseModel):
    product_type: Literal["saas", "web_app", "mobile_app", "other"]
    problem: str
    target_customer: str
    solution: str
    business_model: str
    keywords: list[str]
    region: str = Field(default="global", description="Country or city where customers are, only if the user said it. Otherwise 'global'")


class FinanceInput(BaseModel):
    # The assumptions behind the math. Later, an agent will suggest these.
    # gt=0 means "greater than 0". le=1 means "at most 1". This blocks bad input.
    total_customers: int = Field(gt=0)          # all possible customers in the market
    price_per_month: float = Field(gt=0)        # what one user pays per month
    reach_pct: float = Field(gt=0, le=1)        # share of market we can reach (0.2 = 20%)
    win_pct: float = Field(gt=0, le=1)          # share of reachable market we win in year 1
    gross_margin: float = Field(gt=0, le=1)     # share of revenue left after direct costs
    monthly_churn: float = Field(gt=0, le=1)    # share of users who cancel each month
    cac: float = Field(ge=0)                    # cost to get one customer
    variable_cost_per_user: float = Field(ge=0) # monthly cost to serve one user (API, hosting)
    fixed_costs_monthly: float = Field(ge=0)    # monthly costs even with zero users
    cash: float = Field(ge=0)  


class FinanceResult(BaseModel):
    tam: float
    sam: float
    som: float
    ltv: float
    ltv_cac_ratio: float | None       # None when CAC is 0 (can't divide)
    payback_months: float | None
    break_even_users: int | None      # None if price does not cover variable cost
    runway_months: float | None       # None if there is no monthly cost


class Evidence(BaseModel):
    title: str
    url: str
    why_relevant: str


class DemandReport(BaseModel):
    demand_level: Literal["high", "medium", "low", "unclear"]
    summary: str
    pain_points: list[str]
    evidence: list[Evidence]
    limitations: str

class Competitor(BaseModel):
    name: str
    what_it_does: str
    pricing: str
    weakness_or_gap: str
    source_url: str

class CompetitorReport(BaseModel):
    competition_level: Literal["high", "medium", "low", "unclear"]
    competitors: list[Competitor]
    market_gap: str
    limitations: str

class MarketSizeReport(BaseModel):
    total_customers: int | None
    customers_source_url: str | None
    customers_note: str
    price_per_month: float | None
    currency: str | None
    limitations: str

class ScoreResult(BaseModel):
    total: int                                   # 0-100
    verdict: Literal["Go", "Pivot", "No-Go", "Insufficient data"]
    breakdown: dict[str, int]                    # factor -> points out of 100
    unknown_factors: list[str]   


class ReportText(BaseModel):
    executive_summary: str
    demand_analysis: str
    competition_analysis: str
    market_and_finance: str
    key_risks: list[str]
    next_steps: list[str]


class ValidationResult(BaseModel):
    idea: StructuredIdea
    demand: DemandReport
    competitors: CompetitorReport | None
    market: MarketSizeReport | None
    finance: FinanceResult | None
    assumptions: dict[str, str]                 
    score: ScoreResult
    errors: list[str]   
    report_text: ReportText | None = None
    report_id: str | None =None

