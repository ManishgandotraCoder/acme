"""Enforce the modular-monolith dependency rules (see docs/adr/0001-modular-monolith.md).

Fails CI when someone adds an undeclared dependency, turning coupling into a reviewed decision.
"""

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"

# Which other modules each module may import from. Everything may use core and shared.
ALLOWED_MODULE_DEPENDENCIES: dict[str, set[str]] = {
    "employees": set(),
    "insights": {"employees"},  # reads the Employee table
    "assistant": {"employees", "insights"},  # vocabulary + answers come from these
}


def _imports(package: Path) -> list[tuple[Path, str]]:
    found = []
    for file in package.rglob("*.py"):
        for node in ast.walk(ast.parse(file.read_text())):
            if isinstance(node, ast.ImportFrom) and node.module:
                found.append((file, node.module))
            elif isinstance(node, ast.Import):
                found.extend((file, alias.name) for alias in node.names)
    return found


@pytest.mark.parametrize("layer", ["core", "shared"])
def test_foundation_layers_never_depend_on_modules(layer):
    violations = [
        f"{file.relative_to(APP)} imports {name}"
        for file, name in _imports(APP / layer)
        if name.startswith("app.modules")
    ]
    assert violations == []


@pytest.mark.parametrize("module", sorted(ALLOWED_MODULE_DEPENDENCIES))
def test_modules_only_depend_on_declared_modules(module):
    allowed = ALLOWED_MODULE_DEPENDENCIES[module] | {module}
    violations = [
        f"{file.relative_to(APP)} imports {name}"
        for file, name in _imports(APP / "modules" / module)
        if name.startswith("app.modules.") and name.split(".")[2] not in allowed
    ]
    assert violations == []


def test_every_module_has_declared_dependencies():
    modules = {p.name for p in (APP / "modules").iterdir() if (p / "__init__.py").exists()}
    assert modules == set(ALLOWED_MODULE_DEPENDENCIES)
