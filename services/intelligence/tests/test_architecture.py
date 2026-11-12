import ast
from pathlib import Path


def test_inner_layers_do_not_import_outer_layers():
    root = Path(__file__).parents[1] / "src"
    for layer in ("domain", "application"):
        forbidden = ("fastapi", "sqlalchemy", "src.infrastructure", "src.presentation")
        if layer == "domain":
            forbidden += ("src.application", "pydantic")
        for source in (root / layer).rglob("*.py"):
            for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom):
                    names = [node.module or ""]
                assert not any(name.startswith(forbidden) for name in names), source
