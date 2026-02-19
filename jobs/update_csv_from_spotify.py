from __future__ import annotations

import os
from pathlib import Path

from backend import load_top_songs, save_top_songs_to_csv
from backend.common import DEFAULT_LIMIT, ensure_positive_int

DEFAULT_CSV_PATH = Path("data/top_songs_brasil.csv")
DEFAULT_ENV_PATH = Path(".env")

def main() -> None:
    limit = ensure_positive_int(
        os.getenv("SPOTIFY_LIMIT", str(DEFAULT_LIMIT)).strip(),
        field_name="SPOTIFY_LIMIT",
    )
    csv_path = Path(os.getenv("SPOTIFY_CSV_PATH", str(DEFAULT_CSV_PATH)).strip() or str(DEFAULT_CSV_PATH))
    env_path = Path(os.getenv("SPOTIFY_ENV_PATH", str(DEFAULT_ENV_PATH)).strip() or str(DEFAULT_ENV_PATH))

    dataframe = load_top_songs(limit=limit, env_path=env_path)
    saved_path = save_top_songs_to_csv(dataframe, csv_path=csv_path)

    print(
        f"CSV updated from Spotify with {len(dataframe)} rows at '{saved_path}'. "
        f"Top track: {dataframe.iloc[0]['track']}"
    )


if __name__ == "__main__":
    main()
