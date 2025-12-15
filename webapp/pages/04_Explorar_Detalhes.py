import streamlit as st
import sys
from pathlib import Path
import pandas as pd

sys.path.append(str(Path(__file__).parent.parent.parent))

from webapp.utils.data_fetchers import (
    get_stops_with_risk, get_stop_details, get_stop_complaints,
    get_stop_routes, get_connected_stops, get_complaint_details,
    get_nearby_complaints, get_complaints_by_location
)
from webapp.utils.footer_console import render_query_console

st.set_page_config(page_title="Explorar Detalhes", page_icon="🔍", layout="wide")

st.title("Explorador de Detalhes")
st.markdown("Busque e explore informações detalhadas sobre paradas e reclamações")

tab1, tab2 = st.tabs(["Explorar Parada", "Explorar Reclamação"])

with tab1:
    st.subheader("Pesquisar Parada")

    stops_df = get_stops_with_risk()

    if stops_df.empty:
        st.warning("Nenhum dado de parada disponível. Execute o pipeline ETL primeiro.")
    else:
        # Search/select stop
        col1, col2 = st.columns([3, 1])

        with col1:
            selected_stop_name = st.selectbox(
                "Selecione uma parada:",
                options=sorted(stops_df[stops_df['name'].notna()]['name'].unique()),
                key="stop_search"
            )

        # Get selected stop ID
        selected_stop = stops_df[stops_df['name'] == selected_stop_name].iloc[0] if selected_stop_name else None

        if selected_stop is not None:
            stop_id = selected_stop['id']

            # Get detailed info
            try:
                stop_details = get_stop_details(stop_id)

                if stop_details:
                    # Overview metrics
                    st.divider()
                    st.subheader("📍 Visão Geral")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric(
                            "Nível de Risco",
                            stop_details.get('risk_level', 'N/A'),
                            help="Alto (≥0.6), Médio (≥0.333), Baixo (<0.333)"
                        )

                    with col2:
                        st.metric(
                            "Pontuação de Risco",
                            f"{stop_details.get('risk_score', 0):.3f}"
                        )

                    # Complaints info
                    st.divider()
                    st.subheader("📋 Informações de Reclamações")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.metric(
                            "Total de Reclamações",
                            int(stop_details.get('total_complaints', 0))
                        )

                    with col2:
                        st.metric(
                            "Reclamações Abertas",
                            int(stop_details.get('open_complaints', 0))
                        )

                    # Routes serving this stop
                    st.divider()
                    st.subheader("🚌 Rotas que Servem Esta Parada")

                    routes_df = get_stop_routes(stop_id)
                    if not routes_df.empty:
                        display_cols = st.columns([1, 3, 1, 1])
                        with display_cols[0]:
                            st.write("**Rota**")
                        with display_cols[1]:
                            st.write("**Nome da Rota**")
                        with display_cols[2]:
                            st.write("**Tipo**")
                        with display_cols[3]:
                            st.write("**Risco Médio**")

                        for _, route in routes_df.iterrows():
                            cols = st.columns([1, 3, 1, 1])
                            with cols[0]:
                                st.write(route['short_name'])
                            with cols[1]:
                                st.write(route['long_name'] if route['long_name'] else '-')
                            with cols[2]:
                                st.write(route['type'] if route['type'] else '-')
                            with cols[3]:
                                st.write(f"{route['avg_risk']:.3f}" if route['avg_risk'] else '-')
                    else:
                        st.info("Nenhuma rota encontrada para esta parada")

                    # Complaints affecting this stop
                    st.divider()
                    st.subheader("⚠️ Reclamações Afetando Esta Parada")

                    complaints_df = get_stop_complaints(stop_id)

                    if not complaints_df.empty:
                        # Category distribution
                        col1, col2 = st.columns(2)

                        with col1:
                            st.write("**Distribuição por Categoria**")
                            by_category = complaints_df['servico'].value_counts()
                            for category, count in by_category.items():
                                st.write(f"  • {category}: {count}")

                        with col2:
                            st.write("**Distribuição por Status**")
                            by_status = complaints_df['status'].value_counts()
                            for status, count in by_status.items():
                                emoji = "🟢" if status == 'Fechado' else "🟠" if status == 'Em Atendimento' else "🔴"
                                st.write(f"  {emoji} {status}: {count}")

                        # Detailed complaints table
                        st.write("**Lista Detalhada de Reclamações**")

                        # Create expandable sections for each complaint
                        for idx, (_, comp) in enumerate(complaints_df.iterrows()):
                            status_emoji = "🟢" if comp['status'] == 'Fechado' else "🟠" if comp['status'] == 'Em Atendimento' else "🔴"

                            with st.expander(f"{status_emoji} {comp['protocolo']} - {comp['servico']} ({comp['criticidade']})"):
                                col1, col2, col3, col4 = st.columns(4)

                                with col1:
                                    st.write(f"**Data**: {comp['data_abertura']}")

                                with col2:
                                    st.write(f"**Status**: {comp['status']}")

                                with col3:
                                    st.write(f"**Criticidade**: {comp['criticidade']}")

                                with col4:
                                    st.write(f"**Peso**: {comp['peso']:.2f}")

                                if comp['bairro']:
                                    st.write(f"**Bairro**: {comp['bairro']}")

                                if comp['descricao']:
                                    st.write(f"**Descrição**: {comp['descricao']}")
                    else:
                        st.info("Nenhuma reclamação afetando esta parada nos últimos 30 dias")

                    # Connected stops
                    st.divider()
                    st.subheader("🔗 Paradas Conectadas")

                    connected_df = get_connected_stops(stop_id, hops=1)

                    if not connected_df.empty:
                        st.dataframe(
                            connected_df[['name', 'risk_level', 'risk_score', 'total_complaints']],
                            use_container_width=True,
                            hide_index=True
                        )
                    else:
                        st.info("Nenhuma parada diretamente conectada")

                else:
                    st.error("Parada não encontrada")

            except Exception as e:
                st.error(f"Erro ao carregar detalhes da parada: {str(e)}")
                st.exception(e)

