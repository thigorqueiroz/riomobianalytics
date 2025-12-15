import streamlit as st
import subprocess
import sys
from pathlib import Path
import shutil

sys.path.append(str(Path(__file__).parent.parent.parent))

from webapp.utils.footer_console import render_query_console

st.set_page_config(page_title="Gerenciamento de Dados", page_icon="📤", layout="wide")

st.title("Gerenciamento de Dados e Pipeline ETL")
st.markdown("Carregue novos dados e dispare processos ETL")

tab1, tab2, tab3 = st.tabs(["Carregar Dados", "Executar Pipeline ETL", "Status do Sistema"])

with tab1:
    st.subheader("Carregar Arquivos de Dados")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Dados GTFS")
        st.info("Carregue um arquivo zip GTFS contendo dados da rede de trânsito")

        gtfs_file = st.file_uploader(
            "Escolha o arquivo zip GTFS",
            type=['zip'],
            help="Carregue gtfs_rio-de-janeiro.zip ou similar em formato GTFS"
        )

        if gtfs_file is not None:
            if st.button("Carregar Arquivo GTFS", type="primary"):
                try:
                    save_path = Path("data/gtfs") / gtfs_file.name
                    save_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(save_path, "wb") as f:
                        f.write(gtfs_file.getbuffer())

                    st.success(f"Arquivo GTFS carregado com sucesso em {save_path}")
                except Exception as e:
                    st.error(f"Erro ao carregar arquivo GTFS: {str(e)}")

    with col2:
        st.markdown("### Dados de Reclamações 1746")
        st.info("Carregue um arquivo CSV com reclamações de cidadãos")

        complaint_file = st.file_uploader(
            "Escolha um arquivo CSV",
            type=['csv'],
            help="Carregue reclamacoes.csv ou chamados_v2.csv"
        )

        if complaint_file is not None:
            if st.button("Carregar Arquivo de Reclamações", type="primary"):
                try:
                    save_path = Path("data/1746") / complaint_file.name
                    save_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(save_path, "wb") as f:
                        f.write(complaint_file.getbuffer())

                    st.success(f"Arquivo de reclamações carregado com sucesso em {save_path}")
                except Exception as e:
                    st.error(f"Erro ao carregar arquivo de reclamações: {str(e)}")

