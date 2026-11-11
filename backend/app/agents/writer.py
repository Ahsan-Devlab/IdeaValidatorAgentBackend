import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.llm import build_llm
from app.models import ReportText

parser = PydanticOutputParser(pydantic_object=ReportText)

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You write a startup idea validation report for a founder. Use ONLY the data given.\n"
     "Rules:\n"
     "- Use plain, simple English. Be honest, not encouraging. Do not hype.\n"
     "- The verdict is score.verdict. Never change or soften it. End executive_summary with it.\n"
     "- Use only numbers that appear in the data. Never invent statistics, quotes, or prices.\n"
     "- Any number listed in 'assumptions' as (assumed) must be called an assumption in the text.\n"
     "- If a section has null data or a limitation, say what is missing. Do not fill the gap.\n"
     "- executive_summary: max 4 sentences. Do not list assumptions or finance numbers there.\n"
     "- Finance numbers use assumptions.total_customers. If market.total_customers is different, say so and describe it exactly as market.customers_note does. Never call it the TAM base.\n"
     "- Claim a market gap only if competitors.market_gap states one. If it says 'No proven gap', say that.\n"
     "- If any competitor has pricing 'Free', add a risk about charging for a paid plan.\n"
     "- key_risks: base them on the data (competition, weak demand, assumptions, missing data).\n"
     "You must return ONLY a raw JSON object, no markdown tags\n"
     "- next_steps: a practical 30-day plan, such as customer interviews and a landing page test.\n\n"
     "{format_instructions}"),
    ("human", "Data:\n{data}"),
]).partial(format_instructions=parser.get_format_instructions())


chain = prompt | build_llm(temperature=0) | parser


def run_writer(data: dict) -> ReportText:
    return chain.invoke({"data": json.dumps(data, indent= 1, default=str)})