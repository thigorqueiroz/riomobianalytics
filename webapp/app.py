import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from utils.data_fetchers import get_system_stats
from utils.footer_console import render_query_console
from utils.query_logger import QueryLogger

st.set_page_config(
    page_title="RioMobiAnalytics",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("RioMobiAnalytics")
st.markdown("Sistema de análise de risco de trânsito para Rio de Janeiro")

st.sidebar.success("Selecione uma página acima")

try:
    stats = get_system_stats()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "Total de Paradas",
            f"{stats.get('total_stops', 0):,}",
        )

    with col2:
        st.metric(
            "Rotas de Trânsito",
            f"{stats.get('total_routes', 0):,}",
        )

    with col3:
        st.metric(
            "Total de Reclamações",
            f"{stats.get('total_complaints', 0):,}",
        )

    with col4:
        st.metric(
            "Reclamações Abertas",
            f"{stats.get('open_complaints', 0):,}",
        )

    st.divider()

    col5, col6 = st.columns(2)

    with col5:
        avg_risk = stats.get('avg_risk', 0)
        risk_level = "Alto" if avg_risk > 67 else "Médio" if avg_risk > 33 else "Baixo"
        st.metric(
            "Risco Médio do Sistema",
            f"{avg_risk:.1f}",
            delta=None,
            help="Pontuação de risco média (escala 0-100)"
        )
        st.write(f"**{risk_level}** Nível de Risco")

    with col6:
        high_risk = stats.get('high_risk_stops', 0)
        st.metric(
            "Paradas com Alto Risco",
            f"{high_risk:,}",
            help="Paradas no top 33% de risco (score >= 67)"
        )

    st.divider()

    st.subheader("Sobre")
    st.markdown("""
    **RioMobiAnalytics** integra dados de trânsito GTFS com 1746 reclamações de cidadãos para:

    - **Visualização em Mapa**: Mapa interativo mostrando níveis de risco na rede de trânsito
    - **Painel de Risco**: Análises e métricas de paradas, rotas e reclamações
    - **Grafo de Rede**: Análise de grafos mostrando conectividade entre paradas
    - **Explorador**: Busque e explore detalhes sobre paradas e reclamações
    - **Gerenciamento de Dados**: Carregue novos dados e dispare pipelines ETL

    ### Arquitetura
    - **MongoDB**: Armazena dados brutos de reclamações com indexação geoespacial
    - **Neo4j**: Banco de dados de grafo para rede de trânsito e relacionamentos

    ### Navegação
    Use a barra lateral para navegar entre diferentes páginas de análise.
    """)

    st.divider()

    st.info("Nota: Os dados são armazenados em cache por 5 minutos. Atualize para ver as alterações mais recentes.")

except Exception as e:
    st.error(f"Erro ao carregar dados do sistema: {str(e)}")
    st.info("Certifique-se de que MongoDB e Neo4j estão em execução e acessíveis.")

# Render query console footer
with st.container():
    render_query_console()
