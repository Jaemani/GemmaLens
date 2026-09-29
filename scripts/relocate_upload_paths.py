"""Validate/rewrite upload paths in an offline staging copy of a SQLite DB."""

import argparse
import sqlite3
from pathlib import Path


def relocate(database: Path, old_root: Path, new_root: Path, apply: bool = False) -> int:
    database = database.resolve(strict=True)
    old_root = old_root.resolve()
    new_root = new_root.resolve(strict=True)
    changes = []
    with sqlite3.connect(database.as_uri() + "?mode=rw", uri=True) as connection:
        for document_id, raw in connection.execute("SELECT id, original_file_path FROM documents WHERE original_file_path IS NOT NULL"):
            source = Path(raw)
            try:
                relative = source.relative_to(old_root)
            except ValueError as error:
                raise ValueError("A stored path is outside --old-root; supply the correct root or review this staging DB separately") from error
            destination = (new_root / relative).resolve()
            if not destination.is_relative_to(new_root) or not destination.is_file():
                raise ValueError("A relocated file is missing or escapes --new-root; no paths were changed")
            changes.append((str(destination), document_id))
        if apply and changes:
            backup = database.with_name(database.name + ".before-relocation.sqlite3")
            with backup.open("xb"):
                pass
            backup.chmod(0o600)
            with sqlite3.connect(backup) as snapshot:
                connection.backup(snapshot)
            connection.executemany("UPDATE documents SET original_file_path=? WHERE id=?", changes)
    return len(changes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", type=Path, required=True, help="Offline staging COPY, never the live writer")
    parser.add_argument("--old-root", type=Path, required=True)
    parser.add_argument("--new-root", type=Path, required=True)
    parser.add_argument("--apply", action="store_true", help="Back up the staging DB and commit all validated path changes")
    args = parser.parse_args()
    count = relocate(args.database, args.old_root, args.new_root, args.apply)
    print(f"{'Updated' if args.apply else 'Validated (dry run)'} {count} upload paths")


if __name__ == "__main__":
    main()
