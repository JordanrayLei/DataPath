from __future__ import annotations

import json
import zipfile
from pathlib import Path

from scripts.download_olist import EXPECTED_FILES, safe_extract
from scripts.load_olist import FILE_TABLES


def test_olist_file_mapping_covers_expected_archive() -> None:
    assert set(FILE_TABLES) == EXPECTED_FILES
    assert len(FILE_TABLES) == 9


def test_olist_archive_extraction_ignores_unexpected_files(tmp_path) -> None:
    archive = tmp_path / "olist.zip"
    output = tmp_path / "output"
    with zipfile.ZipFile(archive, "w") as target:
        for filename in EXPECTED_FILES:
            target.writestr(filename, "header\n")
        target.writestr("../unexpected.txt", "not extracted")
    safe_extract(archive, output)
    assert {path.name for path in output.iterdir()} == EXPECTED_FILES
    assert not (tmp_path / "unexpected.txt").exists()


def test_olist_relationship_contract_marks_fanout_paths() -> None:
    contract = json.loads(
        (Path(__file__).parents[1] / "data/external/olist/relationships.json").read_text(
            encoding="utf-8"
        )
    )
    statuses = {item["status"] for item in contract["join_paths"]}
    assert "aggregate_before_join" in statuses
    assert "aggregate_geolocation_before_join" in statuses
