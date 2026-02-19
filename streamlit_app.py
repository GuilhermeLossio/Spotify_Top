import logging

import streamlit as st

from backend import DataSourceError, compute_summary_metrics, load_top_songs_from_csv

logger = logging.getLogger(__name__)

@st.cache_data(ttl=900, show_spinner=False)
def fetch_top_songs():
    return load_top_songs_from_csv(limit=50)


def render_styles() -> None:
    st.markdown(
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css">',
        unsafe_allow_html=True,
    )
    st.markdown(
        """
<style>
.bootstrap-container {padding: 1rem 1.25rem;}
.stApp {
    background: linear-gradient(to bottom right, #071028, #0b1020);
    color: #e6eef8;
}
div.stButton > button, div.stDownloadButton > button {
    background-color: #1DB954;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.5rem 1rem;
    transition: all 0.3s ease;
}
div.stButton > button:hover, div.stDownloadButton > button:hover {
    background-color: #17a44a;
    box-shadow: 0 6px 12px rgba(0,0,0,0.5);
    transform: translateY(-2px);
    color: white;
}
/* tweak card and text colors for dark theme */
.card {
    border: 1px solid rgba(255,255,255,0.06);
    background: rgba(255,255,255,0.02);
    box-shadow: 0 6px 18px rgba(2,6,23,0.6);
    border-radius: 12px;
    color: #e6eef8;
}
.card-value {font-size:1.25rem; font-weight:700; color: #e6eef8;}
.card-subtitle {font-size:0.85rem; color: #94a3b8;}
.header-lead {color: #94a3b8; margin-top: -0.25rem}

/* ensure tables/text in dataframes are readable */
div[class^="stDataFrame"] table, div.stDataFrame, .stDataFrame table {
    color: #e6eef8;
}
</style>
""",
        unsafe_allow_html=True,
    )


def render_header() -> None:
    st.markdown(
        """
<div class="container bootstrap-container">
  <div class="row align-items-center">
    <div class="col-md-9">
      <h1 class="mb-1">Spotify Top Songs - Brazil</h1>
      <p class="header-lead">Explore top tracks loaded from local CSV file.</p>
    </div>
    <div class="col-md-3 text-md-end text-start">
      <small class="text-muted">Built with Streamlit, Bootstrap and CSV data</small>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_ranking(df) -> None:
    st.subheader("Ranking")
    st.dataframe(
        df,
        width="stretch",
        hide_index=True,
        column_config={
            "position": st.column_config.NumberColumn("Posicao", format="#%d"),
            "track": "Musica",
            "artist": "Artista",
            "streams": st.column_config.ProgressColumn(
                "Popularidade (0-100)",
                format="%d",
                min_value=0,
                max_value=int(df["streams"].max()) if len(df) > 0 else 100,
            ),
        },
    )


def render_metrics(metrics) -> None:
    st.markdown(
        f"""
<div class="container bootstrap-container">
  <div class="row gx-3">
    <div class="col-sm-6 col-md-3 mb-3">
      <div class="card text-center">
        <div class="card-body">
          <h6 class="card-subtitle mb-2">Total tracks</h6>
          <div class="card-title card-value">{metrics.total_tracks}</div>
        </div>
      </div>
    </div>
    <div class="col-sm-6 col-md-3 mb-3">
      <div class="card text-center">
        <div class="card-body">
          <h6 class="card-subtitle mb-2">Total popularidade</h6>
          <div class="card-title card-value">{metrics.total_streams:,}</div>
        </div>
      </div>
    </div>
    <div class="col-sm-6 col-md-3 mb-3">
      <div class="card text-center">
        <div class="card-body">
          <h6 class="card-subtitle mb-2">Top track</h6>
          <div class="card-title card-value">{metrics.top_track}</div>
        </div>
      </div>
    </div>
    <div class="col-sm-6 col-md-3 mb-3">
      <div class="card text-center">
        <div class="card-body">
          <h6 class="card-subtitle mb-2">Media popularidade</h6>
          <div class="card-title card-value">{metrics.avg_streams:,}</div>
        </div>
      </div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_chart(df) -> None:
    st.subheader("Popularidade por faixa")
    chart_df = df.set_index("track")["streams"]
    st.bar_chart(chart_df, color="#1DB954")


def main() -> None:
    st.set_page_config(page_title="Spotify Top Brazil", layout="wide")
    render_styles()
    render_header()

    try:
        with st.spinner("Carregando dados do arquivo CSV..."):
            df = fetch_top_songs()
    except DataSourceError as exc:
        logger.exception("Falha ao carregar dados do CSV")
        st.error(str(exc))
        st.info(
            "Valide se o arquivo data/top_songs_brasil.csv existe e contem as colunas: "
            "position, track, artist, streams."
        )
        st.stop()

    render_ranking(df)
    metrics = compute_summary_metrics(df)
    render_metrics(metrics)

    st.download_button(
        "Download CSV",
        df.to_csv(index=False),
        file_name="spotify_top_brazil.csv",
        mime="text/csv",
    )

    render_chart(df)


if __name__ == "__main__":
    main()
