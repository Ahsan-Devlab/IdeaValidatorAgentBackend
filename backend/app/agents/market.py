from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.llm import build_llm
from app.models import StructuredIdea, MarketSizeReport
from app.tools.web_search import search_web

# Directories and videos are not statistics, so we skip them
BAD_SOURCES = ("scribd.com", "youtube.com", "pinterest.com")
MIN_CUSTOMERS = 1000   # a "market" of 30 shops is a contact list, not a statistic

parser = PydanticOutputParser(pydantic_object=MarketSizeReport)

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You extract market numbers from search results. Use ONLY the results given.\n"
     "Rules:\n"
     "- total_customers: only a number that appears in the results and matches the target customer and region.\n"
     "- In customers_note, say exactly what the number counts and the year if shown.\n"
     "- If numbers conflict, choose the one closest to the target customer and mention the conflict.\n"
     "- Do NOT calculate, estimate, or use your own knowledge. If no suitable number exists, use null.\n"
          "- Ignore contact directories, member lists, and company lists. Use only a count from a statistic, survey, report, or news article.\n"
     "- price_per_month: only if a price is stated in the results; set currency too. Otherwise null.\n"
     "- limitations: say what the number counts and does not count (for example all shops vs only shops selling on credit) "
     "and how reliable the source looks. Never write 'No limitations'.\n"
     "- customers_source_url must be copied exactly from the results.\n\n"
     "{format_instructions}"),
    ("human", "Target customer: {customer}\nRegion: {region}\n\nSearch results:\n{results}"),
]).partial(format_instructions=parser.get_format_instructions())


chain = prompt | build_llm(temperature=0) | parser

def run_market_size(idea: StructuredIdea) -> MarketSizeReport:
    found = {}   # key = url, which removes duplicates
    for q in (f"number of {idea.target_customer} in {idea.region}",
              f"how many {idea.target_customer} in {idea.region} statistics"):
        for r in search_web(q):
            if not any(b in r["url"] for b in BAD_SOURCES):
                found[r["url"]] = r

    if not found:
        return MarketSizeReport(total_customers=None, curstomers_note="No suitable number found.",
                                price_per_month=None, currency=None,
                                limitations="Search returned no results.")

    text = "\n".join(f"- {r['title']} | {r['snippet']} | {url}" for url, r in found.items())
    report = chain.invoke({"customer": idea.target_customer, "region": idea.region, "results": text})

    if report.customers_source_url not in found:
        report.total_customers = None
        report.curstomers_note = "LLM made up a source link."

    # Reject numbers too small to be a real market count
    if report.total_customers is not None and report.total_customers < MIN_CUSTOMERS:
        report.customers_note += " (Ignored: too small to be a market statistic.)"
        report.total_customers = None
        report.customers_source_url = None

    return report