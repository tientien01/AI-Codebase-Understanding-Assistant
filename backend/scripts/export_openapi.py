from __future__ import annotations

import argparse
import difflib
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent
ARTIFACT_PATH = REPOSITORY_ROOT / "docs" / "06-api-and-integrations" / "artifacts" / "openapi-v1.json"

# Running this file directly places backend/scripts on sys.path. Add backend so
# the application is imported exactly as it is by the normal backend runtime.
sys.path.insert(0, str(BACKEND_ROOT))

from app.main import app  # noqa: E402  (path setup must happen before import)


def render_openapi() -> str:
    """Return a deterministic representation suitable for source control."""
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def write_artifact(content: str) -> int:
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(content, encoding="utf-8", newline="\n")
    print(f"Wrote {ARTIFACT_PATH.relative_to(REPOSITORY_ROOT)}")
    return 0


def check_artifact(content: str) -> int:
    if not ARTIFACT_PATH.exists():
        print(f"Missing OpenAPI artifact: {ARTIFACT_PATH.relative_to(REPOSITORY_ROOT)}", file=sys.stderr)
        return 1

    committed = ARTIFACT_PATH.read_text(encoding="utf-8")
    if committed == content:
        print("OpenAPI artifact is up to date.")
        return 0

    diff = difflib.unified_diff(
        committed.splitlines(),
        content.splitlines(),
        fromfile="committed/openapi-v1.json",
        tofile="generated/openapi-v1.json",
        lineterm="",
    )
    print("OpenAPI artifact drift detected. Run with --write only for an authorized contract change.", file=sys.stderr)
    for line_number, line in enumerate(diff):
        if line_number >= 200:
            print("... diff truncated after 200 lines", file=sys.stderr)
            break
        print(line, file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Export or verify the deterministic FastAPI OpenAPI artifact.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="Fail when generated OpenAPI differs from the artifact.")
    mode.add_argument("--write", action="store_true", help="Write the generated OpenAPI artifact.")
    args = parser.parse_args()

    content = render_openapi()
    return write_artifact(content) if args.write else check_artifact(content)


if __name__ == "__main__":
    raise SystemExit(main())
