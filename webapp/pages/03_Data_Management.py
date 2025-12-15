import streamlit as st
import subprocess
import sys
from pathlib import Path
import shutil

sys.path.append(str(Path(__file__).parent.parent.parent))

st.set_page_config(page_title="Data Management", page_icon="📤", layout="wide")

st.title("Data Management & ETL Pipeline")
st.markdown("Upload new data and trigger ETL processes")

tab1, tab2, tab3 = st.tabs(["Upload Data", "Run ETL Pipeline", "System Status"])

with tab1:
    st.subheader("Upload Data Files")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### GTFS Data")
        st.info("Upload GTFS zip file containing transit network data")

        gtfs_file = st.file_uploader(
            "Choose GTFS zip file",
            type=['zip'],
            help="Upload gtfs_rio-de-janeiro.zip or similar GTFS format"
        )

        if gtfs_file is not None:
            if st.button("Upload GTFS File", type="primary"):
                try:
                    save_path = Path("data/gtfs") / gtfs_file.name
                    save_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(save_path, "wb") as f:
                        f.write(gtfs_file.getbuffer())

                    st.success(f"GTFS file uploaded successfully to {save_path}")
                except Exception as e:
                    st.error(f"Error uploading GTFS file: {str(e)}")

    with col2:
        st.markdown("### 1746 Complaint Data")
        st.info("Upload CSV file with citizen complaints")

        complaint_file = st.file_uploader(
            "Choose CSV file",
            type=['csv'],
            help="Upload reclamacoes.csv or chamados_v2.csv"
        )

        if complaint_file is not None:
            if st.button("Upload Complaint File", type="primary"):
                try:
                    save_path = Path("data/1746") / complaint_file.name
                    save_path.parent.mkdir(parents=True, exist_ok=True)

                    with open(save_path, "wb") as f:
                        f.write(complaint_file.getbuffer())

                    st.success(f"Complaint file uploaded successfully to {save_path}")
                except Exception as e:
                    st.error(f"Error uploading complaint file: {str(e)}")

with tab2:
    st.subheader("ETL Pipeline Control")

    st.warning("⚠️ Running ETL scripts will modify the database. Make sure you have backups.")

    st.markdown("### Pipeline Steps")

    steps = [
        ("01_setup_databases.py", "Setup Databases", "Initialize MongoDB and Neo4j schemas"),
        ("02_load_gtfs_to_neo4j.py", "Load GTFS Data", "Load transit network data into Neo4j"),
        ("03_load_1746_to_mongodb.py", "Load Complaints", "Load complaint data into MongoDB"),
        ("04_sync_1746_to_neo4j.py", "Sync to Neo4j", "Sync complaints from MongoDB to Neo4j"),
        ("05_calculate_metrics.py", "Calculate Metrics", "Compute risk scores and metrics"),
        ("06_run_analyses.py", "Run Analytics", "Execute graph analytics algorithms")
    ]

    for script, title, description in steps:
        with st.expander(f"**{title}** - {script}"):
            st.markdown(f"*{description}*")

            col1, col2 = st.columns([2, 1])

            with col1:
                st.code(f"python scripts/{script}", language="bash")

            with col2:
                if st.button(f"Run {title}", key=script):
                    with st.spinner(f"Running {script}..."):
                        try:
                            result = subprocess.run(
                                [sys.executable, f"scripts/{script}"],
                                capture_output=True,
                                text=True,
                                timeout=600
                            )

                            if result.returncode == 0:
                                st.success(f"{title} completed successfully")
                                with st.expander("View Output"):
                                    st.code(result.stdout)
                            else:
                                st.error(f"{title} failed")
                                with st.expander("View Error"):
                                    st.code(result.stderr)

                        except subprocess.TimeoutExpired:
                            st.error(f"{title} timed out after 10 minutes")
                        except Exception as e:
                            st.error(f"Error running {title}: {str(e)}")

    st.divider()

    st.markdown("### Run Full Pipeline")
    st.info("Execute all ETL steps in sequence")

    if st.button("Run Complete Pipeline", type="primary", use_container_width=True):
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, (script, title, description) in enumerate(steps):
            status_text.text(f"Running step {i+1}/{len(steps)}: {title}")
            progress_bar.progress((i) / len(steps))

            try:
                result = subprocess.run(
                    [sys.executable, f"scripts/{script}"],
                    capture_output=True,
                    text=True,
                    timeout=600
                )

                if result.returncode == 0:
                    st.success(f"✓ {title} completed")
                else:
                    st.error(f"✗ {title} failed")
                    st.code(result.stderr)
                    break

            except Exception as e:
                st.error(f"Error in {title}: {str(e)}")
                break

        progress_bar.progress(1.0)
        status_text.text("Pipeline complete!")

with tab3:
    st.subheader("System Status")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### MongoDB Status")

        try:
            from webapp.utils.db_connections import get_mongo_db
            db = get_mongo_db()

            count = db.reclamacoes_1746_raw.count_documents({})
            synced = db.reclamacoes_1746_raw.count_documents({"synced_to_neo4j": True})

            st.success("MongoDB connected")
            st.metric("Total Complaints", f"{count:,}")
            st.metric("Synced to Neo4j", f"{synced:,}")

            if count > 0:
                sync_percentage = (synced / count) * 100
                st.progress(sync_percentage / 100)
                st.caption(f"{sync_percentage:.1f}% synced")

        except Exception as e:
            st.error(f"MongoDB connection failed: {str(e)}")

    with col2:
        st.markdown("### Neo4j Status")

        try:
            from webapp.utils.db_connections import query_neo4j

            result = query_neo4j("MATCH (n) RETURN count(n) as total")
            total_nodes = result[0]['total'] if result else 0

            result = query_neo4j("MATCH ()-[r]->() RETURN count(r) as total")
            total_relationships = result[0]['total'] if result else 0

            st.success("Neo4j connected")
            st.metric("Total Nodes", f"{total_nodes:,}")
            st.metric("Total Relationships", f"{total_relationships:,}")

        except Exception as e:
            st.error(f"Neo4j connection failed: {str(e)}")

    st.divider()

    st.markdown("### Data Directory Status")

    data_path = Path("data")

    if data_path.exists():
        gtfs_path = data_path / "gtfs"
        complaints_path = data_path / "1746"

        col3, col4 = st.columns(2)

        with col3:
            st.markdown("**GTFS Files**")
            if gtfs_path.exists():
                files = list(gtfs_path.glob("*"))
                if files:
                    for f in files:
                        size_mb = f.stat().st_size / (1024 * 1024)
                        st.text(f"📄 {f.name} ({size_mb:.1f} MB)")
                else:
                    st.warning("No GTFS files found")
            else:
                st.warning("GTFS directory not found")

        with col4:
            st.markdown("**Complaint Files**")
            if complaints_path.exists():
                files = list(complaints_path.glob("*.csv"))
                if files:
                    for f in files:
                        size_mb = f.stat().st_size / (1024 * 1024)
                        st.text(f"📄 {f.name} ({size_mb:.1f} MB)")
                else:
                    st.warning("No complaint files found")
            else:
                st.warning("Complaints directory not found")

    else:
        st.warning("Data directory not found")

st.info("💡 Refresh this page after running ETL steps to see updated statistics")
