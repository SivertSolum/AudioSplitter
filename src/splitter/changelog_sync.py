from __future__ import annotations

import argparse
import re
import tomllib
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CHANGELOG_PATH = PROJECT_ROOT / "CHANGELOG.md"
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"

UNRELEASED_HEADING = "## [Unreleased]"
SECTION_HEADING = re.compile(r"^## \[([^\]]+)\]")
EMPTY_UNRELEASED_BODY = """### Added

### Changed

### Fixed

### Removed

"""


def read_version() -> str:
    data = tomllib.loads(PYPROJECT_PATH.read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def parse_ordered_sections(text: str) -> tuple[str, list[tuple[str, str]]]:
    lines = text.splitlines()
    first_section_index = next(
        (index for index, line in enumerate(lines) if SECTION_HEADING.match(line)),
        len(lines),
    )
    preamble = "\n".join(lines[:first_section_index]).rstrip() + "\n\n"
    ordered: list[tuple[str, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in lines[first_section_index:]:
        match = SECTION_HEADING.match(line)
        if match:
            if current_heading is not None:
                ordered.append((current_heading, "\n".join(current_lines).rstrip() + "\n"))
            current_heading = line.strip()
            current_lines = []
            continue
        if current_heading is not None:
            current_lines.append(line)

    if current_heading is not None:
        ordered.append((current_heading, "\n".join(current_lines).rstrip() + "\n"))

    return preamble, ordered


def render_changelog(preamble: str, ordered_sections: list[tuple[str, str]]) -> str:
    parts = [preamble.rstrip(), ""]
    for heading, body in ordered_sections:
        parts.append(heading)
        if body.strip():
            parts.append(body.rstrip())
        parts.append("")
    return "\n".join(parts).rstrip() + "\n"


def section_has_entries(body: str) -> bool:
    return any(line.startswith("- ") for line in body.splitlines())


def extract_version_notes(text: str, version: str) -> str:
    _, ordered = parse_ordered_sections(text)
    target_prefix = f"## [{version}]"
    for heading, body in ordered:
        if heading.startswith(target_prefix):
            return body.strip()
    return ""


def promote_unreleased(text: str, version: str, release_date: date | None = None) -> tuple[str, bool]:
    release_date = release_date or date.today()
    preamble, ordered = parse_ordered_sections(text)

    unreleased_body = ""
    version_exists = False
    for heading, body in ordered:
        if heading == UNRELEASED_HEADING:
            unreleased_body = body
        elif heading.startswith(f"## [{version}]"):
            version_exists = True

    if version_exists:
        normalized = text if text.endswith("\n") else text + "\n"
        return normalized, False

    if not section_has_entries(unreleased_body):
        raise SystemExit(
            f"No changelog section exists for [{version}] and [Unreleased] has no bullet entries. "
            "Add release notes under [Unreleased] before bumping the version in pyproject.toml."
        )

    promoted_heading = f"## [{version}] - {release_date.isoformat()}"
    rebuilt: list[tuple[str, str]] = []

    for heading, body in ordered:
        if heading == UNRELEASED_HEADING:
            rebuilt.append((UNRELEASED_HEADING, EMPTY_UNRELEASED_BODY))
            rebuilt.append((promoted_heading, unreleased_body))
        else:
            rebuilt.append((heading, body))

    return render_changelog(preamble, rebuilt), True


def sync_changelog(
    *,
    promote: bool = False,
    extract_path: Path | None = None,
    version: str | None = None,
) -> bool:
    """Promote unreleased notes and/or extract release notes. Returns True if changelog was modified."""
    resolved_version = version or read_version()
    changelog_text = CHANGELOG_PATH.read_text(encoding="utf-8")
    changed = False

    if promote:
        updated, promoted = promote_unreleased(changelog_text, resolved_version)
        if promoted:
            CHANGELOG_PATH.write_text(updated, encoding="utf-8")
            changed = True
            changelog_text = updated

    if extract_path is not None:
        notes = extract_version_notes(changelog_text, resolved_version)
        if not notes:
            raise SystemExit(
                f"Could not extract release notes for version [{resolved_version}] from CHANGELOG.md."
            )
        extract_path.write_text(notes + "\n", encoding="utf-8")

    return changed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Promote and extract Keep a Changelog sections for CI.")
    parser.add_argument(
        "--promote",
        action="store_true",
        help="Create ## [version] from [Unreleased] when the version section is missing.",
    )
    parser.add_argument(
        "--extract",
        metavar="FILE",
        help="Write release notes for the current pyproject version to FILE.",
    )
    parser.add_argument("--version", help="Override version read from pyproject.toml.")
    args = parser.parse_args(argv)

    if not args.promote and not args.extract:
        parser.error("Specify --promote and/or --extract.")

    changed = sync_changelog(
        promote=args.promote,
        extract_path=Path(args.extract) if args.extract else None,
        version=args.version,
    )

    if args.promote and not changed:
        version = args.version or read_version()
        print(f"Changelog section ## [{version}] already exists; no promotion needed.")
    elif args.promote:
        version = args.version or read_version()
        print(f"Promoted [Unreleased] to ## [{version}] in CHANGELOG.md")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
