def split_text(text: str, max_length: int) -> list[str]:
    """Split text into non-empty chunks, preferring line boundaries."""
    if max_length < 1:
        raise ValueError("max_length must be positive")

    chunks = []
    remaining = text.strip()
    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break
        split_at = remaining.rfind("\n", 0, max_length + 1)
        if split_at <= 0:
            split_at = max_length
        chunks.append(remaining[:split_at].rstrip())
        remaining = remaining[split_at:].lstrip("\n")
    return chunks
