import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="Spotify Top Brazil",
    layout="wide"
)

# Inject Bootstrap CSS and custom styles
st.markdown('<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">', unsafe_allow_html=True)
st.markdown("""
<style>
.bootstrap-container {padding: 1rem 1.25rem;}
.card-value {font-size:1.25rem; font-weight:700;}
.card-subtitle {font-size:0.85rem; color: #6c757d;}
.header-lead {color: #6c757d; margin-top: -0.25rem}
.card {
    border: none;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    border-radius: 12px;
}
.stApp {
    background: linear-gradient(to bottom right, #e3f2fd, #bbdefb);
}
div.stButton > button, div.stDownloadButton > button {
    background-color: #0d6efd;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    transition: all 0.3s ease;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
    background-color: #0b5ed7;
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    transform: translateY(-2px);
    color: white;
}
</style>
""", unsafe_allow_html=True)

# Bootstrap-styled header
st.markdown("""
<div class="container bootstrap-container">
  <div class="row align-items-center">
    <div class="col-md-9">
      <h1 class="mb-1">🇧🇷 Spotify Top Songs — Brazil</h1>
      <p class="header-lead">Explore top tracks, streams and interactive charts.</p>
    </div>
    <div class="col-md-3 text-md-end text-start">
      <small class="text-muted">Built with Streamlit & Bootstrap</small>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# Path to CSV file
DATA_PATH = Path("data/top_songs_brasil.csv")

if not DATA_PATH.exists():
    st.error("CSV file not found in /data")
    st.stop()

# Read CSV
df = pd.read_csv(DATA_PATH)

required_columns = {"position", "track", "artist", "streams"}
if not required_columns.issubset(df.columns):
    st.error(
        f"Invalid CSV. Expected columns: {', '.join(required_columns)}"
    )
    st.stop()

# Order by position
df = df.sort_values("position")

# ---- UI ----
st.subheader("📊 Ranking")

st.dataframe(
    df,
    width="stretch",
    hide_index=True,
    column_config={
        "position": st.column_config.NumberColumn("Posição", format="#%d"),
        "track": "Música",
        "artist": "Artista",
        "streams": st.column_config.ProgressColumn(
            "Streams", format="%d", min_value=0, max_value=int(df["streams"].max()) if len(df) > 0 else 100
        ),
    },
)

# ---- Metrics ----
# Compute summary metrics
total_tracks = len(df)
total_streams = int(df['streams'].sum())
avg_streams = int(df['streams'].mean()) if total_tracks > 0 else 0
top_track = df.iloc[0]['track'] if total_tracks > 0 else ""

st.markdown(f"""
<div class="container bootstrap-container">
  <div class="row gx-3">
    <div class="col-sm-6 col-md-3 mb-3">
      <div class="card text-center">
        <div class="card-body">
          <h6 class="card-subtitle mb-2">Total tracks</h6>
          <div class="card-title card-value">{total_tracks}</div>
        </div>
      </div>
    </div>
    <div class="col-sm-6 col-md-3 mb-3">
      <div class="card text-center">
        <div class="card-body">
          <h6 class="card-subtitle mb-2">Total streams</h6>
          <div class="card-title card-value">{total_streams:,}</div>
        </div>
      </div>
    </div>
    <div class="col-sm-6 col-md-3 mb-3">
      <div class="card text-center">
        <div class="card-body">
          <h6 class="card-subtitle mb-2">Top track</h6>
          <div class="card-title card-value">{top_track}</div>
        </div>
      </div>
    </div>
    <div class="col-sm-6 col-md-3 mb-3">
      <div class="card text-center">
        <div class="card-body">
          <h6 class="card-subtitle mb-2">Avg streams</h6>
          <div class="card-title card-value">{avg_streams:,}</div>
        </div>
      </div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# Add a download button for filtered/exported data
st.download_button("Download CSV", df.to_csv(index=False), file_name="spotify_top_brazil.csv", mime="text/csv")

# ---- Chart ----
st.subheader("🔥 Streams per track")

chart_df = df.set_index("track")["streams"]

st.bar_chart(chart_df, color="#1DB954")

# ---- Footer ----
st.markdown('<footer class="text-muted py-3">Source: CSV data simulating Spotify Charts Brazil</footer>', unsafe_allow_html=True)
