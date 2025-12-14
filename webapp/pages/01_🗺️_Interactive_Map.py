import streamlit as st
import folium
from streamlit_folium import st_folium
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from webapp.utils.data_fetchers import get_stops_with_risk, get_complaints_by_location

st.set_page_config(page_title="Interactive Map", page_icon="🗺️", layout="wide")

st.title("Interactive Map")
st.markdown("Visualize transit stops, routes, and complaints on an interactive map")

tab1, tab2 = st.tabs(["Transit Stops Risk Map", "Complaints Map"])

with tab1:
    st.subheader("Transit Stops by Risk Level")

    try:
        stops_df = get_stops_with_risk()

        if stops_df.empty:
            st.warning("No stop data available. Run the ETL pipeline first.")
        else:
            col1, col2 = st.columns([3, 1])

            with col2:
                st.markdown("### Filters")

                risk_filter = st.selectbox(
                    "Risk Level",
                    ["All", "Alto", "Medio", "Baixo"],
                    index=0
                )

                min_complaints = st.slider(
                    "Min Complaints",
                    0,
                    int(stops_df['total_complaints'].max()) if 'total_complaints' in stops_df else 10,
                    0
                )

                if risk_filter != "All":
                    stops_df = stops_df[stops_df['risk_level'] == risk_filter]

                stops_df = stops_df[stops_df['total_complaints'] >= min_complaints]

                st.metric("Stops Shown", len(stops_df))
                st.metric("Avg Risk", f"{stops_df['risk_score'].mean():.3f}")

            with col1:
                rio_center = [-22.9068, -43.1729]
                m = folium.Map(
                    location=rio_center,
                    zoom_start=11,
                    tiles="OpenStreetMap"
                )

                def get_color(risk_score):
                    if risk_score >= 0.6:
                        return 'red'
                    elif risk_score >= 0.3:
                        return 'orange'
                    else:
                        return 'green'

                for _, stop in stops_df.iterrows():
                    folium.CircleMarker(
                        location=[stop['lat'], stop['lon']],
                        radius=6,
                        popup=folium.Popup(f"""
                            <b>{stop['name']}</b><br>
                            Risk Score: {stop['risk_score']:.3f}<br>
                            Risk Level: {stop['risk_level']}<br>
                            Complaints: {int(stop['total_complaints'])}<br>
                            Centrality: {stop['centrality']:.4f}
                        """, max_width=200),
                        color=get_color(stop['risk_score']),
                        fill=True,
                        fillColor=get_color(stop['risk_score']),
                        fillOpacity=0.7,
                        weight=2
                    ).add_to(m)

                folium.LayerControl().add_to(m)

                st_folium(m, width=None, height=600)

            st.divider()

            st.subheader("Top 10 Highest Risk Stops")
            top_stops = stops_df.nlargest(10, 'risk_score')[['name', 'risk_score', 'risk_level', 'total_complaints', 'centrality']]
            st.dataframe(top_stops, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Error loading stops data: {str(e)}")

with tab2:
    st.subheader("Complaints Distribution")

    try:
        complaints_df = get_complaints_by_location()

        if complaints_df.empty:
            st.warning("No complaint data available.")
        else:
            col1, col2 = st.columns([3, 1])

            with col2:
                st.markdown("### Filters")

                category_filter = st.multiselect(
                    "Categories",
                    options=complaints_df['servico'].unique(),
                    default=None
                )

                status_filter = st.multiselect(
                    "Status",
                    options=complaints_df['status'].unique(),
                    default=None
                )

                if category_filter:
                    complaints_df = complaints_df[complaints_df['servico'].isin(category_filter)]

                if status_filter:
                    complaints_df = complaints_df[complaints_df['status'].isin(status_filter)]

                st.metric("Complaints Shown", len(complaints_df))

            with col1:
                rio_center = [-22.9068, -43.1729]
                m = folium.Map(
                    location=rio_center,
                    zoom_start=11,
                    tiles="OpenStreetMap"
                )

                def get_complaint_color(peso):
                    if peso >= 1.0:
                        return 'red'
                    elif peso >= 0.5:
                        return 'orange'
                    else:
                        return 'blue'

                for _, complaint in complaints_df.iterrows():
                    folium.CircleMarker(
                        location=[complaint['lat'], complaint['lon']],
                        radius=4,
                        popup=folium.Popup(f"""
                            <b>Complaint {complaint['protocolo']}</b><br>
                            Category: {complaint['servico']}<br>
                            Status: {complaint['status']}<br>
                            Criticality: {complaint['criticidade']}<br>
                            Weight: {complaint['peso']:.2f}
                        """, max_width=200),
                        color=get_complaint_color(complaint['peso']),
                        fill=True,
                        fillColor=get_complaint_color(complaint['peso']),
                        fillOpacity=0.6,
                        weight=1
                    ).add_to(m)

                st_folium(m, width=None, height=600)

    except Exception as e:
        st.error(f"Error loading complaints data: {str(e)}")

st.info("💡 Click on markers to see detailed information")
