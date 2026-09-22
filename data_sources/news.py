from agents.web_agent import format_source_records, search_web_records


def _limit_text_preserving_source_ids(text: str, source_ids: list[str], limit_chars: int | None) -> str:
    if limit_chars is None or len(text) <= limit_chars:
        return text

    suffix = "\nSource IDs: " + ", ".join(source_ids) if source_ids else ""
    body_limit = max(limit_chars - len(suffix), 0)
    return text[:body_limit].rstrip() + suffix


def search_text_with_sources(
    query: str,
    days: int = 1,
    category: str = "web",
    max_results: int = 7,
    limit_chars: int | None = None,
) -> tuple[str, list[str]]:
    records = search_web_records(
        query,
        days=days,
        category=category,
        max_results=max_results,
    )
    text = format_source_records(records)
    if not text:
        text = "No fresh results found for today."
    source_ids = [record.id for record in records]
    text = _limit_text_preserving_source_ids(text, source_ids, limit_chars)
    return text, source_ids
