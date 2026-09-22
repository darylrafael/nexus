import requests
from datetime import datetime, timedelta
from config import OBSIDIAN_API_KEY, OBSIDIAN_BASE_URL

BASE_URL = OBSIDIAN_BASE_URL

HEADERS = {
    "Authorization": f"Bearer {OBSIDIAN_API_KEY}",
    "Content-Type": "text/markdown"
}

JSON_HEADERS = {
    "Authorization": f"Bearer {OBSIDIAN_API_KEY}",
    "Content-Type": "application/json"
}


def write_note(title: str, content: str) -> bool:
    try:
        filename = f"nexus/{title}.md"
        response = requests.put(
            f"{BASE_URL}/vault/{filename}",
            headers=HEADERS,
            data=content.encode("utf-8"),
            verify=False
        )
        print(f"STATUS: {response.status_code}")
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"  [memory] write failed: {e}")
        return False


def read_note(title: str) -> str:
    """
    Read a specific note by its title (without .md extension).
    Path pattern: nexus/{title}.md
    Returns raw markdown content, or empty string if not found.
    """
    try:
        filename = f"nexus/{title}.md"
        response = requests.get(
            f"{BASE_URL}/vault/{filename}",
            headers={"Authorization": f"Bearer {OBSIDIAN_API_KEY}"},
            verify=False
        )
        if response.status_code == 200:
            return response.text
        print(f"  [memory] note not found: {filename} (status {response.status_code})")
        return ""
    except Exception as e:
        print(f"  [memory] read_note failed: {e}")
        return ""


def read_recent_notes(days: int = 7) -> str:
    """
    Read recent Evening Review notes filtered by date.
    
    FIX: Previously ignored `days` param and used contextLength=300
    which truncated JSON blocks → load_recent_learnings always returned [].
    
    Now:
    - Filters by date using filename prefix (YYYY-MM-DD format)
    - Fetches full note content via read_note(), not truncated snippets
    - Searches for "Evening Review" specifically (not generic "nexus")
    """
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        # Search for evening review notes
        response = requests.post(
            f"{BASE_URL}/search/simple/",
            headers=JSON_HEADERS,
            json={"query": "Evening Review", "contextLength": 100},
            verify=False
        )
        if response.status_code != 200:
            print(f"  [memory] search failed: status {response.status_code}")
            return ""

        results = response.json()
        # Collect and sort by date prefix so ordering is deterministic regardless
        # of what order Obsidian's search API returns results.
        filtered = []
        for r in results:
            filename = r.get("filename", "")
            basename = filename.replace("nexus/", "").replace(".md", "")
            date_part = basename[:10]  # "YYYY-MM-DD" — lexicographically sortable
            if date_part >= cutoff:
                filtered.append((date_part, basename))

        # Sort ascending so reverse() below gives most-recent-first
        filtered.sort(key=lambda x: x[0])

        notes = []
        for date_part, basename in filtered:
            full_content = read_note(basename)
            if full_content:
                print(f"  [memory] loaded: {basename}")
                notes.append(full_content)

        if not notes:
            print(f"  [memory] no Evening Review notes found in last {days} days")
            return ""

        # Most recent first
        notes.reverse()
        return "\n\n---\n\n".join(notes)

    except Exception as e:
        print(f"  [memory] read_recent_notes failed: {e}")
        return ""