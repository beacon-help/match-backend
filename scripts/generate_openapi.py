from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate OpenAPI JSON for the Match API.")
    parser.add_argument(
        "--output",
        default="openapi.json",
        help="Path to write the generated OpenAPI JSON.",
    )
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    from match.main import create_app
    app = create_app()

    openapi_spec = app.openapi()
    output_path.write_text(json.dumps(openapi_spec, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
