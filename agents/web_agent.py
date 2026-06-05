from tavily import TavilyClient
from config import TAVILY_API_KEY
from datetime import datetime, timedelta

client = TavilyClient(api_key=TAVILY_API_KEY)

def search_web(query: str, days: int = 1) -> str:
    results = client.search(query, max_results=7, days=days)
    cutoff = datetime.now() - timedelta(days=days)
    output = []
    for r in results["results"]:
        pub = r.get("published_date", "")
        try:
            pub_date = datetime.fromisoformat(pub.replace("Z", "+00:00").replace("+00:00", ""))
            pub_date = pub_date.replace(tzinfo=None)
            if pub_date < cutoff:
                continue  # Skip old articles
        except:
            pass  # If no date, include it
        output.append(f"[{pub}] {r['title']}\n{r['content']}\nSource: {r['url']}\n")
    return "\n".join(output) if output else "No fresh results found for today."

def search_multiple(queries: dict, days: int = 1) -> dict:
    results = {}
    for category, query in queries.items():
        print(f"  [web_agent] searching: {category}")
        try:
            results[category] = search_web(query, days=days)
        except Exception as e:
            results[category] = f"Search failed: {e}"
    return results
