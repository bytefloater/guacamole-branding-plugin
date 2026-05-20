#!/usr/bin/env python3
"""Validate guac-manifest.json: all declared files exist on disk, and every
url("app/ext/branding/...") reference in CSS is on disk and in manifest resources."""

import json
import re
import sys
from pathlib import Path

BRANDING_DIR = Path(__file__).parent.parent / "branding"
MANIFEST_PATH = BRANDING_DIR / "guac-manifest.json"
RESOURCE_PREFIX = "app/ext/branding/"

URL_PATTERN = re.compile(
    r'url\(\s*["\']?(app/ext/branding/[^"\')\s]+)["\']?\s*\)'
)


def main() -> None:
    errors: list[str] = []

    with MANIFEST_PATH.open() as fh:
        manifest = json.load(fh)

    resource_keys: set[str] = set(manifest.get("resources", {}).keys())

    # Verify all manifest-declared files exist on disk
    for section in ("css", "js", "translations"):
        for rel_path in manifest.get(section, []):
            if not (BRANDING_DIR / rel_path).exists():
                errors.append(f"manifest.{section}: missing '{rel_path}'")

    for rel_path in resource_keys:
        if not (BRANDING_DIR / rel_path).exists():
            errors.append(f"manifest.resources: missing '{rel_path}'")

    # Scan CSS files for url() references to branding resources
    for css_rel in manifest.get("css", []):
        css_path = BRANDING_DIR / css_rel
        if not css_path.exists():
            continue  # already reported above

        for match in URL_PATTERN.finditer(css_path.read_text(encoding="utf-8")):
            full_url = match.group(1)
            resource_rel = full_url.removeprefix(RESOURCE_PREFIX)

            if not (BRANDING_DIR / resource_rel).exists():
                errors.append(f"{css_rel}: url '{resource_rel}' not found on disk")
            elif resource_rel not in resource_keys:
                errors.append(
                    f"{css_rel}: url '{resource_rel}' not declared in manifest resources"
                )

    if errors:
        for e in errors:
            print(f"ERROR: {e}", file=sys.stderr)
        print(f"\n{len(errors)} error(s) found.", file=sys.stderr)
        sys.exit(1)

    css_count = len(manifest.get("css", []))
    print(f"OK — manifest verified, {css_count} CSS file(s) scanned.")


if __name__ == "__main__":
    main()
