import httpx

HN_URL = "https://hn.algolia.com/api/v1/search"

def search_hackernews(query: str, limit: int = 5) -> list[dict]:
    try:
        r = httpx.get(
                HN_URL,
                params={"query": query, "tags": "story", "hitsPerPage": limit},
                timeout=10,   # never let a slow API freeze our app
            )
        r.raise_for_status()
        hits = r.json()["hits"]
    except Exception as e:
        print(f"Error searching Hacker News: {e}")
        return []
    return [
        {
            "title": h.get("title"),
            "points": h.get("points", 0),           # upvotes = interest level
            "comments": h.get("num_comments", 0),   # comments = discussion level
            "url": f"https://news.ycombinator.com/item?id={h['objectID']}",
        }
        for h in hits
    ]
