# Spotify Top Brazil 🇧🇷

This project is a Streamlit application that visualizes the top songs in Brazil using a modern, Bootstrap-styled interface.

## 🚀 Getting Started

### Prerequisites

Ensure you have Python installed. You will need the following libraries:

- `streamlit`
- `pandas`

You can install them using pip:

```bash
pip install streamlit pandas
```

### Running the Local Server

To start the application locally, run the following command in your terminal:

```bash
streamlit run streamlit_app.py
```

The application will automatically open in your default web browser at `http://localhost:8501`.

## 📊 Data Source & Import

Currently, the application imports data from a local CSV file located at `data/top_songs_brasil.csv`.

**Note on API Access:**
Direct integration with the Spotify API is currently disabled because the API key has restricted access. As a workaround, we are using a static CSV dataset to simulate the chart data. Once API access is restored or configured, the data source can be switched to live fetching.

### CSV Structure

The CSV file is expected to have the following columns:
- `position`: The rank of the song.
- `track`: The name of the song.
- `artist`: The artist name.
- `streams`: The number of streams.