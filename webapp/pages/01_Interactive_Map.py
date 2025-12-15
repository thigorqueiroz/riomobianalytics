import streamlit as st
import folium
from streamlit_folium import st_folium
import sys
from pathlib import Path
from datetime import datetime

sys.path.append(str(Path(__file__).parent.parent.parent))

from webapp.utils.data_fetchers import (
    get_stops_with_risk, get_complaints_by_location, get_stop_details,
    get_stop_complaints, get_complaint_details, get_nearby_complaints,
    get_stop_routes, get_connected_stops
)
from webapp.utils.footer_console import render_query_console

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
                    ["Todos", "Alto", "Medio", "Baixo"],
                    index=0
                )

                min_complaints = st.slider(
                    "Mín. de Reclamações",
                    0,
                    int(stops_df['total_complaints'].max()) if 'total_complaints' in stops_df else 10,
                    0
                )

                if risk_filter != "Todos":
                    stops_df = stops_df[stops_df['risk_level'] == risk_filter]

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
                            Reclamações: {int(stop['total_complaints'])}
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
            top_stops = stops_df.nlargest(10, 'risk_score')[['name', 'risk_score', 'risk_level', 'total_complaints', 'id']]

            # Create columns for selectable table
            cols = st.columns([3, 1, 1, 1])
            with cols[0]:
                st.write("**Parada**")
            with cols[1]:
                st.write("**Risco**")
            with cols[2]:
                st.write("**Reclamações**")
            with cols[3]:
                st.write("**Ação**")

            for _, stop in top_stops.iterrows():
                cols = st.columns([3, 1, 1, 1])
                with cols[0]:
                    st.write(stop['name'])
                with cols[1]:
                    st.write(f"{stop['risk_score']:.2f}")
                with cols[2]:
                    st.write(f"{int(stop['total_complaints'])}")
                with cols[3]:
                    if st.button("Ver", key=f"btn_{stop['id']}", use_container_width=True):
                        st.session_state.selected_stop_id = stop['id']
                        st.rerun()

            # Display detailed stop information if selected
            if "selected_stop_id" in st.session_state:
                st.divider()
                st.subheader("Detalhes da Parada")

                stop_id = st.session_state.selected_stop_id
                try:
                    stop_details = get_stop_details(stop_id)
                    if stop_details:
                        col1, col2 = st.columns(2)

                        with col1:
                            st.metric("Nível de Risco", stop_details.get('risk_level', 'N/A'))
                        with col2:
                            st.metric("Pontuação de Risco", f"{stop_details.get('risk_score', 0):.3f}")

                        st.write(f"**Reclamações Totais**: {stop_details.get('total_complaints', 0)} | **Abertas**: {stop_details.get('open_complaints', 0)}")

                        # Show routes serving this stop
                        routes = stop_details.get('routes', [])
                        if routes:
                            st.write(f"**Rotas que servem**: {', '.join(filter(None, routes))}")

                        # Show complaints affecting this stop
                        st.markdown("### Reclamações Afetando Esta Parada")
                        complaints_df = get_stop_complaints(stop_id)
                        if not complaints_df.empty:
                            # Display summary
                            by_category = complaints_df['servico'].value_counts()
                            st.write("**Por Categoria**:")
                            for category, count in by_category.items():
                                st.write(f"  • {category}: {count}")

                            # Show recent complaints
                            st.write("**Reclamações Recentes**:")
                            for _, comp in complaints_df.head(5).iterrows():
                                status_color = "🟢" if comp['status'] == 'Fechado' else "🟠" if comp['status'] == 'Em Atendimento' else "🔴"
                                st.write(f"{status_color} **{comp['protocolo']}**: {comp['servico']} ({comp['criticidade']}) - {comp['bairro']}")
                                if comp['descricao']:
                                    st.caption(comp['descricao'][:100] + "...")
                        else:
                            st.info("Nenhuma reclamação afetando esta parada")

                        # Show connected stops
                        st.markdown("### Paradas Conectadas (Próximo Nó)")
                        connected = get_connected_stops(stop_id, hops=1)
                        if not connected.empty:
                            st.dataframe(connected[['name', 'risk_level', 'risk_score', 'total_complaints']], use_container_width=True, hide_index=True)
                        else:
                            st.info("Nenhuma parada conectada encontrada")

                        if st.button("Fechar Detalhes"):
                            del st.session_state.selected_stop_id
                            st.rerun()
                    else:
                        st.warning("Parada não encontrada")
                except Exception as e:
                    st.error(f"Erro ao carregar detalhes: {str(e)}")

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

            st.divider()

            st.subheader("Detalhes de Reclamações")

            # Complaint detail view
            if "selected_complaint_protocolo" in st.session_state:
                st.subheader(f"Reclamação: {st.session_state.selected_complaint_protocolo}")

                protocolo = st.session_state.selected_complaint_protocolo
                try:
                    complaint_details = get_complaint_details(protocolo)
                    if complaint_details:
                        col1, col2, col3, col4 = st.columns(4)

                        with col1:
                            status_emoji = "🟢" if complaint_details.get('status') == 'Fechado' else "🟠" if complaint_details.get('status') == 'Em Atendimento' else "🔴"
                            st.metric("Status", f"{status_emoji} {complaint_details.get('status', 'N/A')}")
                        with col2:
                            st.metric("Criticidade", complaint_details.get('criticidade', 'N/A'))
                        with col3:
                            st.metric("Peso", f"{complaint_details.get('peso', 0):.2f}")
                        with col4:
                            st.metric("Paradas Afetadas", int(complaint_details.get('stop_count', 0)))

                        st.write(f"**Categoria**: {complaint_details.get('servico', 'N/A')}")
                        st.write(f"**Bairro**: {complaint_details.get('bairro', 'N/A')}")

                        # Format date
                        data_abertura = complaint_details.get('data_abertura')
                        if data_abertura:
                            st.write(f"**Data de Abertura**: {data_abertura}")

                        # Description
                        descricao = complaint_details.get('descricao')
                        if descricao:
                            st.write(f"**Descrição**: {descricao}")

                        # Affected stops
                        affected_stops = complaint_details.get('affected_stops', [])
                        if affected_stops:
                            st.write("**Paradas Afetadas**:")
                            for stop_name in filter(None, affected_stops):
                                st.write(f"  • {stop_name}")

                        # Nearby complaints
                        st.markdown("### Reclamações Próximas")
                        lat = complaint_details.get('lat')
                        lon = complaint_details.get('lon')
                        if lat and lon:
                            nearby = get_nearby_complaints(lat, lon, radius_meters=500)
                            if not nearby.empty:
                                nearby_filtered = nearby[nearby['protocolo'] != protocolo].head(10)
                                if not nearby_filtered.empty:
                                    st.dataframe(nearby_filtered[['protocolo', 'servico', 'status', 'criticidade', 'peso']], use_container_width=True, hide_index=True)
                                else:
                                    st.info("Nenhuma reclamação próxima")
                            else:
                                st.info("Nenhuma reclamação próxima")

                        if st.button("Fechar Detalhes"):
                            del st.session_state.selected_complaint_protocolo
                            st.rerun()
                    else:
                        st.warning("Reclamação não encontrada")
                except Exception as e:
                    st.error(f"Erro ao carregar detalhes da reclamação: {str(e)}")
            else:
                # Show summary of complaints
                st.write(f"**Total de Reclamações**: {len(complaints_df)}")

                if not complaints_df.empty:
                    # Summary by status
                    st.write("**Por Status**:")
                    by_status = complaints_df['status'].value_counts()
                    for status, count in by_status.items():
                        emoji = "🟢" if status == 'Fechado' else "🟠" if status == 'Em Atendimento' else "🔴"
                        st.write(f"  {emoji} {status}: {count}")

                    # Summary by category
                    st.write("**Por Categoria**:")
                    by_category = complaints_df['servico'].value_counts()
                    for category, count in by_category.items():
                        st.write(f"  • {category}: {count}")

                    # Sample complaints
                    st.write("**Amostra de Reclamações**:")
                    for _, comp in complaints_df.head(10).iterrows():
                        if st.button(
                            f"🔍 {comp['protocolo']} - {comp['servico']} ({comp['criticidade']})",
                            key=f"comp_{comp['protocolo']}"
                        ):
                            st.session_state.selected_complaint_protocolo = comp['protocolo']
                            st.rerun()

    except Exception as e:
        st.error(f"Erro ao carregar dados de reclamações: {str(e)}")

st.info("💡 Clique em 'Ver' na tabela de paradas para explorar detalhes. Clique em um protocolo de reclamação para ver mais informações.")

# Render query console footer
with st.container():
    render_query_console()
