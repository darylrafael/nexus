import json
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any


ARTIFACT_ROOT = Path(__file__).parent.parent / "runs"


def _run_dir(date_key: str) -> Path:
    path = ARTIFACT_ROOT / date_key
    path.mkdir(parents=True, exist_ok=True)
    return path


def _json_ready(payload: Any) -> Any:
    if is_dataclass(payload):
        return asdict(payload)
    return payload


def save_json_artifact(date_key: str, filename: str, payload: Any) -> Path:
    path = _run_dir(date_key) / filename
    path.write_text(
        json.dumps(_json_ready(payload), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return path


def load_json_artifact(date_key: str, filename: str) -> Any | None:
    path = ARTIFACT_ROOT / date_key / filename
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def save_text_artifact(date_key: str, filename: str, content: str) -> Path:
    path = _run_dir(date_key) / filename
    path.write_text(content, encoding="utf-8")
    return path
