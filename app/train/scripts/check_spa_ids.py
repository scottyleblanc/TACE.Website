"""
check_spa_ids.py -- static consistency check between the SPA's JavaScript and
its HTML.

There is no build step, no bundler and no test runner for this SPA, so a
renamed or mistyped element id fails silently in the browser: getElementById
returns null and the feature quietly stops working. This catches that class of
bug without needing a JS runtime installed.

Checks both directions:
  - every id the JS looks up exists in index.html
  - every id declared in index.html is referenced by the JS (stale markup)

Exits 0 if consistent, 1 otherwise. Intended for CI or a pre-deploy check.

Usage:
    python app/train/scripts/check_spa_ids.py
    python app/train/scripts/check_spa_ids.py --src app/train/src
"""

import argparse
import re
import sys
from pathlib import Path

# Ids the JS creates at runtime rather than reading from static markup, so they
# are legitimately absent from index.html.
RUNTIME_IDS = frozenset({"coach-thinking-bubble"})

# Ids rendered into innerHTML templates by the JS and then read back, so they
# are legitimately absent from index.html too.
JS_RENDERED_IDS = frozenset({
    "today-check", "today-notes", "save-notes-btn",
})

_GET_BY_ID = re.compile(r"""getElementById\(\s*['"]([^'"]+)['"]\s*\)""")
_HTML_ID = re.compile(r"""\sid\s*=\s*['"]([^'"]+)['"]""")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check SPA element-id consistency.")
    parser.add_argument(
        "--src",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "src",
        help="SPA source directory containing index.html and the JS",
    )
    args = parser.parse_args()

    html_path = args.src / "index.html"
    if not html_path.exists():
        print(f"[ERROR] not found: {html_path}", file=sys.stderr)
        return 1

    html_ids = set(_HTML_ID.findall(html_path.read_text(encoding="utf-8")))

    js_ids: dict[str, set[str]] = {}
    for js_path in sorted(args.src.glob("*.js")):
        for found in _GET_BY_ID.findall(js_path.read_text(encoding="utf-8")):
            js_ids.setdefault(found, set()).add(js_path.name)

    print(f"[INFO]  {html_path.name}: {len(html_ids)} id(s)")
    print(f"[INFO]  JS lookups: {len(js_ids)} distinct id(s)")

    known = RUNTIME_IDS | JS_RENDERED_IDS
    missing = {i: s for i, s in js_ids.items() if i not in html_ids and i not in known}
    unused = html_ids - set(js_ids) - known

    ok = True
    if missing:
        ok = False
        print(f"\n[FAIL]  {len(missing)} id(s) looked up in JS but absent from index.html:", file=sys.stderr)
        for element_id, sources in sorted(missing.items()):
            print(f"          {element_id}  (referenced in {', '.join(sorted(sources))})", file=sys.stderr)
    else:
        print("[OK]    every id the JS looks up exists in index.html")

    if unused:
        # Stale markup is a warning, not a failure -- an id can legitimately be
        # styling-only or reserved for markup not yet wired up.
        print(f"\n[WARN]  {len(unused)} id(s) in index.html never looked up by JS: {sorted(unused)}")
    else:
        print("[OK]    no unreferenced ids in index.html")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
