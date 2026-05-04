from pathlib import Path
from typing import Any
import yaml

_DIR = Path(__file__).parent

def _load_prompt(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return {"template": text}
        
    end = text.find("\n---\n", 4)
    if end == -1:
        return {"template": text}
        
    meta = yaml.safe_load(text[4:end]) or {}
    template = text[end + 5:]
    return {**meta, "template": template}

def get_prompt(name: str, arguments: dict[str, Any] | None = None) -> dict | None:
    path = _DIR / f"{name}.md"
    if not path.exists():
        return None
        
    info = _load_prompt(path)
    args = arguments or {}
    
    # Optional logic for setting default values for specific prompts like previously
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
            
    elif name == "dos_calculation":
        args.setdefault("spin_polarized", False)
        
    elif name == "geometry_optimization":
        args.setdefault("optimize_cell", False)
        
    elif name == "convergence_test":
        args.setdefault("parameter", "both")
        
    elif name == "surface_calculation":
        args.setdefault("layers", 6)
        
    elif name == "magnetic_calculation":
        args.setdefault("configuration", "ferromagnetic")

    try:
        text = info["template"].format(**args)
    except KeyError:
        text = info["template"]
        
    return {"messages": [{"role": "user", "content": {"type": "text", "text": text.strip()}}]}

def list_prompts() -> list[dict]:
    results = []
    for p in sorted(_DIR.glob("*.md")):
        info = _load_prompt(p)
        results.append({
            "name": p.stem,
            "description": info.get("description", ""),
            "arguments": info.get("arguments", []),
        })
    return results

__all__ = ["get_prompt", "list_prompts"]
