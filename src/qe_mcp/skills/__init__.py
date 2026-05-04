from pathlib import Path
from typing import Any
import yaml

_DIR = Path(__file__).parent


def _load_skill(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {"template": text}

    end = text.find("\n---\n", 4)
    if end == -1:
        return {"template": text}

    meta = yaml.safe_load(text[4:end]) or {}
    template = text[end + 5:]
    return {**meta, "template": template}


def get_skill(name: str, arguments: dict[str, Any] | None = None) -> dict | None:
    path = _DIR / f"{name}.md"
    if not path.exists():
        return None

    info = _load_skill(path)
    args = arguments or {}

    if name == "band_structure":
        accuracy = args.get("accuracy", "medium")
        if accuracy == "low":
            args.setdefault("ecutwfc", 40)
            args.setdefault("npoints", 50)
        elif accuracy == "high":
            args.setdefault("ecutwfc", 80)
            args.setdefault("npoints", 150)
        else:
            args.setdefault("ecutwfc", 60)
            args.setdefault("npoints", 100)

    elif name == "dos":
        args.setdefault("spin_polarized", False)

    elif name == "relax":
        args.setdefault("optimize_cell", False)

    elif name == "convergence":
        args.setdefault("parameter", "both")

    elif name == "magnetic":
        args.setdefault("configuration", "ferromagnetic")

    elif name == "status":
        args.setdefault("job_ids", "")

    try:
        text = info["template"].format(**args)
    except KeyError:
        text = info["template"]

    return {"messages": [{"role": "user", "content": {"type": "text", "text": text.strip()}}]}


def list_skills() -> list[dict]:
    results = []
    for p in sorted(_DIR.glob("*.md")):
        info = _load_skill(p)
        results.append({
            "name": p.stem,
            "description": info.get("description", ""),
            "arguments": info.get("arguments", []),
        })
    return results


__all__ = ["get_skill", "list_skills"]
