import importlib.util
import sqlite3
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location("relocation", Path(__file__).resolve().parents[2] / "scripts/relocate_upload_paths.py")
relocation = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relocation)


def create_database(tmp_path):
    database = tmp_path / "copy.sqlite3"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE documents (id TEXT, original_file_path TEXT)")
        connection.execute("INSERT INTO documents VALUES (?, ?)", ("doc", "/old/uploads/source.txt"))
    new_root = tmp_path / "uploads"
    new_root.mkdir()
    (new_root / "source.txt").write_text("synthetic source")
    return database, new_root


def stored_path(database):
    with sqlite3.connect(database) as connection:
        return connection.execute("SELECT original_file_path FROM documents").fetchone()[0]


def test_dry_run_does_not_modify_database(tmp_path):
    database, new_root = create_database(tmp_path)
    assert relocation.relocate(database, Path("/old/uploads"), new_root) == 1
    assert stored_path(database) == "/old/uploads/source.txt"


def test_apply_backs_up_original_and_relocates_file(tmp_path):
    database, new_root = create_database(tmp_path)
    assert relocation.relocate(database, Path("/old/uploads"), new_root, apply=True) == 1
    assert Path(stored_path(database)).read_text() == "synthetic source"
    assert stored_path(database.with_name(database.name + ".before-relocation.sqlite3")) == "/old/uploads/source.txt"


@pytest.mark.parametrize("escape", [False, True])
def test_missing_or_escaping_source_never_changes_paths(tmp_path, escape):
    database, new_root = create_database(tmp_path)
    (new_root / "source.txt").unlink()
    if escape:
        outside = tmp_path / "outside.txt"
        outside.write_text("outside")
        (new_root / "source.txt").symlink_to(outside)
    with pytest.raises(ValueError):
        relocation.relocate(database, Path("/old/uploads"), new_root, apply=True)
    assert stored_path(database) == "/old/uploads/source.txt"
    assert not database.with_name(database.name + ".before-relocation.sqlite3").exists()
