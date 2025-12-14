import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.data_fetchers import get_system_stats

st.set_page_config(
    page_title="RioMobiAnalytics",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("RioMobiAnalytics")
st.markdown("Transit risk analysis system for Rio de Janeiro")

st.sidebar.success("Select a page above")

try:
    stats = get_system_stats()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total Stops",
            f"{stats.get('total_stops', 0):,}",
        )

    with col2:
        st.metric(
            "Transit Routes",
            f"{stats.get('total_routes', 0):,}",
        )

    with col3:
        st.metric(
            "Total Complaints",
            f"{stats.get('total_complaints', 0):,}",
        )

    with col4:
        st.metric(
            "Open Complaints",
            f"{stats.get('open_complaints', 0):,}",
        )

    st.divider()

    col5, col6 = st.columns(2)

    with col5:
        avg_risk = stats.get('avg_risk', 0)
        risk_color = "🔴" if avg_risk > 0.6 else "🟡" if avg_risk > 0.3 else "🟢"
        st.metric(
            "System Average Risk",
            f"{avg_risk:.3f}",
            delta=None,
            help="Average risk score across all transit stops"
        )
        st.write(f"{risk_color} Risk Level")

    with col6:
        high_risk = stats.get('high_risk_stops', 0)
        st.metric(
            "High Risk Stops",
            f"{high_risk:,}",
            help="Stops with risk score >= 0.6"
        )

    st.divider()

    st.subheader("About")
    st.markdown("""
    **RioMobiAnalytics** integrates GTFS transit data with 1746 citizen complaints to:

    - 📍 **Map Visualization**: Interactive map showing risk levels across the transit network
    - 📊 **Risk Dashboard**: Analytics and metrics for stops, routes, and complaints
    - 🕸️ **Network Graph**: Graph analysis showing connectivity and critical nodes
    - 📤 **Data Management**: Upload new data and trigger ETL pipelines

    ### Architecture
    - **MongoDB**: Stores raw complaint data with geospatial indexing
    - **Neo4j**: Graph database for transit network and relationships
    - **Graph Analytics**: Betweenness centrality, PageRank, community detection

    ### Navigation
    Use the sidebar to navigate between different analysis pages.
    """)

    st.divider()

    st.info("💡 Tip: All data is cached for 5 minutes. Refresh the page to see the latest updates.")

except Exception as e:
    st.error(f"Error loading system data: {str(e)}")
    st.info("Make sure MongoDB and Neo4j are running and accessible.")
