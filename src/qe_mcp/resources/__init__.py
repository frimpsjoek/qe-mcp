from pathlib import Path
import yaml

_DIR = Path(__file__).parent

def _uri_to_path(uri: str) -> Path:
    # "qe://docs/pw" → _DIR / "docs/pw.md"
    _, rest = uri.split("://", 1)
    return _DIR / f"{rest}.md"

def _parse_md(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    meta = yaml.safe_load(text[4:end]) or {}
    return meta, text[end + 5:]

def get_resource(uri: str) -> dict | None:
    path = _uri_to_path(uri)
    if not path.exists():
        return None
    meta, body = _parse_md(path)
    return {
        "uri": uri,
        "name": meta.get("name", path.stem),
        "mimeType": "text/markdown",
        "text": body.strip(),
    }

def list_resources() -> list[dict]:
    results = []
    for subdir in ("docs", "llm"):
        subdir_path = _DIR / subdir
        if not subdir_path.exists():
            continue
        for md in sorted(subdir_path.glob("*.md")):
            meta, _ = _parse_md(md)
            uri = f"qe://{subdir}/{md.stem}"
            results.append({
                "uri": uri,
                "name": meta.get("name", md.stem),
                "description": meta.get("description", ""),
                "mimeType": "text/markdown",
            })
    return results

__all__ = ["get_resource", "list_resources"]
