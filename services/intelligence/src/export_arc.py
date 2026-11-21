"""Export current backend arc artifacts. This command performs no inference."""

import argparse
import asyncio
import json
from pathlib import Path
from uuid import UUID

from src.application.arc_intelligence import article_markdown
from src.infrastructure.config.settings import get_settings
from src.infrastructure.persistence.database import create_database
from src.infrastructure.research_runtime import build_arc_intelligence


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", required=True, type=UUID)
    parser.add_argument("--continuity", required=True, type=UUID)
    parser.add_argument("--arc", required=True, type=UUID)
    parser.add_argument("--through", type=int)
    parser.add_argument("--allowed-source", action="append", type=UUID)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    engine, factory = create_database(get_settings().database_url)
    try:
        result = await build_arc_intelligence(factory).read(
            args.universe, args.continuity, args.arc, args.through, args.allowed_source
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(article_markdown(result), encoding="utf8")
        args.output.with_suffix(".json").write_text(
            json.dumps(result, indent=2, ensure_ascii=True), encoding="utf8"
        )
        print(f"Exported {result['status']} artifacts to {args.output}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
