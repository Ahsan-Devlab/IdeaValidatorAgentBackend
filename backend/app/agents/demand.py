from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from app.llm import build_llm
from app.models import StructuredIdea, DemandReport
from app.tools.hackernews import search_hackernews
from app.tools.web_search import search_community


parser = PydanticOutputParser(pydantic_object=DemandReport)

prompt = ChatPromptTemplate.from_messages([
    ("system",
     "You are a skeptical market analyst. Judge demand for the idea using ONLY the posts given.\n"
     "Rules:\n"
     "- Ignore posts that are not about the same problem.\n"
     "- Only put a post in evidence if it is relevant. Copy its URL exactly.\n"
     "- limitations: name a product only if it appears in the posts given. Also state what is missing, such as willingness to pay.\n"
     "- If few relevant posts exist, use demand_level 'low' or 'unclear'. Do not be optimistic.\n"
     "- Never invent facts, numbers, or quotes.\n\n"
     "{format_instructions}"),
    ("human", "Idea: {idea}\n\nPosts found:\n{posts}"),
]).partial(format_instructions=parser.get_format_instructions())

from langchain_core.runnables import RunnableSequence

chain = RunnableSequence(prompt, build_llm(temperature=0), parser)

#chain = prompt | build_llm(temperature=0) | parser


def gather_posts(idea: StructuredIdea) ->  dict:
    posts = {}
    for kw in idea.keywords[:2]:
        for p in search_hackernews(kw):
            posts[p["url"]] = {"source": "Hacker News", "title": p["title"],
                               "text": f"{p['points']} points, {p['comments']} comments"}
        for p in search_community(f"{kw} problem"):
            posts[p["url"]] = {"source": "Community", "title": p["title"], "text": p["snippet"]}
    return posts


def run_demand(idea: StructuredIdea) -> DemandReport:
    posts = gather_posts(idea)

    # No data = say so honestly. Do not call the LLM and let it guess.
    if not posts:
        return DemandReport(demand_level="unclear", summary="No posts were found.",
                            pain_points=[], evidence=[],
                            limitations="Search tools returned no results.")

    # Turn posts into numbered plain text for the prompt
    text = "\n".join(
        f"- [{p['source']}] {p['title']} | {p['text']} | {url}" for url, p in posts.items()
    )
    idea_text = f"{idea.problem} | Customer: {idea.target_customer} | Solution: {idea.solution}"
    report = chain.invoke({"idea": idea_text, "posts": text})

    # Safety check: free models sometimes invent links. Keep only URLs we really found.
    report.evidence = [e for e in report.evidence if e.url in posts]
    return report