from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import pandas as pd

from .common import DEFAULT_LIMIT, REQUIRED_COLUMNS, DataSourceError, ensure_positive_int

DEFAULT_PLAYLIST_ID = "37i9dQZEVXbMXbN3EUUhlg"
DEFAULT_MARKET = "BR"
SPOTIFY_API_BASE = "https://api.spotify.com/v1"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"


@dataclass(frozen=True)
class SummaryMetrics:
    total_tracks: int
    total_streams: int
    avg_streams: int
    top_track: str


def _is_forbidden_error(error: DataSourceError) -> bool:
    return "Spotify API error (403)" in str(error)


def _clean_env_value(value: str) -> str:
    cleaned = value.strip()
    if cleaned.endswith(";"):
        cleaned = cleaned[:-1].rstrip()
    if len(cleaned) >= 2 and (
        (cleaned[0] == "'" and cleaned[-1] == "'")
        or (cleaned[0] == '"' and cleaned[-1] == '"')
    ):
        cleaned = cleaned[1:-1]
    return cleaned.strip()


def _load_env_file(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = _clean_env_value(value)
    return values


def _load_config(env_path: Path) -> dict[str, str]:
    from_file = _load_env_file(env_path)
    keys = (
        "SPOTIFY_TOKEN",
        "SPOTIFY_CLIENT_ID",
        "SPOTIFY_CLIENT_SECRET",
        "SPOTIFY_PLAYLIST_ID",
        "SPOTIFY_MARKET",
    )
    config: dict[str, str] = {}
    for key in keys:
        env_value = os.getenv(key)
        if env_value is not None and env_value.strip():
            config[key] = _clean_env_value(env_value)
        elif key in from_file:
            config[key] = from_file[key]
    return config


def _extract_error_message(payload_text: str) -> str:
    try:
        parsed = json.loads(payload_text)
    except json.JSONDecodeError:
        return payload_text.strip() or "Unknown Spotify API error."

    if isinstance(parsed, dict):
        if "error_description" in parsed:
            return str(parsed["error_description"])
        error_value = parsed.get("error")
        if isinstance(error_value, dict) and "message" in error_value:
            return str(error_value["message"])
        if isinstance(error_value, str):
            return error_value
    return payload_text.strip() or "Unknown Spotify API error."


def _request_json(
    url: str,
    *,
    headers: dict[str, str] | None = None,
    data: bytes | None = None,
    method: str = "GET",
) -> dict[str, Any]:
    request = Request(url=url, headers=headers or {}, data=data, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            payload_text = response.read().decode("utf-8")
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        message = _extract_error_message(detail)
        raise DataSourceError(f"Spotify API error ({exc.code}) on {method} {url}: {message}") from exc
    except URLError as exc:
        reason = getattr(exc, "reason", "Network error")
        raise DataSourceError(f"Failed to reach Spotify API: {reason}") from exc

    try:
        parsed = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise DataSourceError("Spotify API returned invalid JSON.") from exc

    if not isinstance(parsed, dict):
        raise DataSourceError("Spotify API returned an unexpected payload.")
    return parsed


def _create_access_token(client_id: str, client_secret: str) -> str:
    credentials = f"{client_id}:{client_secret}".encode("utf-8")
    encoded_credentials = base64.b64encode(credentials).decode("ascii")
    token_payload = urlencode({"grant_type": "client_credentials"}).encode("utf-8")
    token_headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    response = _request_json(
        SPOTIFY_TOKEN_URL,
        headers=token_headers,
        data=token_payload,
        method="POST",
    )
    access_token = str(response.get("access_token", "")).strip()
    if not access_token:
        raise DataSourceError("Could not obtain an access token from Spotify.")
    return access_token


def _resolve_access_token(config: dict[str, str]) -> str:
    direct_token = config.get("SPOTIFY_TOKEN", "").strip()
    if direct_token:
        return direct_token

    client_id = config.get("SPOTIFY_CLIENT_ID", "").strip()
    client_secret = config.get("SPOTIFY_CLIENT_SECRET", "").strip()
    if client_id and client_secret:
        return _create_access_token(client_id, client_secret)

    raise DataSourceError(
        "Spotify credentials not configured. Set SPOTIFY_TOKEN or "
        "SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET."
    )


def _fetch_playlist_tracks(token: str, playlist_id: str, market: str) -> list[dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    markets_to_try = [market.strip()]
    if markets_to_try[0]:
        markets_to_try.append("")

    last_forbidden: DataSourceError | None = None
    for market_value in markets_to_try:
        query_params: dict[str, Any] = {"limit": 100}
        if market_value:
            query_params["market"] = market_value
        query = urlencode(query_params)
        next_url = f"{SPOTIFY_API_BASE}/playlists/{playlist_id}/tracks?{query}"
        items: list[dict[str, Any]] = []

        try:
            while next_url:
                payload = _request_json(next_url, headers=headers)
                batch = payload.get("items")
                if not isinstance(batch, list):
                    raise DataSourceError("Unexpected playlist payload from Spotify API.")
                items.extend([item for item in batch if isinstance(item, dict)])
                next_value = payload.get("next")
                next_url = str(next_value) if next_value else ""
        except DataSourceError as exc:
            if market_value and _is_forbidden_error(exc):
                last_forbidden = exc
                continue
            raise

        return items

    if last_forbidden:
        raise DataSourceError(
            f"{last_forbidden} | Access denied for playlist '{playlist_id}' with and without "
            "market filter. Try another public playlist ID in SPOTIFY_PLAYLIST_ID."
        ) from last_forbidden

    return []


def load_top_songs(limit: int = DEFAULT_LIMIT, env_path: Path | str = Path(".env")) -> pd.DataFrame:
    limit = ensure_positive_int(limit, field_name="The limit")

    config = _load_config(Path(env_path))
    playlist_id = config.get("SPOTIFY_PLAYLIST_ID", DEFAULT_PLAYLIST_ID) or DEFAULT_PLAYLIST_ID
    market = config.get("SPOTIFY_MARKET", DEFAULT_MARKET) or DEFAULT_MARKET
    token = _resolve_access_token(config)

    playlist_items = _fetch_playlist_tracks(token, playlist_id, market)
    rows: list[dict[str, Any]] = []
    for item in playlist_items:
        track = item.get("track")
        if not isinstance(track, dict):
            continue

        track_name = str(track.get("name", "")).strip()
        if not track_name:
            continue

        artists = track.get("artists")
        if isinstance(artists, list):
            artist_names = [
                str(artist.get("name", "")).strip()
                for artist in artists
                if isinstance(artist, dict) and str(artist.get("name", "")).strip()
            ]
            artist_name = ", ".join(artist_names)
        else:
            artist_name = ""

        try:
            popularity = int(track.get("popularity", 0))
        except (TypeError, ValueError):
            popularity = 0

        rows.append(
            {
                "position": len(rows) + 1,
                "track": track_name,
                "artist": artist_name,
                "streams": max(0, popularity),
            }
        )
        if len(rows) >= limit:
            break

    if not rows:
        raise DataSourceError("Spotify API returned no tracks for the selected playlist.")

    return pd.DataFrame(rows, columns=REQUIRED_COLUMNS)


def compute_summary_metrics(df: pd.DataFrame) -> SummaryMetrics:
    if df.empty:
        return SummaryMetrics(
            total_tracks=0,
            total_streams=0,
            avg_streams=0,
            top_track="",
        )

    total_tracks = len(df)
    total_streams = int(df["streams"].sum())
    avg_streams = int(df["streams"].mean())
    top_track = str(df.iloc[0]["track"])

    return SummaryMetrics(
        total_tracks=total_tracks,
        total_streams=total_streams,
        avg_streams=avg_streams,
        top_track=top_track,
    )
