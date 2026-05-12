"""Architecture guards for the clean proxy_service package layout."""

from __future__ import annotations

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = APP_ROOT / "src" / "proxy_service"
OLD_IMPORT_PREFIXES = ("control_plane", "pipeline", "red_team", "src")
SCAN_ROOTS = (
    APP_ROOT / "src",
    APP_ROOT / "tests",
    APP_ROOT / "scripts",
)

MOVED_MODULES = {
    "domain/firewall/pipeline/runner.py": "application/firewall/runner.py",
    "domain/red_team/api/routes.py": "interfaces/http/routers/benchmark.py",
    "domain/red_team/api/service.py": "application/red_team/service.py",
    "domain/red_team/api/__init__.py": "interfaces/http/schemas/benchmark.py",
    "domain/red_team/engine/worker.py": "application/red_team/worker.py",
    "domain/red_team/engine/adapters.py": "infrastructure/red_team/adapters.py",
    "domain/red_team/export/renderer.py": "infrastructure/red_team/export/renderer.py",
    "domain/red_team/persistence/models.py": "infrastructure/persistence/red_team/models.py",
    "domain/red_team/persistence/repository.py": "infrastructure/persistence/red_team/repository.py",
}


def _python_files(*roots: Path) -> list[Path]:
    files: list[Path] = []
    for root in roots:
        if root.exists():
            files.extend(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)
    return sorted(files)


def _absolute_imports(path: Path) -> list[tuple[int, str]]:
    tree = ast.parse(path.read_text(), filename=str(path))
    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.append((node.lineno, node.module))
    return imports


def test_no_stale_proxy_import_prefixes() -> None:
    violations: list[str] = []
    for path in _python_files(*SCAN_ROOTS):
        for lineno, module in _absolute_imports(path):
            root = module.split(".", 1)[0]
            if root in OLD_IMPORT_PREFIXES:
                rel = path.relative_to(APP_ROOT)
                violations.append(f"{rel}:{lineno} imports {module}")

    assert violations == []


def test_side_effectful_modules_stay_out_of_domain() -> None:
    missing_new: list[str] = []
    lingering_old: list[str] = []
    for old_path, new_path in MOVED_MODULES.items():
        if (SRC_ROOT / old_path).exists():
            lingering_old.append(old_path)
        if not (SRC_ROOT / new_path).is_file():
            missing_new.append(new_path)

    assert lingering_old == []
    assert missing_new == []


def test_red_team_domain_has_no_application_or_infrastructure_imports() -> None:
    domain_root = SRC_ROOT / "domain" / "red_team"
    forbidden_prefixes = (
        "proxy_service.application",
        "proxy_service.infrastructure",
        "proxy_service.interfaces",
    )
    violations: list[str] = []

    for path in _python_files(domain_root):
        for lineno, module in _absolute_imports(path):
            if module.startswith(forbidden_prefixes):
                rel = path.relative_to(APP_ROOT)
                violations.append(f"{rel}:{lineno} imports {module}")

    assert violations == []
