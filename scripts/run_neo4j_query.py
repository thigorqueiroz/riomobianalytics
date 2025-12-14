#!/usr/bin/env python3
"""
Execute Neo4j queries via Python
Usage: python run_neo4j_query.py [query_name]
"""
import sys
from neo4j import GraphDatabase
import config


class Neo4jQueryRunner:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
        )

    def close(self):
        self.driver.close()

    def execute_query(self, query, parameters=None):
        """Execute a Cypher query and return results"""
        with self.driver.session() as session:
            result = session.run(query, parameters or {})
            return list(result)

    def print_results(self, records, title="Query Results"):
        """Pretty print query results"""
        print(f"\n{'='*80}")
        print(f"{title}")
        print(f"{'='*80}\n")

        if not records:
            print("No results found.")
            return

        # Print each record
        for i, record in enumerate(records, 1):
            print(f"Record {i}:")
            for key in record.keys():
                value = record[key]
                print(f"  {key}: {value}")
            print()

        print(f"Total records: {len(records)}")
        print(f"{'='*80}\n")


# Predefined queries
QUERIES = {
    "high_risk_stops": {
        "query": """
            MATCH (s:Stop)
            WHERE s.risk_score > 0
            RETURN s.id, s.name, s.risk_score, s.lat, s.lon
            ORDER BY s.risk_score DESC
            LIMIT 10
        """,
        "description": "Top 10 stops with highest risk scores"
    },

    "risky_routes": {
        "query": """
            MATCH (r:Route)
            WHERE r.avg_risk_score > 0
            RETURN r.short_name, r.long_name, r.avg_risk_score,
                   r.high_risk_stops, r.total_stops
            ORDER BY r.avg_risk_score DESC
            LIMIT 10
        """,
        "description": "Top 10 routes with highest average risk"
    },

    "stops_with_complaints": {
        "query": """
            MATCH (s:Stop)<-[a:AFFECTS]-(rec:Reclamacao)
            WITH s, count(rec) as complaint_count,
                 collect(DISTINCT rec.servico)[0..3] as top_categories
            WHERE complaint_count > 0
            RETURN s.name, s.risk_score, complaint_count, top_categories
            ORDER BY complaint_count DESC
            LIMIT 10
        """,
        "description": "Stops with most nearby complaints"
    },

    "critical_connections": {
        "query": """
            MATCH (s1:Stop)-[c:CONNECTS_TO]->(s2:Stop)
            WHERE c.combined_risk > 0
            RETURN s1.name as from_stop, s2.name as to_stop,
                   c.distance_meters, c.combined_risk, c.risk_adjusted_cost
            ORDER BY c.combined_risk DESC
            LIMIT 10
        """,
        "description": "Most critical transit connections"
    },

    "complaint_categories": {
        "query": """
            MATCH (rec:Reclamacao)
            WITH rec.servico as category, count(*) as count
            RETURN category, count
            ORDER BY count DESC
            LIMIT 10
        """,
        "description": "Top complaint categories"
    },

    "network_stats": {
        "query": """
            MATCH (s:Stop)
            WITH count(s) as total_stops,
                 sum(CASE WHEN s.risk_score > 0.05 THEN 1 ELSE 0 END) as high_risk_stops,
                 avg(s.risk_score) as avg_risk
            MATCH (r:Route)
            WITH total_stops, high_risk_stops, avg_risk, count(r) as total_routes
            MATCH (rec:Reclamacao)
            RETURN total_stops, high_risk_stops, avg_risk,
                   total_routes, count(rec) as total_complaints
        """,
        "description": "Network statistics overview"
    },

    "stop_details": {
        "query": """
            MATCH (s:Stop {name: $stop_name})
            OPTIONAL MATCH (s)<-[a:AFFECTS]-(rec:Reclamacao)
            OPTIONAL MATCH (s)-[c:CONNECTS_TO]->(s2:Stop)
            RETURN s.id, s.name, s.risk_score, s.lat, s.lon,
                   count(DISTINCT rec) as nearby_complaints,
                   count(DISTINCT c) as connections,
                   collect(DISTINCT rec.servico)[0..5] as complaint_types
        """,
        "description": "Detailed information about a specific stop",
        "parameters": {"stop_name": "Copacabana"}
    },

    "route_analysis": {
        "query": """
            MATCH (r:Route {short_name: $route_number})
            MATCH (r)-[:SERVES]->(s:Stop)
            RETURN r.short_name, r.long_name, r.avg_risk_score,
                   count(s) as total_stops,
                   avg(s.risk_score) as calculated_avg_risk,
                   max(s.risk_score) as max_stop_risk
        """,
        "description": "Analysis of a specific route",
        "parameters": {"route_number": "001"}
    },

    "nearby_stops": {
        "query": """
            MATCH (s1:Stop)
            WHERE s1.lat IS NOT NULL AND s1.lon IS NOT NULL
            WITH s1, point({latitude: $lat, longitude: $lon}) as userLocation
            WITH s1, distance(point({latitude: s1.lat, longitude: s1.lon}), userLocation) as dist
            WHERE dist <= $radius
            RETURN s1.name, s1.risk_score, round(dist) as distance_meters
            ORDER BY dist
            LIMIT $limit
        """,
        "description": "Find stops near a location",
        "parameters": {"lat": -22.9068, "lon": -43.1729, "radius": 1000, "limit": 10}
    },

    "risk_distribution": {
        "query": """
            MATCH (s:Stop)
            WHERE s.risk_score IS NOT NULL
            WITH
                CASE
                    WHEN s.risk_score = 0 THEN 'No Risk'
                    WHEN s.risk_score < 0.02 THEN 'Very Low'
                    WHEN s.risk_score < 0.05 THEN 'Low'
                    WHEN s.risk_score < 0.10 THEN 'Medium'
                    WHEN s.risk_score < 0.20 THEN 'High'
                    ELSE 'Very High'
                END as risk_level
            RETURN risk_level, count(*) as stop_count
            ORDER BY
                CASE risk_level
                    WHEN 'No Risk' THEN 1
                    WHEN 'Very Low' THEN 2
                    WHEN 'Low' THEN 3
                    WHEN 'Medium' THEN 4
                    WHEN 'High' THEN 5
                    WHEN 'Very High' THEN 6
                END
        """,
        "description": "Distribution of risk levels across stops"
    }
}


