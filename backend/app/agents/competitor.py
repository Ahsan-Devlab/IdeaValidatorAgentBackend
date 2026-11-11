from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.llm import build_llm
from app.models import StructuredIdea, CompetitorReport
from app.tools.web_search import search_web

parser = PydanticOutputParser(pydantic_object=CompetitorReport)

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a skeptical competitor analyst. Use ONLY the search results given.\n"
     "Rules:\n"
     "- List at most 7 competitors, ordered from most direct to least direct.\n"
     "- Direct = same customer AND same problem. Skip general accounting, ERP, CRM, or bank software unless no direct product exists.\n"
     "- Merge duplicates (the same product listed twice) into one entry.\n"
          "- name must be a real product or company name, never a page title like 'X Alternative'.\n"
     "- weakness_or_gap: only what the results say. If not stated, write 'Not found'. Never infer weaknesses.\n"
     "- competition_level is 'high' if 3 or more listed competitors offer the core feature of the idea.\n"
     "- pricing: write it only if the results state it. Otherwise write 'Not found'. Never guess prices.\n"
     "- source_url must be copied exactly from the results.\n"
     "- market_gap: a feature missing from search results is NOT proof a competitor lacks it. "
     "Name a gap only if a result says competitors lack it. Otherwise write 'No proven gap: competitors may already offer this.'\n"
     "- Prefer products available in the customer's region. Skip products tied to another country's payment system.\n"
     "- limitations: say what the results could not show (pricing, weaknesses, local apps). Never write 'Not found'.\n"
     "If competitors already cover the main features, say the market is crowded and the gap is unclear.\n"
     "- If you find few or no competitors, use competition_level 'unclear'. Do NOT claim 'no competition'.\n\n"
     "{format_instructions}"),
    ("human", "Idea: {idea}\n\nSearch results:\n{results}"),
]).partial(format_instructions=parser.get_format_instructions())


chain = prompt | build_llm(temperature=0) | parser

def gather_results(idea: StructuredIdea) -> dict:
    found = {}   # key = url, which removes duplicates
    # Use up to 3 keywords. One keyword can easily hit the wrong topic.
    for kw in idea.keywords[:3]:
        # "app alternatives" pushes results toward real products, not articles.
        for r in search_web(f"best {kw} apps alternatives"):
            found[r["url"]] = r
    return found

def run_competitors(idea: StructuredIdea) -> CompetitorReport:
    found = gather_results(idea)
    if not found:
        return CompetitorReport(competition_level="unclear", competitors=[],
                                market_gap="Not enough data.",
                                limitations="Search returned no results.")
    
    text = "\n".join(f"- {r['title']} | {r['snippet']} | {url}" for url, r in found.items())
    idea_text = f"{idea.problem} | Customer: {idea.target_customer} | Solution: {idea.solution} | Region: {idea.region}"
    report = chain.invoke({"idea": idea_text, "results": text})

    # Safety check: drop any competitor whose source link the LLM made up
    report.competitors = [c for c in report.competitors if c.source_url in found]
        # Remove duplicate names, keep the first one
    seen, unique = set(), []
    for c in report.competitors:
        if c.name.lower() not in seen:
            seen.add(c.name.lower())
            unique.append(c)
    report.competitors = unique[:7]
    # Rule of thumb so the label never contradicts the data: 4+ rivals = crowded
    if len(report.competitors) >= 4:
        report.competition_level = "high"
    return report