import streamlit as st
from .query_logger import QueryLogger
import pandas as pd

def render_query_console():
    """Renderiza a console de queries no rodapé"""

    st.divider()

    # Header da console
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.subheader("📊 Console de Queries")

    with col2:
        if st.button("🗑️ Limpar", key="clear_console"):
            QueryLogger.clear_logs()
            st.rerun()

    with col3:
        if st.button("🔄 Atualizar", key="refresh_console"):
            st.rerun()

    # Estatísticas
    stats = QueryLogger.get_stats()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Total de Queries", stats["total_queries"])

    with col2:
        st.metric("Neo4j", stats["neo4j_queries"])

    with col3:
        st.metric("MongoDB", stats["mongo_queries"])

    with col4:
        st.metric("Tempo Total (ms)", f"{stats['total_duration_ms']:.0f}")

    # Logs detalhados
    logs = QueryLogger.get_logs()

    if logs:
        # Tabs para diferentes tipos de query
        tab1, tab2, tab3 = st.tabs(["Todas as Queries", "Neo4j", "MongoDB"])

        with tab1:
            display_logs(logs)

        with tab2:
            neo4j_logs = [l for l in logs if l["database"] == "Neo4j"]
            display_logs(neo4j_logs)

        with tab3:
            mongo_logs = [l for l in logs if l["database"] == "MongoDB"]
            display_logs(mongo_logs)
    else:
        st.info("Nenhuma query executada ainda. Use a aplicação para ver as queries aqui.")


def display_logs(logs):
    """Exibe os logs em formato expandível"""

    for idx, log in enumerate(reversed(logs)):  # Mostrar mais recentes primeiro
        timestamp = log.get("timestamp", "N/A")
        database = log.get("database", "N/A")
        duration = log.get("duration_ms", 0)
        status = log.get("status", "?")

        # Título do expander
        if database == "Neo4j":
            query_preview = log.get("query", "")[:60] + "..."
            title = f"{status} [{timestamp}] Neo4j - {query_preview}"
        else:
            operation = log.get("operation", "N/A")
            query_preview = log.get("query", "")[:60]
            title = f"{status} [{timestamp}] MongoDB {operation} - {query_preview}"

        with st.expander(title, expanded=False):
            col1, col2 = st.columns([1, 1])

            with col1:
                st.write(f"**Database**: {database}")
                st.write(f"**Tempo**: {duration:.2f}ms")

            with col2:
                st.write(f"**Timestamp**: {timestamp}")
                if database == "Neo4j":
                    st.write(f"**Status**: {status}")

            # Query/Operation completa
            if database == "Neo4j":
                st.markdown("**Query Cypher:**")
                st.code(log.get("query", ""), language="cypher")

                if log.get("parameters"):
                    st.markdown("**Parâmetros:**")
                    st.json(log.get("parameters", {}))
            else:
                st.markdown("**Operação:**")
                st.write(log.get("operation", "N/A"))
                st.markdown("**Query:**")
                st.code(str(log.get("query", "")), language="json")

            # Divisor entre logs
            st.divider()


def render_minimal_console():
    """Renderiza uma versão minimalista da console (inline)"""

    stats = QueryLogger.get_stats()

    # Pequena inline status bar
    col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])

    with col1:
        st.caption("📊 Query Stats")

    with col2:
        st.caption(f"Total: {stats['total_queries']}")

    with col3:
        st.caption(f"Neo4j: {stats['neo4j_queries']}")

    with col4:
        st.caption(f"MongoDB: {stats['mongo_queries']}")

    with col5:
        st.caption(f"Tempo: {stats['total_duration_ms']:.0f}ms")
