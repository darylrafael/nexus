import urllib3
import requests
from datetime import datetime, timedelta
from config import OBSIDIAN_API_KEY, OBSIDIAN_BASE_URL

# Suppress self-signed certificate warnings for local Obsidian REST API
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    """Best-effort note sync to Obsidian. Never crashes pipeline if Obsidian is offline."""
    if not OBSIDIAN_API_KEY:
        return False
    try:
        filename = f"nexus/{title}.md"
        response = requests.put(
            f"{BASE_URL}/vault/{filename}",
            headers=HEADERS,
            data=content.encode("utf-8"),
            verify=False,
            timeout=2
        )
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"  [obsidian] Note sync skipped ({title}): {e}")
        return False


def read_note(title: str) -> str:
    """
    Read a specific note by its title (without .md extension).
    Path pattern: nexus/{title}.md
    Returns raw markdown content, or empty string if not found or unreachable.
    """
    if not OBSIDIAN_API_KEY:
        return ""
    try:
        filename = f"nexus/{title}.md"
        response = requests.get(
            f"{BASE_URL}/vault/{filename}",
            headers={"Authorization": f"Bearer {OBSIDIAN_API_KEY}"},
            verify=False,
            timeout=2
        )
        if response.status_code == 200:
            return response.text
        return ""
    except Exception as e:
        print(f"  [obsidian] read_note skipped ({title}): {e}")
        return ""


def read_recent_notes(days: int = 7) -> str:
    """
    Read recent Evening Review notes filtered by date.
    """
    if not OBSIDIAN_API_KEY:
        return ""
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        # Search for evening review notes
        response = requests.post(
            f"{BASE_URL}/search/simple/",
            headers=JSON_HEADERS,
            json={"query": "Evening Review", "contextLength": 100},
            verify=False,
            timeout=2
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