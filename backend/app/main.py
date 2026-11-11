from fastapi import FastAPI, HTTPException
from app.llm import build_llm
from app.models import IdeaInput, StructuredIdea, FinanceInput, FinanceResult
from app.agents.intake import run_intake
from app.finance.calculators import run_finance
from app.tools.web_search import search_community
from app.tools.hackernews import search_hackernews
from app.agents.demand import run_demand
from app.models import DemandReport
from app.agents.competitor import run_competitors
from app.models import CompetitorReport
from app.agents.market import run_market_size
from app.models import MarketSizeReport
from app.graph import graph, UnsupportedIdea
from app.models import ValidationResult
from fastapi.responses import Response
from app.report.build_pdf import build_pdf
from app.config import settings
from app.db import save_report, get_report
from fastapi.middleware.cors import CORSMiddleware



app = FastAPI(title="Idea Validator")

# Lets the browser frontend call this API. Only the listed addresses are allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",")],
    allow_methods=["GET", "POST"],   # we only use these two
    allow_headers=["*"],
)

@app.get("/testing")
def test_llm():
    llm = build_llm()
    response = llm.invoke("Hello, who are you?")
    return {"response": response}


@app.post("/intake", response_model=StructuredIdea)
def intake(data: IdeaInput):
    try:
        result = run_intake(data.idea)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    if result.product_type == "other":
        raise HTTPException(status_code=400, detail="Product type 'other' is not allowed.")
    return result

@app.post("/finance", response_model=FinanceResult)
def finance(data: FinanceInput):
    return run_finance(data)


@app.get("/test-tools")
def test_tools(q: str):
    return {
        "community_search": search_community(q),
        "hackernews_search": search_hackernews(q),

    }

@app.post("/demand", response_model=DemandReport)
def demand(idea: StructuredIdea):
    # Takes the structured idea from /intake and judges market demand.
    try:
        return run_demand(idea)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Demand agent failed: {e}")



@app.post("/competitors", response_model=CompetitorReport)
def competitors(idea: StructuredIdea):
    # Takes the structured idea and finds competitors
    try:
        return run_competitors(idea)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Competitor agent failed: {e}")



@app.post("/markget-size", response_model=MarketSizeReport)
def market_size(idea: StructuredIdea):
    try:
        return run_market_size(idea)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Market size agent failed: {e}")



@app.post("/validate", response_model=ValidationResult)
def validate(data: IdeaInput):
    try:
        s = graph.invoke({"inp": data, "errors": []})
    except UnsupportedIdea as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Pipeline failed: {e}")
    result = ValidationResult(
        idea=s["idea"], demand=s.get("demand"), competitors=s.get("competitors"),
        market=s.get("market"), finance=s.get("finance"),
        assumptions=s.get("assumptions", {}), score=s["score"], errors=s["errors"],
        report_text=s.get("report_text"),
    )
    # Save the report only if Supabase is set up
    if settings.supabase_url and settings.supabase_secret_key:
        try:
            result.report_id = save_report(result.model_dump(mode="json"))
        except Exception as e:
            # A failed save must not throw away a finished (and costly) report
            result.errors.append(f"save: {e}")
    return result

@app.post("/report/pdf")
def report_pdf(result: ValidationResult):
    try:
        pdf = build_pdf(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail= f"PDF failed: {e}")
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="idea-validation-report.pdf"'})



def load_or_404(report_id: str) -> ValidationResult:
    # Shared by both report routes below
    try:
        data = get_report(report_id)
    except Exception as e:
        # Most common cause: the free project is paused. Restore it in the dashboard.
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")
    if not data:
        raise HTTPException(status_code=404, detail="Report not found")
    return ValidationResult(**data)

@app.get("/reports/{report_id}", response_model=ValidationResult)
def read_report(report_id: str):
    # The frontend share page will call this
    return load_or_404(report_id)

@app.get("/reports/{report_id}/pdf")
def read_report_pdf(report_id: str):
    # "inline" shows the PDF in the browser tab when someone opens the share link
    pdf = build_pdf(load_or_404(report_id))
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": 'inline; filename="idea-validation-report.pdf"'})

@app.get("/health")
def health():
    # A cheap database read. In Step 13 a free pinger calls this daily to keep Supabase awake.
    try:
        get_report("health-check")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {e}")