"""Load db/dev_seed/seed.sql into the Axom database."""

from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

import typer


def main() -> int:
    parser = argparse.ArgumentParser(description="Load dev seed into Axom DB")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete existing seed memories (source_context=dev_seed) before load",
    )
    args = parser.parse_args()

    db_path = os.environ.get(
        "AXOM_DB_PATH",
        os.path.expanduser(os.path.join("~", ".axom", "axom.db")),
    )
    seed_path = Path(__file__).resolve().parent.parent / "db" / "dev_seed" / "seed.sql"
    if not seed_path.exists():
        typer.secho(f"[ERROR] Seed file not found: {seed_path}", fg=typer.colors.RED)
        typer.echo("Run: make seed-generate")
        return 1
    conn = sqlite3.connect(db_path, timeout=30)
    if args.clear:
        conn.execute("DELETE FROM memories WHERE source_context = ?", ("dev_seed",))
        conn.commit()
        typer.secho("[OK] Cleared existing seed memories", fg=typer.colors.GREEN)
    conn.executescript(seed_path.read_text(encoding="utf-8"))
    conn.close()
    typer.secho(f"[OK] Seed loaded into {db_path}", fg=typer.colors.GREEN)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
