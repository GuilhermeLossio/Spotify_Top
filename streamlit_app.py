import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="Spotify Top Brazil",
    layout="centered"
)

st.title("🇧🇷 Spotify Top Songs — Brazil")

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
    hide_index=True
)

# ---- Metrics ----
st.subheader("📈 Metrics")

col1, col2 = st.columns(2)

with col1:
    st.metric(
        label="Total tracks",
        value=len(df)
    )

with col2:
    st.metric(
        label="Total streams",
        value=f"{df['streams'].sum():,}".replace(",", ".")
    )

# ---- Chart ----
st.subheader("🔥 Streams per track")

chart_df = df.set_index("track")["streams"]

st.bar_chart(chart_df)

# ---- Footer ----
st.caption(
    "Source: CSV data simulating Spotify Charts Brazil"
)
