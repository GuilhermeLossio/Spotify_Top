from __future__ import annotations

import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend import load_top_songs_from_csv
from backend.common import DEFAULT_LIMIT, DataSourceError, ensure_positive_int

DEFAULT_TABLE_NAME = "spotify_top_daily"
DEFAULT_DB_PATH = Path("data/spotify_top.db")
DEFAULT_CSV_PATH = Path("data/top_songs_brasil.csv")


def _read_table_name() -> str:
    table_name = os.getenv("SPOTIFY_DB_TABLE", DEFAULT_TABLE_NAME).strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", table_name):
        raise DataSourceError(
            "SPOTIFY_DB_TABLE must use only letters, digits, and underscore, "
            "starting with a letter or underscore."
        )
    return table_name


def main() -> None:
    csv_path = Path(os.getenv("SPOTIFY_CSV_PATH", str(DEFAULT_CSV_PATH)).strip())
    db_path = Path(os.getenv("SPOTIFY_SQLITE_PATH", str(DEFAULT_DB_PATH)).strip())
    limit = ensure_positive_int(
        os.getenv("SPOTIFY_LIMIT", str(DEFAULT_LIMIT)).strip(),
        field_name="SPOTIFY_LIMIT",
    )
    table_name = _read_table_name()

    df = load_top_songs_from_csv(limit=limit, csv_path=csv_path)
    run_at = datetime.now(timezone.utc)
    snapshot_date = run_at.date().isoformat()
    captured_at_utc = run_at.isoformat()

    df = df.copy()
    df["snapshot_date"] = snapshot_date
    df["captured_at_utc"] = captured_at_utc

    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(db_path) as connection:
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    snapshot_date TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    track TEXT NOT NULL,
                    artist TEXT NOT NULL,
                    streams INTEGER NOT NULL,
                    captured_at_utc TEXT NOT NULL,
                    PRIMARY KEY (snapshot_date, position)
                )
                """
            )
            connection.execute(
                f"DELETE FROM {table_name} WHERE snapshot_date = ?",
                (snapshot_date,),
            )
            df.to_sql(table_name, connection, if_exists="append", index=False)
            connection.commit()
    except sqlite3.OperationalError as exc:
        raise DataSourceError(
            f"Could not write SQLite database '{db_path}': {exc}. "
            "Check file permissions and directory compatibility for SQLite locks."
        ) from exc

    print(
        f"Snapshot persisted: {len(df)} rows, table='{table_name}', "
        f"date={snapshot_date}, db='{db_path}'"
    )


if __name__ == "__main__":
    main()
