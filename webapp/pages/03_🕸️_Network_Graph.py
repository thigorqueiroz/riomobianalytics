import streamlit as st
import plotly.graph_objects as go
import networkx as nx
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from webapp.utils.data_fetchers import get_network_graph_data, get_stops_with_risk

st.set_page_config(page_title="Network Graph", page_icon="🕸️", layout="wide")

st.title("Transit Network Graph")
st.markdown("Interactive visualization of the transit network with graph analytics")

try:
    network_df = get_network_graph_data()
    stops_df = get_stops_with_risk()

    if network_df.empty:
        st.warning("No network data available. Run the ETL pipeline first.")
    else:
        col1, col2 = st.columns([3, 1])

        with col2:
            st.markdown("### Settings")

            max_edges = st.slider(
                "Max Edges to Display",
                min_value=50,
                max_value=500,
                value=200,
                step=50,
                help="More edges = slower rendering"
            )

            color_by = st.selectbox(
                "Color Nodes By",
                ["Risk Score", "Centrality", "PageRank", "Community"],
                index=0
            )

            show_labels = st.checkbox("Show Node Labels", value=False)

            layout_algo = st.selectbox(
                "Layout Algorithm",
                ["Spring", "Kamada-Kawai", "Circular"],
                index=0
            )

        network_subset = network_df.head(max_edges)

        G = nx.Graph()

        for _, row in network_subset.iterrows():
            G.add_edge(
                row['source'],
                row['target'],
                distance=row['distance'],
                cost=row['cost']
            )

        stop_dict = stops_df.set_index('id').to_dict('index')

        for node in G.nodes():
            if node in stop_dict:
                G.nodes[node].update(stop_dict[node])

        if layout_algo == "Spring":
            pos = nx.spring_layout(G, k=0.5, iterations=50)
        elif layout_algo == "Kamada-Kawai":
            pos = nx.kamada_kawai_layout(G)
        else:
            pos = nx.circular_layout(G)

        edge_trace = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_trace.append(
                go.Scatter(
                    x=[x0, x1, None],
                    y=[y0, y1, None],
                    mode='lines',
                    line=dict(width=0.5, color='#888'),
                    hoverinfo='none',
                    showlegend=False
                )
            )

        node_x = []
        node_y = []
        node_text = []
        node_color = []

        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

            if node in stop_dict:
                info = stop_dict[node]
                node_text.append(
                    f"Name: {info.get('name', 'Unknown')}<br>"
                    f"Risk: {info.get('risk_score', 0):.3f}<br>"
                    f"Centrality: {info.get('centrality', 0):.4f}<br>"
                    f"PageRank: {info.get('pagerank', 0):.6f}<br>"
                    f"Community: {info.get('community', 'N/A')}<br>"
                    f"Complaints: {int(info.get('total_complaints', 0))}"
                )

                if color_by == "Risk Score":
                    node_color.append(info.get('risk_score', 0))
                elif color_by == "Centrality":
                    node_color.append(info.get('centrality', 0))
                elif color_by == "PageRank":
                    node_color.append(info.get('pagerank', 0))
                else:
                    node_color.append(info.get('community', 0))
            else:
                node_text.append("No data")
                node_color.append(0)

        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode='markers+text' if show_labels else 'markers',
            hoverinfo='text',
            text=[stop_dict.get(node, {}).get('name', '')[:10] for node in G.nodes()] if show_labels else None,
            textposition="top center",
            hovertext=node_text,
            marker=dict(
                showscale=True,
                colorscale='Reds' if color_by == "Risk Score" else 'Viridis',
                color=node_color,
                size=10,
                colorbar=dict(
                    thickness=15,
                    title=color_by,
                    xanchor='left',
                    x=1.02
                ),
                line_width=2
            )
        )

        fig = go.Figure(data=edge_trace + [node_trace],
                       layout=go.Layout(
                           title=dict(
                               text=f'Transit Network Graph ({len(G.nodes())} nodes, {len(G.edges())} edges)',
                               font=dict(size=16)
                           ),
                           showlegend=False,
                           hovermode='closest',
                           margin=dict(b=0, l=0, r=0, t=40),
                           xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                           height=700
                       ))

        with col1:
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        st.subheader("Network Statistics")

        col3, col4, col5, col6 = st.columns(4)

        with col3:
            st.metric("Total Nodes", len(G.nodes()))

        with col4:
            st.metric("Total Edges", len(G.edges()))

        with col5:
            avg_degree = sum(dict(G.degree()).values()) / len(G.nodes())
            st.metric("Avg Degree", f"{avg_degree:.2f}")

        with col6:
            density = nx.density(G)
            st.metric("Network Density", f"{density:.4f}")

        st.divider()

        st.subheader("Top Connected Nodes")

        degree_centrality = nx.degree_centrality(G)
        top_nodes = sorted(degree_centrality.items(), key=lambda x: x[1], reverse=True)[:10]

        top_nodes_data = []
        for node_id, degree in top_nodes:
            if node_id in stop_dict:
                info = stop_dict[node_id]
                top_nodes_data.append({
                    "Name": info.get('name', 'Unknown'),
                    "Degree Centrality": f"{degree:.4f}",
                    "Risk Score": f"{info.get('risk_score', 0):.3f}",
                    "Total Complaints": int(info.get('total_complaints', 0))
                })

        st.table(top_nodes_data)

except Exception as e:
    st.error(f"Error loading network graph: {str(e)}")
    st.exception(e)

st.info("💡 Hover over nodes to see details. Use the layout algorithm to explore different views.")
