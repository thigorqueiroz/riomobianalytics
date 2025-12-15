import pandas as pd
from .db_connections import get_mongo_db, query_neo4j
import streamlit as st

@st.cache_data(ttl=300)
def get_stops_with_risk():
    query = """
    MATCH (s:Stop)
    RETURN s.id as id, s.name as name, s.lat as lat, s.lon as lon,
           s.risk_score as risk_score,
           COALESCE(s.risk_score_normalized, 0) as risk_score_normalized,
           s.risk_level as risk_level,
           s.total_reclamacoes as total_complaints,
           s.betweenness_centrality as centrality,
           s.pagerank as pagerank,
           s.community_id as community
    ORDER BY s.risk_score_normalized DESC
    """
    data = query_neo4j(query)
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_routes_with_metrics():
    query = """
    MATCH (r:Route)
    RETURN r.id as id, r.short_name as name, r.long_name as full_name,
           r.avg_risk_score as avg_risk, r.total_stops as total_stops,
           r.high_risk_stops as high_risk_stops
    ORDER BY r.avg_risk_score DESC
    """
    data = query_neo4j(query)
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_complaints_summary():
    db = get_mongo_db()

    pipeline = [
        {"$group": {
            "_id": "$servico",
            "count": {"$sum": 1},
            "avg_peso": {"$avg": "$peso"}
        }},
        {"$sort": {"count": -1}}
    ]

    results = list(db.reclamacoes_1746_raw.aggregate(pipeline))
    return pd.DataFrame(results).rename(columns={"_id": "category"})

@st.cache_data(ttl=300)
def get_network_graph_data():
    query = """
    MATCH (s1:Stop)-[c:CONNECTS_TO]->(s2:Stop)
    RETURN s1.id as source, s2.id as target, s1.name as source_name,
           s2.name as target_name, c.distance_meters as distance,
           c.risk_adjusted_cost as cost, s1.risk_score as source_risk,
           s2.risk_score as target_risk
    LIMIT 500
    """
    data = query_neo4j(query)
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_system_stats():
    query = """
    MATCH (s:Stop)
    WHERE s.risk_score IS NOT NULL
    WITH count(s) as total_stops,
         avg(s.risk_score_normalized) as avg_risk_normalized,
         percentileCont(s.risk_score_normalized, 0.67) as p67,
         count(CASE WHEN s.risk_level = 'Alto' THEN 1 END) as high_risk_stops
    MATCH (r:Route)
    WITH total_stops, avg_risk_normalized, p67, high_risk_stops, count(r) as total_routes
    MATCH (rec:Reclamacao)
    WITH total_stops, avg_risk_normalized, p67, high_risk_stops, total_routes,
         count(rec) as total_complaints,
         count(CASE WHEN rec.status = 'Aberto' THEN 1 END) as open_complaints
    RETURN total_stops, total_routes, total_complaints, open_complaints,
           avg_risk_normalized as avg_risk, high_risk_stops
    """
    data = query_neo4j(query)
    return data[0] if data else {}

@st.cache_data(ttl=300)
def get_top_critical_stops(limit=10):
    query = f"""
    MATCH (s:Stop)
    WHERE s.betweenness_centrality > 0
    RETURN s.name as name, s.betweenness_centrality as centrality,
           s.risk_score as risk, s.lat as lat, s.lon as lon,
           CASE
             WHEN s.betweenness_centrality > 0.05 AND s.risk_score > 0.6
             THEN 'CRITICAL'
             WHEN s.betweenness_centrality > 0.05
             THEN 'Structurally Critical'
             WHEN s.risk_score > 0.6
             THEN 'High Risk'
             ELSE 'Normal'
           END as classification
    ORDER BY s.betweenness_centrality DESC
    LIMIT {limit}
    """
    data = query_neo4j(query)
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_complaints_by_location():
    db = get_mongo_db()

    complaints = list(db.reclamacoes_1746_raw.find(
        {},
        {"protocolo": 1, "lat": 1, "lon": 1, "servico": 1, "status": 1, "peso": 1, "criticidade": 1}
    ).limit(1000))

    return pd.DataFrame(complaints)
