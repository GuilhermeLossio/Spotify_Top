from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd

from .common import REQUIRED_COLUMNS, DataSourceError, ensure_positive_int

DEFAULT_CSV_PATH = Path("data/top_songs_brasil.csv")
CSV_ENCODINGS = ("utf-8", "utf-8-sig", "cp1252", "latin-1")


def _read_csv_with_fallbacks(csv_path: Path, encodings: Iterable[str] = CSV_ENCODINGS) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in encodings:
        try:
            return pd.read_csv(csv_path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue

    if last_error:
        raise DataSourceError(
            f"Could not decode CSV file '{csv_path}'. "
            "Try UTF-8 or CP1252 encoding."
        ) from last_error

    raise DataSourceError(f"Could not read CSV file '{csv_path}'.")


def _validate_columns(df: pd.DataFrame) -> None:
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        expected = ", ".join(REQUIRED_COLUMNS)
        missing_display = ", ".join(missing)
        raise DataSourceError(
            f"Invalid CSV format. Missing columns: {missing_display}. Expected: {expected}."
        )


def _normalize_top_songs_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    _validate_columns(df)
    normalized = df.loc[:, REQUIRED_COLUMNS].copy()
    normalized["position"] = pd.to_numeric(normalized["position"], errors="coerce")
    normalized["streams"] = pd.to_numeric(normalized["streams"], errors="coerce")
    normalized = normalized.dropna(subset=["position", "track", "artist", "streams"])
    normalized["position"] = normalized["position"].astype(int)
    normalized["streams"] = normalized["streams"].astype(int).clip(lower=0)
    normalized["track"] = normalized["track"].astype(str).str.strip()
    normalized["artist"] = normalized["artist"].astype(str).str.strip()
    normalized = normalized[normalized["track"] != ""]
    return normalized.sort_values("position").reset_index(drop=True)


def load_top_songs_from_csv(
    limit: int,
    csv_path: Path | str = DEFAULT_CSV_PATH,
) -> pd.DataFrame:
    limit = ensure_positive_int(limit, field_name="The limit")

    source_path = Path(csv_path)
    if not source_path.exists():
        raise DataSourceError(f"CSV file not found: {source_path}")

    df = _read_csv_with_fallbacks(source_path)
    normalized = _normalize_top_songs_dataframe(df).head(limit).reset_index(drop=True)

    if normalized.empty:
        raise DataSourceError("CSV has no valid rows after validation.")

    return normalized


def save_top_songs_to_csv(
    df: pd.DataFrame,
    csv_path: Path | str = DEFAULT_CSV_PATH,
) -> Path:
    normalized = _normalize_top_songs_dataframe(df)
    if normalized.empty:
        raise DataSourceError("No valid rows to save in CSV.")

    target_path = Path(csv_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    normalized.to_csv(target_path, index=False, encoding="utf-8")
    return target_path
