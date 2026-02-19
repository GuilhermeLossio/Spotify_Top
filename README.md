# Spotify Top Brazil

This project is a Streamlit application that visualizes top songs in Brazil using a local CSV file, that can be reqeuested from Spotify API using the credentials.
<img width="1906" height="869" alt="image" src="https://github.com/user-attachments/assets/1d3ab88d-023e-44c5-b66a-f823518ed939" />
The project was done for the : Fast-Track Challenge, Institute Minerva. Week 1.<br>
[Institute Minerva](https://minerva.org.br/)

## Project Structure

- `streamlit_app.py`: frontend layer (UI rendering and user interaction).
- `backend/common.py`: shared constants (`REQUIRED_COLUMNS`, `DEFAULT_LIMIT`) and validation helpers.
- `backend/csv_service.py`: CSV loading and validation.
- `backend/spotify_service.py`: Spotify API integration (kept for future sync jobs).
- `jobs/daily_csv_to_sqlite.py`: daily snapshot job from CSV to SQLite.
- `data/top_songs_brasil.csv`: source file used by the app.

## Getting Started

### Prerequisites

Install Python and required libraries:

```bash
pip install streamlit pandas
```

### Run Locally

Start the frontend:

```bash
streamlit run streamlit_app.py
```

The application opens at `http://localhost:8501`.

## CSV Format

The app expects `data/top_songs_brasil.csv` with these columns:

- `position`
- `track`
- `artist`
- `streams`

Validation for required columns and positive numeric limits is centralized in `backend/common.py`.

## Daily Database Snapshot (SQLite)

Run the daily job manually:

```bash
python jobs/daily_csv_to_sqlite.py
```

Optional environment variables:

```env
SPOTIFY_CSV_PATH=data/top_songs_brasil.csv
SPOTIFY_SQLITE_PATH=data/spotify_top.db
SPOTIFY_DB_TABLE=spotify_top_daily
SPOTIFY_LIMIT=50
```

For a daily event, schedule the command above in Windows Task Scheduler (or cron on Linux).

## Route To Update CSV

Start a lightweight HTTP server:

```bash
python api_csv_server.py --host 127.0.0.1 --port 8080
```

Health check:

```bash
curl http://127.0.0.1:8080/health
```

Update CSV from Spotify API:

```bash
curl -X POST http://127.0.0.1:8080/routes/csv/update -H "Content-Type: application/json" -d "{\"source\":\"spotify\",\"limit\":50,\"csv_path\":\"data/top_songs_brasil.csv\"}"
```

Update CSV from payload rows:

```bash
curl -X POST http://127.0.0.1:8080/routes/csv/update -H "Content-Type: application/json" -d "{\"source\":\"rows\",\"csv_path\":\"data/top_songs_brasil.csv\",\"rows\":[{\"position\":1,\"track\":\"Song\",\"artist\":\"Artist\",\"streams\":123}]}"
```

## Cron With Streamlit Deploy

If you deploy on Streamlit Community Cloud, there is no native background cron job inside the app runtime.
Use an external scheduler and update the CSV in the repository.

This repo includes a daily GitHub Actions workflow:

- `.github/workflows/update-csv-daily.yml`
- `jobs/update_csv_from_spotify.py`

Required GitHub Secrets:

- `SPOTIFY_CLIENT_ID`
- `SPOTIFY_CLIENT_SECRET`
- `SPOTIFY_TOKEN` (optional)
- `SPOTIFY_PLAYLIST_ID` (optional)
- `SPOTIFY_MARKET` (optional)

The workflow runs daily at `09:00 UTC` and can also be triggered manually via `workflow_dispatch`.
When the CSV changes, it commits `data/top_songs_brasil.csv` automatically.
