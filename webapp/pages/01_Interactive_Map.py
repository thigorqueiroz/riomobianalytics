import streamlit as st
import folium
from streamlit_folium import st_folium
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from webapp.utils.data_fetchers import get_stops_with_risk, get_complaints_by_location

st.set_page_config(page_title="Mapa Interativo", page_icon="🗺️", layout="wide")

st.title("Mapa Interativo")
st.markdown("Visualize paradas de trânsito, rotas e reclamações em um mapa interativo")

tab1, tab2 = st.tabs(["Mapa de Risco de Paradas", "Mapa de Reclamações"])

with tab1:
    st.subheader("Paradas de Trânsito por Nível de Risco")

    try:
        stops_df = get_stops_with_risk()

        # Filter out stops without risk data
        stops_df = stops_df[stops_df['risk_level'].notna()]

        if stops_df.empty:
            st.warning("Nenhum dado de parada disponível. Execute o pipeline ETL primeiro.")
        else:
            col1, col2 = st.columns([3, 1])

            with col2:
                st.markdown("### Filtros")

                risk_filter = st.selectbox(
                    "Nível de Risco",
                    ["Todos", "Alto", "Médio", "Baixo"],
                    index=0
                )

                min_complaints = st.slider(
                    "Mín. de Reclamações",
                    0,
                    int(stops_df['total_complaints'].max()) if 'total_complaints' in stops_df else 10,
                    0
                )

                # Normalize Portuguese accent variants
                risk_map = {"Médio": "Medio"}
                db_risk_filter = risk_map.get(risk_filter, risk_filter)

                if risk_filter != "Todos":
                    stops_df = stops_df[stops_df['risk_level'] == db_risk_filter]

                stops_df = stops_df[stops_df['total_complaints'] >= min_complaints]

                st.metric("Paradas Exibidas", len(stops_df))
                st.metric("Risco Médio", f"{stops_df['risk_score_normalized'].mean():.1f}")

            with col1:
                rio_center = [-22.9068, -43.1729]
                m = folium.Map(
                    location=rio_center,
                    zoom_start=11,
                    tiles="OpenStreetMap"
                )

                def get_color(risk_score_norm):
                    if risk_score_norm >= 67:
                        return 'red'
                    elif risk_score_norm >= 33:
                        return 'orange'
                    else:
                        return 'green'

                for _, stop in stops_df.iterrows():
                    folium.CircleMarker(
                        location=[stop['lat'], stop['lon']],
                        radius=6,
                        popup=folium.Popup(f"""
                            <b>{stop['name']}</b><br>
                            Pontuação de Risco: {stop['risk_score_normalized']:.1f}/100<br>
                            Nível de Risco: {stop['risk_level']}<br>
                            Reclamações: {int(stop['total_complaints'])}<br>
                            Centralidade: {stop['centrality']:.4f}
                        """, max_width=200),
                        color=get_color(stop['risk_score_normalized']),
                        fill=True,
                        fillColor=get_color(stop['risk_score_normalized']),
                        fillOpacity=0.7,
                        weight=2
                    ).add_to(m)

                folium.LayerControl().add_to(m)

                st_folium(m, width=None, height=600)

            st.divider()

            st.subheader("Top 10 Paradas com Maior Risco")
            top_stops = stops_df.nlargest(10, 'risk_score')[['name', 'risk_score', 'risk_level', 'total_complaints', 'centrality']]
            st.dataframe(top_stops, use_container_width=True, hide_index=True)

    except Exception as e:
        st.error(f"Erro ao carregar dados de paradas: {str(e)}")

with tab2:
    st.subheader("Distribuição de Reclamações")

    try:
        complaints_df = get_complaints_by_location()

        if complaints_df.empty:
            st.warning("Nenhum dado de reclamação disponível.")
        else:
            col1, col2 = st.columns([3, 1])

            with col2:
                st.markdown("### Filtros")

                category_filter = st.multiselect(
                    "Categorias",
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

                st.metric("Reclamações Exibidas", len(complaints_df))

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
                            <b>Reclamação {complaint['protocolo']}</b><br>
                            Categoria: {complaint['servico']}<br>
                            Status: {complaint['status']}<br>
                            Criticidade: {complaint['criticidade']}<br>
                            Peso: {complaint['peso']:.2f}
                        """, max_width=200),
                        color=get_complaint_color(complaint['peso']),
                        fill=True,
                        fillColor=get_complaint_color(complaint['peso']),
                        fillOpacity=0.6,
                        weight=1
                    ).add_to(m)

                st_folium(m, width=None, height=600)

    except Exception as e:
        st.error(f"Erro ao carregar dados de reclamações: {str(e)}")

st.info("Clique nos marcadores para ver informações detalhadas")