with tab2:
    st.subheader("Controle do Pipeline ETL")

    st.warning("Executar scripts ETL modificará o banco de dados. Certifique-se de ter backups.")

    st.markdown("### Etapas do Pipeline")

    steps = [
        ("01_setup_databases.py", "Configurar Bancos de Dados", "Inicializar esquemas MongoDB e Neo4j"),
        ("02_load_gtfs_to_neo4j.py", "Carregar Dados GTFS", "Carregar dados da rede de trânsito no Neo4j"),
        ("03_load_1746_to_mongodb.py", "Carregar Reclamações", "Carregar dados de reclamações no MongoDB"),
        ("04_sync_1746_to_neo4j.py", "Sincronizar com Neo4j", "Sincronizar reclamações do MongoDB para Neo4j"),
        ("05_calculate_metrics.py", "Calcular Métricas", "Calcular pontuações de risco e métricas"),
        ("06_run_analyses.py", "Executar Análises", "Executar algoritmos de análise de grafos")
    ]

    for script, title, description in steps:
        with st.expander(f"**{title}** - {script}"):
            st.markdown(f"*{description}*")

            col1, col2 = st.columns([2, 1])

            with col1:
                st.code(f"python scripts/{script}", language="bash")

            with col2:
                if st.button(f"Executar {title}", key=script):
                    with st.spinner(f"Executando {script}..."):
                        try:
                            result = subprocess.run(
                                [sys.executable, f"scripts/{script}"],
                                capture_output=True,
                                text=True,
                                timeout=600
                            )

                            if result.returncode == 0:
                                st.success(f"{title} concluído com sucesso")
                                with st.expander("Ver Saída"):
                                    st.code(result.stdout)
                            else:
                                st.error(f"{title} falhou")
                                with st.expander("Ver Erro"):
                                    st.code(result.stderr)

                        except subprocess.TimeoutExpired:
                            st.error(f"{title} expirou após 10 minutos")
                        except Exception as e:
                            st.error(f"Erro ao executar {title}: {str(e)}")

    st.divider()

    st.markdown("### Executar Pipeline Completo")
    st.info("Executar todas as etapas ETL em sequência")

    if st.button("Executar Pipeline Completo", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, (script, title, description) in enumerate(steps):
            status_text.text(f"Executando etapa {i+1}/{len(steps)}: {title}")
            progress_bar.progress((i) / len(steps))

            try:
                result = subprocess.run(
                    [sys.executable, f"scripts/{script}"],
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                if result.returncode == 0:
                    st.success(f"✓ {title} concluído")
                else:
                    st.error(f"✗ {title} falhou")
                    st.code(result.stderr)
                    break

            except Exception as e:
                st.error(f"Erro em {title}: {str(e)}")
                break

        progress_bar.progress(1.0)
        status_text.text("Pipeline concluído!")

with tab3:
    st.subheader("Status do Sistema")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Status do MongoDB")

        try:
            from webapp.utils.db_connections import get_mongo_db
            db = get_mongo_db()

            count = db.reclamacoes_1746_raw.count_documents({})
            synced = db.reclamacoes_1746_raw.count_documents({"synced_to_neo4j": True})

            st.success("MongoDB conectado")
            st.metric("Total de Reclamações", f"{count:,}")
            st.metric("Sincronizado com Neo4j", f"{synced:,}")

            if count > 0:
                sync_percentage = (synced / count) * 100
                st.progress(sync_percentage / 100)
                st.caption(f"{sync_percentage:.1f}% sincronizado")

        except Exception as e:
            st.error(f"Falha na conexão com MongoDB: {str(e)}")

    with col2:
        st.markdown("### Status do Neo4j")

        try:
            from webapp.utils.db_connections import query_neo4j

            result = query_neo4j("MATCH (n) RETURN count(n) as total")
            total_nodes = result[0]['total'] if result else 0

            result = query_neo4j("MATCH ()-[r]->() RETURN count(r) as total")
            total_relationships = result[0]['total'] if result else 0

            st.success("Neo4j conectado")
            st.metric("Total de Nós", f"{total_nodes:,}")
            st.metric("Total de Relacionamentos", f"{total_relationships:,}")

        except Exception as e:
            st.error(f"Falha na conexão com Neo4j: {str(e)}")

    st.divider()

    st.markdown("### Status do Diretório de Dados")

    data_path = Path("data")

    if data_path.exists():
        gtfs_path = data_path / "gtfs"
        complaints_path = data_path / "1746"

        col3, col4 = st.columns(2)

        with col3:
            st.markdown("**Arquivos GTFS**")
            if gtfs_path.exists():
                files = list(gtfs_path.glob("*"))
                if files:
                    for f in files:
                        size_mb = f.stat().st_size / (1024 * 1024)
                        st.text(f"📄 {f.name} ({size_mb:.1f} MB)")
                else:
                    st.warning("Nenhum arquivo GTFS encontrado")
            else:
                st.warning("Diretório GTFS não encontrado")

        with col4:
            st.markdown("**Arquivos de Reclamações**")
            if complaints_path.exists():
                files = list(complaints_path.glob("*.csv"))
                if files:
                    for f in files:
                        size_mb = f.stat().st_size / (1024 * 1024)
                        st.text(f"📄 {f.name} ({size_mb:.1f} MB)")
                else:
                    st.warning("Nenhum arquivo de reclamações encontrado")
            else:
                st.warning("Diretório de reclamações não encontrado")

    else:
        st.warning("Diretório de dados não encontrado")

st.info("Atualize esta página após executar as etapas ETL para ver as estatísticas atualizadas")

# Render query console footer
with st.container():
    render_query_console()
