import operator
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, START, END
from app.models import IdeaInput
from app.agents.intake import run_intake
from app.agents.demand import run_demand
from app.agents.competitor import run_competitors
from app.agents.market import run_market_size
from app.finance.assumptions import build_finance_input
from app.finance.calculators import run_finance
from app.finance.score import score_idea
from app.agents.writer import run_writer

class UnsupportedIdea(Exception):
    pass

class state(TypedDict, total=False):
    inp: IdeaInput
    idea: object; demand: object; competitors: object
    market: object; finance: object; score: object
    assumptions: dict
    errors: Annotated[list[str], operator.add]
    report_text: object

def intake_node(state):
    idea = run_intake(state["inp"].idea)
    if idea.product_type == "other":
        raise UnsupportedIdea("Only SaaS, web app, or mobile app allowed")
    return{"idea": idea}

def safe(key, fn):
    def node(state):
        try:
            return {key: fn(state["idea"])}
        except Exception as e:
            return {key: None, "errors": [f"{key}: {e}"]}
    return node

def finance_node(state):
    fin_input, notes = build_finance_input(state["inp"], state.get("market"))
    return {"finance": run_finance(fin_input) if fin_input else None, "assumptions": notes}

def score_node(state):
    return {"score": score_idea(state.get("demand"), state.get("competitors"), state.get("finance"))}

def writer_node(state):
    # Convert every report object to plain dicts for the writer
    keys = ("idea", "demand", "competitors", "market", "finance", "score")
    data = {k: (state[k].model_dump(mode="json") if state.get(k) else None) for k in keys}
    data["assumptions"] = state.get("assumptions", {})
    try:
        return {"report_text": run_writer(data)}
    except Exception as e:
        return {"report_text": None, "errors": [f"writer: {e}"]}

g = StateGraph(state)

g.add_node("intake", intake_node)
g.add_node("demand_node", safe("demand", run_demand))
g.add_node("competitor_node", safe("competitors", run_competitors))
g.add_node("market_node", safe("market", run_market_size))
g.add_node("finance_node", finance_node)
g.add_node("score_node", score_node)
g.add_node("writer_node", writer_node)

g.add_edge(START, "intake")
for n in ("demand_node", "competitor_node", "market_node"):
    g.add_edge("intake", n)

g.add_edge(["demand_node", "competitor_node", "market_node"], "finance_node")
g.add_edge("finance_node", "score_node")
g.add_edge("score_node", "writer_node")
g.add_edge("writer_node", END)

graph = g.compile()

# Add this at the bottom of your file
with open("graph_map.png", "wb") as f:
    f.write(graph.get_graph().draw_mermaid_png())