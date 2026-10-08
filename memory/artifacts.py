import json
import os
import uuid
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


def atomic_write_file(target_path: Path, content: str) -> Path:
    """
    Atomically write content to target_path via temporary file and os.replace.
    Guarantees no partial or corrupted file reads by concurrent processes (like Next.js dashboard).
    """
    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_name(f".tmp_{target_path.name}_{os.getpid()}_{uuid.uuid4().hex[:6]}")
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, target_path)
    except Exception:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass
        raise
    return target_path


def save_json_artifact(date_key: str, filename: str, payload: Any) -> Path:
    path = _run_dir(date_key) / filename
    content = json.dumps(_json_ready(payload), ensure_ascii=False, indent=2)
    return atomic_write_file(path, content)


def load_json_artifact(date_key: str, filename: str) -> Any | None:
    path = ARTIFACT_ROOT / date_key / filename
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        # Artifacts are a resilience layer; a partial write must not abort a run.
        print(f"  [artifacts] skipped unreadable JSON artifact {path.name}: {exc}")
        return None


def save_text_artifact(date_key: str, filename: str, content: str) -> Path:
    path = _run_dir(date_key) / filename
    return atomic_write_file(path, content)
