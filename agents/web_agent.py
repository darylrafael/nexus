import hashlib
from datetime import datetime, timedelta

from config import TAVILY_API_KEY
from schemas import SourceRecord

client = None
_SOURCE_REGISTRY = {}
_SEARCH_CACHE: dict[str, dict] = {}
_SEARCH_METRICS = {
    "api_calls": 0,
    "cache_hits": 0,
    "total_queries": 0,
}
SEARCH_CACHE_TTL_SECONDS = 1800  # 30 minutes


def get_source_registry() -> dict:
    return _SOURCE_REGISTRY.copy()


def clear_source_registry() -> None:
    _SOURCE_REGISTRY.clear()


def get_search_metrics() -> dict:
    """Return metrics on Tavily API calls and cache hits."""
    return _SEARCH_METRICS.copy()


def clear_search_cache() -> None:
    """Clear cached search results and reset registry and metrics."""
    _SEARCH_CACHE.clear()
    _SEARCH_METRICS["api_calls"] = 0
    _SEARCH_METRICS["cache_hits"] = 0
    _SEARCH_METRICS["total_queries"] = 0


def _get_client():
    global client
    if client is None:
        from tavily import TavilyClient
        client = TavilyClient(api_key=TAVILY_API_KEY)
    return client


def _source_id(url: str, title: str) -> str:
    raw = f"{url}|{title}".encode("utf-8", errors="ignore")
    return f"src_{hashlib.sha1(raw).hexdigest()[:10]}"


def _compute_cache_key(query: str, days: int, max_results: int) -> str:
    normalized = query.strip().lower()
    raw = f"{normalized}|{days}|{max_results}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def search_web_records(
    query: str,
    days: int = 1,
    category: str = "web",
    max_results: int = 7,
) -> list[SourceRecord]:
    _SEARCH_METRICS["total_queries"] += 1
    cache_key = _compute_cache_key(query, days, max_results)
    now = datetime.now()

    # 1. Check TTL cache for identical queries within the session
    if cache_key in _SEARCH_CACHE:
        entry = _SEARCH_CACHE[cache_key]
        if (now - entry["timestamp"]).total_seconds() < SEARCH_CACHE_TTL_SECONDS:
            _SEARCH_METRICS["cache_hits"] += 1
            # Return fresh copies with requested category
            cached_records = []
            for r in entry["records"]:
                _SOURCE_REGISTRY[r.id] = {
                    "title": r.title,
                    "url": r.url,
                    "published_at": r.published_at,
                    "category": category,
                }
                cached_records.append(SourceRecord(
                    id=r.id,
                    category=category,
                    title=r.title,
                    url=r.url,
                    published_at=r.published_at,
                    retrieved_at=r.retrieved_at,
                    summary=r.summary,
                    freshness_days=r.freshness_days,
                ))
            return cached_records

    # 2. Cache miss -> perform live API call
    _SEARCH_METRICS["api_calls"] += 1
    results = _get_client().search(query, max_results=max_results, days=days)
    cutoff = datetime.now() - timedelta(days=days)
    retrieved_at = datetime.now().isoformat(timespec="seconds")
    records = []

    for result in results.get("results", []):
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
        sid = _source_id(url, title)
        _SOURCE_REGISTRY[sid] = {
            "title": title,
            "url": url,
            "published_at": pub or None,
            "category": category,
        }
        records.append(SourceRecord(
            id=sid,
            category=category,
            title=title,
            url=url,
            published_at=pub or None,
            retrieved_at=retrieved_at,
            summary=result.get("content", ""),
            freshness_days=freshness_days,
        ))

    # Store in cache
    _SEARCH_CACHE[cache_key] = {
        "timestamp": now,
        "records": records,
    }

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
    try:
        records = search_web_records(query, days=days)
        output = format_source_records(records)
        return output if output else "No fresh results found for today."
    except Exception as e:
        print(f"  [web_agent] search_web error: {e}")
        return f"Search data temporarily unavailable: {e}"


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
