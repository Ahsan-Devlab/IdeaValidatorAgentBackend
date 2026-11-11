from tavily import TavilyClient
from app.config import settings


client = TavilyClient(api_key=settings.tavily_api_key)

COMMUNITY_SITES = ["reddit.com", "quora.com", "indiehackers.com", "stackexchange.com"]

def _search(query: str, domains: list[str] | None = None, limit: int = 5) -> list[dict]:
    try:
        res = client.search(
            query=query, 
            max_results=limit,
            search_depth = "basic",
            include_domains=domains or []
            )

    except Exception:
        return []

    return [
       {
            "title": r["title"],
            "url": r["url"],
            "snippet": r["content"][:300],  # cut text to save LLM tokens
        }
        for r in res.get("results", [])
    ]   

def search_community(query: str) -> list[dict]:
    # Real user complaints and requests (Reddit, Quora, Indie Hackers)
    return _search(query, COMMUNITY_SITES)


def search_web(query: str) -> list[dict]:
    # General search, used for competitors in the next steps
    return _search(query)