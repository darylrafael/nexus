def split_text(text: str, max_length: int = 4000) -> list[str]:
    """
    Split text into non-empty chunks adhering to max_length limit.
    Prefers splitting on paragraph boundaries ('\\n\\n'), then line boundaries ('\\n'),
    then word boundaries (' '), avoiding breaking words or markup mid-sentence.
    """
    if max_length < 1:
        raise ValueError("max_length must be positive")

    if not text:
        return []

    chunks = []
    remaining = text.strip()

    while remaining:
        if len(remaining) <= max_length:
            chunks.append(remaining)
            break

        # 1. Try paragraph break
        split_at = remaining.rfind("\n\n", 0, max_length + 1)
        # 2. Try single newline
        if split_at <= 0:
            split_at = remaining.rfind("\n", 0, max_length + 1)
        # 3. Try space/word boundary
        if split_at <= 0:
            split_at = remaining.rfind(" ", 0, max_length + 1)
        # 4. Hard cut
        if split_at <= 0:
            split_at = max_length

        chunk = remaining[:split_at].rstrip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_at:].lstrip("\n ")

    return chunks
