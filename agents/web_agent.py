import hashlib
from datetime import datetime, timedelta

from config import TAVILY_API_KEY
from schemas import SourceRecord

client = None


def _get_client():
    global client
    if client is None:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
    return client


def _source_id(url: str, title: str) -> str:
    raw = f"{url}|{title}".encode("utf-8", errors="ignore")
    return f"src_{hashlib.sha1(raw).hexdigest()[:10]}"


def search_web_records(
    query: str,
    days: int = 1,
    category: str = "web",
    max_results: int = 7,
) -> list[SourceRecord]:
    results = _get_client().search(query, max_results=max_results, days=days)
    cutoff = datetime.now() - timedelta(days=days)
    retrieved_at = datetime.now().isoformat(timespec="seconds")
    records = []

    for result in results["results"]:
        pub = result.get("published_date", "")
        freshness_days = None
        try:
            pub_date = datetime.fromisoformat(pub.replace("Z", "+00:00").replace("+00:00", ""))
            pub_date = pub_date.replace(tzinfo=None)
            freshness_days = max((datetime.now() - pub_date).days, 0)
            if pub_date < cutoff:
                continue
        except Exception:
            pass

        title = result.get("title", "")
        url = result.get("url", "")
        records.append(SourceRecord(
            id=_source_id(url, title),
            category=category,
            title=title,
            url=url,
            published_at=pub or None,
            retrieved_at=retrieved_at,
            summary=result.get("content", ""),
            freshness_days=freshness_days,
        ))

    return records


def format_source_records(records: list[SourceRecord]) -> str:
    output = []
    for record in records:
        output.append(
            f"[{record.published_at or 'no date'}] {record.title}\n"
            f"{record.summary}\n"
            f"Source: {record.url}\n"
            f"Source ID: {record.id}\n"
        )
    return "\n".join(output)


def search_web(query: str, days: int = 1) -> str:
    records = search_web_records(query, days=days)
    output = format_source_records(records)
    return output if output else "No fresh results found for today."


import concurrent.futures

def search_multiple(queries: dict, days: int = 1) -> dict:
    results = {}
    
    def fetch(category, query):
        print(f"  [web_agent] searching: {category}")
        try:
            records = search_web_records(query, days=days, category=category)
            fmt = format_source_records(records)
            return category, fmt if fmt else "No fresh results found for today."
        except Exception as e:
            return category, f"Search failed: {e}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch, cat, q) for cat, q in queries.items()]
        for future in concurrent.futures.as_completed(futures):
            cat, res = future.result()
            results[cat] = res

    return results
