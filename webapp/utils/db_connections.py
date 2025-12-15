from pymongo import MongoClient
from neo4j import GraphDatabase
import streamlit as st
import config
import time
from .query_logger import QueryLogger

@st.cache_resource
def get_mongo_client():
    return MongoClient(config.MONGO_URI)

@st.cache_resource
def get_neo4j_driver():
    return GraphDatabase.driver(
        config.NEO4J_URI,
        auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
    )

def get_mongo_db():
    client = get_mongo_client()
    return client[config.MONGO_DB]

def query_neo4j(cypher_query, parameters=None):
    driver = get_neo4j_driver()
    start_time = time.time()

    try:
        with driver.session() as session:
            result = session.run(cypher_query, parameters or {})
            records = [record.data() for record in result]

        duration_ms = (time.time() - start_time) * 1000
        QueryLogger.log_neo4j(cypher_query, parameters, duration_ms)

        return records
    except Exception as e:
        duration_ms = (time.time() - start_time) * 1000
        QueryLogger.log_neo4j(cypher_query, parameters, duration_ms)
        raise