with tab2:
    st.subheader("Pesquisar Reclamação")

    complaints_df = get_complaints_by_location()

    if complaints_df.empty:
        st.warning("Nenhum dado de reclamação disponível.")
    else:
        # Search complaint by protocol
        protocolo = st.text_input(
            "Digite o número do protocolo da reclamação:",
            placeholder="Ex: 2024001234"
        )

        if protocolo:
            try:
                complaint_details = get_complaint_details(protocolo)

                if complaint_details:
                    st.divider()
                    st.subheader("📋 Detalhes da Reclamação")

                    # Key metrics
                    col1, col2, col3, col4, col5 = st.columns(5)

                    with col1:
                        status_emoji = "🟢" if complaint_details.get('status') == 'Fechado' else "🟠" if complaint_details.get('status') == 'Em Atendimento' else "🔴"
                        st.metric("Status", f"{status_emoji} {complaint_details.get('status', 'N/A')}")

                    with col2:
                        st.metric("Criticidade", complaint_details.get('criticidade', 'N/A'))

                    with col3:
                        st.metric("Peso", f"{complaint_details.get('peso', 0):.2f}")

                    with col4:
                        st.metric("Paradas Afetadas", int(complaint_details.get('stop_count', 0)))

                    with col5:
                        st.metric("Categoria", complaint_details.get('servico', 'N/A'))

                    # Details
                    st.divider()
                    st.subheader("ℹ️ Informações")

                    col1, col2 = st.columns(2)

                    with col1:
                        st.write(f"**Data de Abertura**: {complaint_details.get('data_abertura', 'N/A')}")
                        st.write(f"**Bairro**: {complaint_details.get('bairro', 'N/A')}")
                        st.write(f"**Peso Base da Categoria**: {complaint_details.get('category_weight', 'N/A')}")

                    with col2:
                        st.write(f"**Latitude**: {complaint_details.get('lat', 'N/A')}")
                        st.write(f"**Longitude**: {complaint_details.get('lon', 'N/A')}")

                    # Description
                    descricao = complaint_details.get('descricao')
                    if descricao:
                        st.divider()
                        st.subheader("📝 Descrição")
                        st.write(descricao)

                    # Affected stops
                    affected_stops = complaint_details.get('affected_stops', [])
                    if affected_stops:
                        st.divider()
                        st.subheader("🚏 Paradas Afetadas")
                        for stop_name in filter(None, affected_stops):
                            st.write(f"  • {stop_name}")

                    # Nearby complaints
                    st.divider()
                    st.subheader("🔎 Reclamações Próximas (raio de 500m)")

                    lat = complaint_details.get('lat')
                    lon = complaint_details.get('lon')

                    if lat and lon:
                        try:
                            nearby = get_nearby_complaints(lat, lon, radius_meters=500)

                            if not nearby.empty:
                                nearby_filtered = nearby[nearby['protocolo'] != protocolo]

                                if not nearby_filtered.empty:
                                    st.dataframe(
                                        nearby_filtered[['protocolo', 'servico', 'status', 'criticidade', 'peso']],
                                        use_container_width=True,
                                        hide_index=True
                                    )
                                else:
                                    st.info("Nenhuma reclamação próxima")
                            else:
                                st.info("Nenhuma reclamação próxima")

                        except Exception as e:
                            st.warning(f"Erro ao buscar reclamações próximas: {str(e)}")
                    else:
                        st.warning("Coordenadas da reclamação não disponíveis")

                else:
                    st.warning(f"Reclamação {protocolo} não encontrada")

            except Exception as e:
                st.error(f"Erro ao carregar detalhes da reclamação: {str(e)}")
        else:
            st.info("Digite um protocolo para buscar detalhes da reclamação")

st.divider()
st.info("💡 Este explorador fornece detalhes abrangentes sobre paradas e reclamações incluindo distribuição de reclamações e relacionamentos.")

# Render query console footer
with st.container():
    render_query_console()
