"""Architecture guards for the clean agent_runtime package layout."""

from __future__ import annotations

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
OLD_IMPORT_PREFIXES = ("agent", "src")
SCAN_ROOTS = (
    APP_ROOT / "src",
    APP_ROOT / "tests",
)


def _python_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
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


def test_no_stale_agent_import_prefixes() -> None:
    violations: list[str] = []
    for path in _python_files():
        for lineno, module in _absolute_imports(path):
            root = module.split(".", 1)[0]
            if root in OLD_IMPORT_PREFIXES:
                rel = path.relative_to(APP_ROOT)
                violations.append(f"{rel}:{lineno} imports {module}")

    assert violations == []


def test_old_agent_package_removed() -> None:
    assert not (APP_ROOT / "src" / "agent").exists()
    assert (APP_ROOT / "src" / "agent_runtime").is_dir()