def list_queries():
    """List all available queries"""
    print("\n" + "="*80)
    print("Available Queries")
    print("="*80 + "\n")

    for name, info in QUERIES.items():
        print(f"  {name:<25} - {info['description']}")

    print("\n" + "="*80 + "\n")


def main():
    if len(sys.argv) < 2:
        print("\nUsage: python run_neo4j_query.py [query_name|custom]")
        print("\nExamples:")
        print("  python run_neo4j_query.py high_risk_stops")
        print("  python run_neo4j_query.py risky_routes")
        print("  python run_neo4j_query.py custom")
        list_queries()
        return

    query_name = sys.argv[1]
    runner = Neo4jQueryRunner()

    try:
        if query_name == "list":
            list_queries()

        elif query_name == "custom":
            print("\nEnter your Cypher query (press Ctrl+D or Ctrl+Z when done):")
            query = sys.stdin.read()

            if not query.strip():
                print("No query provided.")
                return

            records = runner.execute_query(query)
            runner.print_results(records, "Custom Query Results")

        elif query_name in QUERIES:
            query_info = QUERIES[query_name]
            print(f"\n🔍 Executing: {query_info['description']}")

            parameters = query_info.get('parameters', {})
            records = runner.execute_query(query_info['query'], parameters)
            runner.print_results(records, query_info['description'])

        else:
            print(f"\n❌ Unknown query: {query_name}")
            list_queries()

    except Exception as e:
        print(f"\n❌ Error executing query: {e}")
        import traceback
        traceback.print_exc()

    finally:
        runner.close()


if __name__ == "__main__":
    main()
