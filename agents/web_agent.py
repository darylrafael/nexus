import hashlib
from datetime import datetime, timedelta
from urllib.parse import urlparse

from config import TAVILY_API_KEY
from schemas import SourceRecord
from core.time import jakarta_now

client = None
_SOURCE_REGISTRY = {}
_SEARCH_CACHE: dict[str, dict] = {}
_SEARCH_METRICS = {
    "api_calls": 0,
    "cache_hits": 0,
    "total_queries": 0,
}
SEARCH_CACHE_TTL_SECONDS = 1800  # 30 minutes

DEFAULT_DOMAIN_DENYLIST = [
    "tiktok.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "threads.net",
    "youtube.com",
    "reddit.com",
]


def is_domain_allowed(url: str, denylist: list[str] = None) -> bool:
    """Filter out social media and low-credibility platforms."""
    if not url:
        return True
    try:
        domain = urlparse(url).netloc.lower()
        if not domain:
            return True
        deny = denylist if denylist is not None else DEFAULT_DOMAIN_DENYLIST
        for blocked in deny:
            if domain == blocked or domain.endswith("." + blocked):
                return False
        return True
    except Exception:
        return True


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
    now = jakarta_now()

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
    client = _get_client()
    try:
        results = client.search(query, max_results=max_results, days=days, topic="news")
    except TypeError:
        results = client.search(query, max_results=max_results, days=days)

    cutoff = now - timedelta(days=days)
    retrieved_at = now.isoformat(timespec="seconds")
    records = []

    for result in results.get("results", []):
        url = result.get("url", "")
        if not is_domain_allowed(url):
            continue

        pub = result.get("published_date", "")
        freshness_days = None
        freshness_status = "fresh"

        if not pub:
            freshness_status = "unknown"
        else:
            try:
                pub_date = datetime.fromisoformat(pub.replace("Z", "+00:00").replace("+00:00", ""))
                pub_date = pub_date.replace(tzinfo=None)
                freshness_days = max((now.replace(tzinfo=None) - pub_date).days, 0)
                if pub_date < cutoff.replace(tzinfo=None):
                    freshness_status = "stale"
                    continue
            except Exception:
                freshness_status = "unknown"

        title = result.get("title", "")
        sid = _source_id(url, title)
        _SOURCE_REGISTRY[sid] = {
            "title": title,
            "url": url,
            "published_at": pub or None,
            "category": category,
            "freshness_status": freshness_status,
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
            freshness_status=freshness_status,
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
        freshness_label = f"freshness: {record.freshness_status}" if record.freshness_status != "fresh" else f"{record.freshness_days}d ago"
        date_display = record.published_at if record.published_at else "date unknown"
        output.append(
            f"[{date_display} | {freshness_label}] {record.title}\n"
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
