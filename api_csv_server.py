from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import pandas as pd

from backend import (
    DataSourceError,
    load_top_songs,
    load_top_songs_from_csv,
    save_top_songs_to_csv,
)
from backend.common import DEFAULT_LIMIT, ensure_positive_int

LOGGER = logging.getLogger("csv_api")
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_CSV_PATH = Path("data/top_songs_brasil.csv")


def _read_payload_rows(rows_value: Any) -> pd.DataFrame:
    if not isinstance(rows_value, list):
        raise DataSourceError("rows must be an array when source is 'rows'.")
    if not rows_value:
        raise DataSourceError("rows cannot be empty when source is 'rows'.")
    return pd.DataFrame(rows_value)


def process_update_request(payload: dict[str, Any]) -> dict[str, Any]:
    source = str(payload.get("source", "spotify")).strip().lower()
    csv_path_raw = str(payload.get("csv_path", str(DEFAULT_CSV_PATH))).strip()
    csv_path = Path(csv_path_raw or str(DEFAULT_CSV_PATH))

    if source == "spotify":
        limit = ensure_positive_int(payload.get("limit", DEFAULT_LIMIT), field_name="limit")
        env_path = Path(str(payload.get("env_path", ".env")).strip() or ".env")
        dataframe = load_top_songs(limit=limit, env_path=env_path)
    elif source == "rows":
        dataframe = _read_payload_rows(payload.get("rows"))
        limit = len(dataframe)
    else:
        raise DataSourceError("source must be 'spotify' or 'rows'.")

    saved_path = save_top_songs_to_csv(dataframe, csv_path=csv_path)
    preview = load_top_songs_from_csv(limit=min(5, len(dataframe)), csv_path=saved_path)
    now_utc = datetime.now(timezone.utc).isoformat()

    return {
        "status": "ok",
        "source": source,
        "csv_path": str(saved_path),
        "rows_written": int(len(dataframe)),
        "limit_requested": int(limit),
        "top_track": str(preview.iloc[0]["track"]),
        "updated_at_utc": now_utc,
    }


class CsvApiHandler(BaseHTTPRequestHandler):
    server_version = "SpotifyTopCsvRoute/1.0"

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json_body(self) -> dict[str, Any]:
        content_length_raw = self.headers.get("Content-Length", "0").strip() or "0"
        try:
            content_length = int(content_length_raw)
        except ValueError as exc:
            raise DataSourceError("Invalid Content-Length header.") from exc

        if content_length <= 0:
            return {}

        raw = self.rfile.read(content_length)
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise DataSourceError("Request body must be valid JSON.") from exc

        if not isinstance(parsed, dict):
            raise DataSourceError("Request body must be a JSON object.")
        return parsed

    def do_GET(self) -> None:
        parsed_path = urlparse(self.path)
        if parsed_path.path == "/health":
            self._send_json(200, {"status": "ok"})
            return
        if parsed_path.path == "/routes/csv/update":
            self._send_json(405, {"status": "error", "message": "Use POST for this route."})
            return
        self._send_json(404, {"status": "error", "message": "Route not found."})

    def do_POST(self) -> None:
        parsed_path = urlparse(self.path)
        if parsed_path.path != "/routes/csv/update":
            self._send_json(404, {"status": "error", "message": "Route not found."})
            return

        try:
            payload = self._read_json_body()
            result = process_update_request(payload)
            self._send_json(200, result)
        except DataSourceError as exc:
            self._send_json(400, {"status": "error", "message": str(exc)})
        except Exception as exc:  # pragma: no cover - defensive guard
            LOGGER.exception("Unexpected error while updating CSV route")
            self._send_json(500, {"status": "error", "message": f"Internal server error: {exc}"})

    def log_message(self, format: str, *args: Any) -> None:
        LOGGER.info("%s - %s", self.client_address[0], format % args)


def main() -> None:
    parser = argparse.ArgumentParser(description="Route server to update CSV data.")
    parser.add_argument("--host", default=DEFAULT_HOST, help=f"Bind host (default: {DEFAULT_HOST}).")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"Bind port (default: {DEFAULT_PORT}).")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
    with ThreadingHTTPServer((args.host, args.port), CsvApiHandler) as server:
        LOGGER.info("CSV route server running on http://%s:%s", args.host, args.port)
        server.serve_forever()


if __name__ == "__main__":
    main()
