"""Web research: collect numbered sources the slides can cite.

v1 pasted raw search snippets into the prompt and never showed where facts
came from. Now every source gets an id, the model cites ids, and the deck
ends with a Sources slide.
"""
from .schema import Source


def web_search(query: str, max_results: int = 6) -> list[dict]:
    from ddgs import DDGS
    with DDGS() as d:
        return list(d.text(query, max_results=max_results, safesearch="moderate"))


def research(topic: str, max_sources: int = 10, search=web_search) -> list[Source]:
    """Two searches: a general one, and one aimed at numbers (for stats/charts)."""
    queries = [topic, f"{topic} statistics data report"]
    seen, sources = set(), []
    for q in queries:
        try:
            results = search(q)
        except Exception:
            continue  # offline / rate-limited: the deck is still made, just without sources
        for r in results:
            url = r.get("href") or r.get("url") or ""
            if not url or url in seen or not r.get("body"):
                continue
            seen.add(url)
            sources.append(Source(id=len(sources) + 1, title=r.get("title", url)[:150],
                                  url=url, snippet=r["body"][:600]))
            if len(sources) >= max_sources:
                return sources
    return sources
