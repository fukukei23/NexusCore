import sys, tomllib
from pathlib import Path

p = Path("pyproject.toml")
if not p.exists():
    print("[info] pyproject.toml: not found at repo root")
    sys.exit(0)

data = tomllib.loads(p.read_text(encoding="utf-8"))

def section(title, items):
    print(f"\n# {title}")
    if not items:
        print("(empty)")
    else:
        for x in sorted(items):
            print(x)

proj_deps = []
poetry_deps = []
opt_groups = {}

# PEP 621
proj_deps = list(data.get("project", {}).get("dependencies", []) or [])

# Poetry
for k, v in (data.get("tool", {}).get("poetry", {}).get("dependencies", {}) or {}).items():
    if k.lower() == "python":
        continue
    if isinstance(v, str):
        poetry_deps.append(f"{k} {v}")
    elif isinstance(v, dict):
        vers = v.get("version", "")
        extras = v.get("extras", [])
        poetry_deps.append(f"{k}{'['+','.join(extras)+']' if extras else ''} {vers}")

# optional-dependencies (PEP 621)
opt_groups = data.get("project", {}).get("optional-dependencies", {}) or {}

print(f"[info] Loaded: {p.resolve()}")
section("project.dependencies", proj_deps)
section("tool.poetry.dependencies", poetry_deps)
for grp, lst in opt_groups.items():
    section(f"optional-dependencies.{grp}", lst)
