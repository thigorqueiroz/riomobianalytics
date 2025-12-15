import pandas as pd
from .db_connections import get_mongo_db, query_neo4j
import streamlit as st
from .query_logger import QueryLogger
import time

@st.cache_data(ttl=300)
def get_stops_with_risk():
    query = """
    MATCH (s:Stop)
    RETURN s.id as id, s.name as name, s.lat as lat, s.lon as lon,
           s.risk_score as risk_score,
           COALESCE(s.risk_score_normalized, 0) as risk_score_normalized,
           s.risk_level as risk_level,
           s.total_reclamacoes as total_complaints
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
    start_time = time.time()

    pipeline = [
        {"$group": {
            "_id": "$servico",
            "count": {"$sum": 1},
            "avg_peso": {"$avg": "$peso"}
        }},
        {"$sort": {"count": -1}}
    ]

    results = list(db.reclamacoes_1746_raw.aggregate(pipeline))

    duration_ms = (time.time() - start_time) * 1000
    QueryLogger.log_mongodb("aggregate", {"collection": "reclamacoes_1746_raw"}, None, duration_ms)

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
    WHERE s.risk_score > 0
    RETURN s.name as name, s.risk_score as risk, s.lat as lat, s.lon as lon,
           s.risk_level as risk_level
    ORDER BY s.risk_score DESC
    LIMIT {limit}
    """
    data = query_neo4j(query)
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_complaints_by_location():
    db = get_mongo_db()
    start_time = time.time()

    complaints = list(db.reclamacoes_1746_raw.find(
        {},
        {"protocolo": 1, "lat": 1, "lon": 1, "servico": 1, "status": 1, "peso": 1, "criticidade": 1}
    ).limit(1000))

    duration_ms = (time.time() - start_time) * 1000
    QueryLogger.log_mongodb("find", {"collection": "reclamacoes_1746_raw"}, None, duration_ms)

    return pd.DataFrame(complaints)

@st.cache_data(ttl=300)
def get_stop_details(stop_id):
    """Get detailed information about a specific stop"""
    query = """
    MATCH (s:Stop {id: $stop_id})
    OPTIONAL MATCH (r:Route)-[:SERVES]->(s)
    OPTIONAL MATCH (rec:Reclamacao)-[:AFFECTS]->(s)
    WHERE rec.status IN ['Aberto', 'Em Atendimento']
    RETURN
      s.id as id,
      s.name as name,
      s.lat as lat,
      s.lon as lon,
      s.risk_score as risk_score,
      s.risk_level as risk_level,
      s.total_reclamacoes as total_complaints,
      s.reclamacoes_abertas as open_complaints,
      s.wheelchair_accessible as wheelchair_accessible,
      collect(DISTINCT r.short_name) as routes,
      count(DISTINCT rec) as active_complaints
    """
    data = query_neo4j(query, {"stop_id": stop_id})
    return data[0] if data else None

@st.cache_data(ttl=300)
def get_stop_complaints(stop_id):
    """Get all complaints affecting a specific stop"""
    query = """
    MATCH (rec:Reclamacao)-[:AFFECTS]->(s:Stop {id: $stop_id})
    RETURN
      rec.protocolo as protocolo,
      rec.data_abertura as data_abertura,
      rec.servico as servico,
      rec.status as status,
      rec.criticidade as criticidade,
      rec.peso as peso,
      rec.bairro as bairro,
      rec.descricao as descricao
    ORDER BY rec.data_abertura DESC
    """
    data = query_neo4j(query, {"stop_id": stop_id})
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_complaint_details(protocolo):
    """Get detailed information about a specific complaint"""
    query = """
    MATCH (rec:Reclamacao {protocolo: $protocolo})
    OPTIONAL MATCH (rec)-[:AFFECTS]->(s:Stop)
    OPTIONAL MATCH (rec)-[:HAS_TYPE]->(c:Categoria)
    RETURN
      rec.id as id,
      rec.protocolo as protocolo,
      rec.data_abertura as data_abertura,
      rec.servico as servico,
      rec.status as status,
      rec.criticidade as criticidade,
      rec.peso as peso,
      rec.lat as lat,
      rec.lon as lon,
      rec.bairro as bairro,
      rec.descricao as descricao,
      collect(DISTINCT s.name) as affected_stops,
      count(DISTINCT s) as stop_count,
      c.peso_base as category_weight
    """
    data = query_neo4j(query, {"protocolo": protocolo})
    return data[0] if data else None

@st.cache_data(ttl=300)
def get_nearby_complaints(lat, lon, radius_meters=500):
    """Get complaints near a specific location"""
    db = get_mongo_db()
    start_time = time.time()

    complaints = list(db.reclamacoes_1746_raw.find(
        {
            "localizacao": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [lon, lat]
                    },
                    "$maxDistance": radius_meters
                }
            }
        },
        {
            "protocolo": 1,
            "data_abertura": 1,
            "servico": 1,
            "status": 1,
            "peso": 1,
            "criticidade": 1,
            "bairro": 1,
            "lat": 1,
            "lon": 1
        }
    ).limit(50))

    duration_ms = (time.time() - start_time) * 1000
    QueryLogger.log_mongodb("geoNear", {"collection": "reclamacoes_1746_raw"}, None, duration_ms)

    return pd.DataFrame(complaints)

@st.cache_data(ttl=300)
def get_stop_routes(stop_id):
    """Get all routes serving a specific stop"""
    query = """
    MATCH (r:Route)-[:SERVES]->(s:Stop {id: $stop_id})
    RETURN
      r.id as id,
      r.short_name as short_name,
      r.long_name as long_name,
      r.type as type,
      r.avg_risk_score as avg_risk
    ORDER BY r.short_name
    """
    data = query_neo4j(query, {"stop_id": stop_id})
    return pd.DataFrame(data)

@st.cache_data(ttl=300)
def get_connected_stops(stop_id, hops=2):
    """Get stops connected to a specific stop"""
    query = f"""
    MATCH (start:Stop {{id: $stop_id}})-[:CONNECTS_TO*1..{hops}]-(connected:Stop)
    RETURN
      connected.id as id,
      connected.name as name,
      connected.risk_score as risk_score,
      connected.risk_level as risk_level,
      connected.total_reclamacoes as total_complaints
    ORDER BY connected.risk_score DESC
    LIMIT 50
    """
    data = query_neo4j(query, {"stop_id": stop_id})
    return pd.DataFrame(data)
