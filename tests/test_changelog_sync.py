from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from splitter.changelog_sync import (
    EMPTY_UNRELEASED_BODY,
    extract_version_notes,
    promote_unreleased,
    section_has_entries,
)


SAMPLE_PREAMBLE = "# Changelog\n\nIntro text.\n\n"
SAMPLE_UNRELEASED = f"""{SAMPLE_PREAMBLE}## [Unreleased]

### Added

- New desktop feature

### Changed

### Fixed

### Removed

## [0.1.0] - 2026-07-04

### Added

- Initial release

"""


def test_section_has_entries() -> None:
    assert section_has_entries("- item\n")
    assert not section_has_entries("### Added\n\n")


def test_promote_unreleased_creates_version_section(tmp_path: Path) -> None:
    updated, changed = promote_unreleased(SAMPLE_UNRELEASED, "0.2.0", release_date=date(2026, 7, 15))
    assert changed is True
    assert "## [0.2.0] - 2026-07-15" in updated
    assert "- New desktop feature" in updated
    assert "## [Unreleased]" in updated
    assert EMPTY_UNRELEASED_BODY.strip() in updated
    assert updated.index("## [Unreleased]") < updated.index("## [0.2.0]")


def test_promote_unreleased_is_noop_when_section_exists() -> None:
    updated, changed = promote_unreleased(SAMPLE_UNRELEASED, "0.1.0")
    assert changed is False
    assert updated == SAMPLE_UNRELEASED


def test_extract_version_notes() -> None:
    notes = extract_version_notes(SAMPLE_UNRELEASED, "0.1.0")
    assert "- Initial release" in notes
