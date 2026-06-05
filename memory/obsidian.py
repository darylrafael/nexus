import requests
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
    try:
        response = requests.post(
            f"{BASE_URL}/search/simple/",
            headers=JSON_HEADERS,
            json={"query": "nexus", "contextLength": 300},
            verify=False
        )
        if response.status_code != 200:
            return ""
        results = response.json()
        notes = []
        for r in results[:5]:
            notes.append(f"### {r.get('filename', '')}\n{r.get('context', '')}")
        return "\n\n".join(notes)
    except Exception as e:
        print(f"  [memory] read failed: {e}")
        return ""