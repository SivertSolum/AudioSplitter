from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from splitter.changelog_sync import (
    EMPTY_UNRELEASED_BODY,
    bump_patch,
    extract_version_notes,
    next_release_version,
    prepare_release,
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


def test_bump_patch() -> None:
    assert bump_patch("0.1.0") == "0.1.1"
    assert bump_patch("0.1.9") == "0.1.10"


def test_next_release_version_bumps_latest_section() -> None:
    assert next_release_version(SAMPLE_UNRELEASED) == "0.1.1"


def test_prepare_release_updates_version_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    changelog = tmp_path / "CHANGELOG.md"
    pyproject = tmp_path / "pyproject.toml"
    init_py = tmp_path / "src" / "splitter" / "__init__.py"
    init_py.parent.mkdir(parents=True)

    changelog.write_text(SAMPLE_UNRELEASED, encoding="utf-8")
    pyproject.write_text('[project]\nversion = "0.1.0"\n', encoding="utf-8")
    init_py.write_text('__version__ = "0.1.0"\n', encoding="utf-8")

    monkeypatch.setattr("splitter.changelog_sync.CHANGELOG_PATH", changelog)
    monkeypatch.setattr("splitter.changelog_sync.PYPROJECT_PATH", pyproject)
    monkeypatch.setattr("splitter.changelog_sync.INIT_PATH", init_py)

    version = prepare_release(release_date=date(2026, 7, 16))
    assert version == "0.1.1"
    assert "## [0.1.1] - 2026-07-16" in changelog.read_text(encoding="utf-8")
    assert 'version = "0.1.1"' in pyproject.read_text(encoding="utf-8")
    assert '__version__ = "0.1.1"' in init_py.read_text(encoding="utf-8")


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
