import urllib3
import requests
from datetime import datetime, timedelta
from config import OBSIDIAN_API_KEY, OBSIDIAN_BASE_URL
from core.time import jakarta_now

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

# Run-level circuit breaker: if Obsidian fails once, short-circuit remaining calls
# during the same process to eliminate latency and log noise.
_OBSIDIAN_UNREACHABLE = False


def reset_obsidian_status():
    """Reset the circuit breaker (e.g. for testing)."""
    global _OBSIDIAN_UNREACHABLE
    _OBSIDIAN_UNREACHABLE = False


def write_note(title: str, content: str) -> bool:
    """Best-effort note sync to Obsidian. Short-circuits if Obsidian is offline."""
    global _OBSIDIAN_UNREACHABLE
    if not OBSIDIAN_API_KEY or _OBSIDIAN_UNREACHABLE:
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
        _OBSIDIAN_UNREACHABLE = True
        print(f"  [obsidian] Offline/unreachable; skipping note sync for this run: {e}")
        return False


def read_note(title: str) -> str:
    """
    Read a specific note by its title (without .md extension).
    Returns raw markdown content, or empty string if not found or unreachable.
    """
    global _OBSIDIAN_UNREACHABLE
    if not OBSIDIAN_API_KEY or _OBSIDIAN_UNREACHABLE:
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
        _OBSIDIAN_UNREACHABLE = True
        print(f"  [obsidian] Offline/unreachable; skipping read_note: {e}")
        return ""


def read_recent_notes(days: int = 7) -> str:
    """
    Read recent Evening Review notes filtered by date.
    """
    global _OBSIDIAN_UNREACHABLE
    if not OBSIDIAN_API_KEY or _OBSIDIAN_UNREACHABLE:
        return ""
    cutoff = (jakarta_now() - timedelta(days=days)).strftime("%Y-%m-%d")

    try:
        response = requests.post(
            f"{BASE_URL}/search/simple/",
            headers=JSON_HEADERS,
            json={"query": "Evening Review", "contextLength": 100},
            verify=False,
            timeout=2
        )
        if response.status_code != 200:
            return ""

        results = response.json()
        filtered = []
        for r in results:
            filename = r.get("filename", "")
            basename = filename.replace("nexus/", "").replace(".md", "")
            date_part = basename[:10]
            if date_part >= cutoff:
                filtered.append((date_part, basename))

        filtered.sort(key=lambda x: x[0])

        notes = []
        for date_part, basename in filtered:
            full_content = read_note(basename)
            if full_content:
                notes.append(full_content)

        if not notes:
            return ""

        notes.reverse()
        return "\n\n---\n\n".join(notes)

    except Exception as e:
        _OBSIDIAN_UNREACHABLE = True
        print(f"  [obsidian] search failed: {e}")
        return ""