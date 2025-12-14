import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from webapp.utils.data_fetchers import (
    get_stops_with_risk,
    get_routes_with_metrics,
    get_complaints_summary,
    get_top_critical_stops
)

st.set_page_config(page_title="Risk Dashboard", page_icon="📊", layout="wide")

st.title("Risk Analysis Dashboard")
st.markdown("Comprehensive risk metrics and analytics")

try:
    stops_df = get_stops_with_risk()
    routes_df = get_routes_with_metrics()
    complaints_df = get_complaints_summary()
    critical_stops_df = get_top_critical_stops(15)

    tab1, tab2, tab3 = st.tabs(["Stops Analysis", "Routes Analysis", "Complaints Analysis"])

    with tab1:
        st.subheader("Transit Stops Risk Analysis")

        col1, col2 = st.columns(2)

        with col1:
            risk_distribution = stops_df['risk_level'].value_counts().reset_index()
            risk_distribution.columns = ['risk_level', 'count']

            fig = px.pie(
                risk_distribution,
                values='count',
                names='risk_level',
                title='Risk Level Distribution',
                color='risk_level',
                color_discrete_map={'Alto': 'red', 'Medio': 'orange', 'Baixo': 'green'}
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.histogram(
                stops_df,
                x='risk_score',
                nbins=30,
                title='Risk Score Distribution',
                labels={'risk_score': 'Risk Score', 'count': 'Number of Stops'},
                color_discrete_sequence=['#636EFA']
            )
            fig.add_vline(x=0.6, line_dash="dash", line_color="red", annotation_text="High Risk Threshold")
            fig.add_vline(x=0.3, line_dash="dash", line_color="orange", annotation_text="Medium Risk Threshold")
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        col3, col4 = st.columns(2)

        with col3:
            fig = px.scatter(
                stops_df,
                x='total_complaints',
                y='risk_score',
                color='risk_level',
                title='Risk Score vs Total Complaints',
                labels={'total_complaints': 'Total Complaints', 'risk_score': 'Risk Score'},
                color_discrete_map={'Alto': 'red', 'Medio': 'orange', 'Baixo': 'green'},
                hover_data=['name']
            )
            st.plotly_chart(fig, use_container_width=True)

        with col4:
            fig = px.scatter(
                stops_df,
                x='centrality',
                y='risk_score',
                color='risk_level',
                title='Centrality vs Risk Score',
                labels={'centrality': 'Betweenness Centrality', 'risk_score': 'Risk Score'},
                color_discrete_map={'Alto': 'red', 'Medio': 'orange', 'Baixo': 'green'},
                hover_data=['name']
            )
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        st.subheader("Top 15 Critical Stops")
        st.dataframe(
            critical_stops_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "centrality": st.column_config.NumberColumn("Centrality", format="%.4f"),
                "risk": st.column_config.NumberColumn("Risk", format="%.3f"),
                "lat": st.column_config.NumberColumn("Latitude", format="%.4f"),
                "lon": st.column_config.NumberColumn("Longitude", format="%.4f")
            }
        )

    with tab2:
        st.subheader("Transit Routes Analysis")

        col1, col2 = st.columns(2)

        with col1:
            top_routes = routes_df.nlargest(15, 'avg_risk')
            fig = px.bar(
                top_routes,
                x='avg_risk',
                y='name',
                orientation='h',
                title='Top 15 Routes by Average Risk',
                labels={'avg_risk': 'Average Risk Score', 'name': 'Route'},
                color='avg_risk',
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.scatter(
                routes_df,
                x='total_stops',
                y='avg_risk',
                size='high_risk_stops',
                title='Route Size vs Risk',
                labels={
                    'total_stops': 'Total Stops',
                    'avg_risk': 'Average Risk',
                    'high_risk_stops': 'High Risk Stops'
                },
                hover_data=['name'],
                color='avg_risk',
                color_continuous_scale='Reds'
            )
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        col3, col4 = st.columns(2)

        with col3:
            fig = px.histogram(
                routes_df,
                x='high_risk_stops',
                nbins=20,
                title='Distribution of High Risk Stops per Route',
                labels={'high_risk_stops': 'High Risk Stops', 'count': 'Number of Routes'}
            )
            st.plotly_chart(fig, use_container_width=True)

        with col4:
            st.subheader("Route Statistics")
            st.metric("Total Routes", len(routes_df))
            st.metric("Avg Stops per Route", f"{routes_df['total_stops'].mean():.1f}")
            st.metric("Avg Risk per Route", f"{routes_df['avg_risk'].mean():.3f}")

            high_risk_routes = len(routes_df[routes_df['avg_risk'] >= 0.6])
            st.metric("High Risk Routes", high_risk_routes)

    with tab3:
        st.subheader("Complaints Analysis")

        col1, col2 = st.columns(2)

        with col1:
            fig = px.bar(
                complaints_df,
                x='count',
                y='category',
                orientation='h',
                title='Complaints by Category',
                labels={'count': 'Number of Complaints', 'category': 'Category'},
                color='count',
                color_continuous_scale='Blues'
            )
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            fig = px.bar(
                complaints_df,
                x='avg_peso',
                y='category',
                orientation='h',
                title='Average Weight by Category',
                labels={'avg_peso': 'Average Weight', 'category': 'Category'},
                color='avg_peso',
                color_continuous_scale='Oranges'
            )
            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        st.subheader("Complaint Categories Summary")
        st.dataframe(
            complaints_df.sort_values('count', ascending=False),
            use_container_width=True,
            hide_index=True,
            column_config={
                "category": "Category",
                "count": st.column_config.NumberColumn("Total Complaints", format="%d"),
                "avg_peso": st.column_config.NumberColumn("Avg Weight", format="%.3f")
            }
        )

except Exception as e:
    st.error(f"Error loading dashboard data: {str(e)}")
    st.exception(e)

st.info("💡 All charts are interactive - hover, zoom, and pan to explore the data")
