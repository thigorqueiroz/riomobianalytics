#!/usr/bin/env python3
"""
Examples of queries for RioMobiAnalytics
"""
from neo4j import GraphDatabase
from pymongo import MongoClient
import config


class QueryExamples:
    def __init__(self):
        self.neo4j_driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
        )
        self.mongo_client = MongoClient(config.MONGO_URI)
        self.mongo_db = self.mongo_client[config.MONGO_DB]

    def close(self):
        self.neo4j_driver.close()
        self.mongo_client.close()

    def get_high_risk_stops(self, limit=10):
        """Find stops with highest risk scores"""
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (s:Stop)
                WHERE s.risk_score IS NOT NULL
                RETURN s.id, s.name, s.risk_score, s.lat, s.lon
                ORDER BY s.risk_score DESC
                LIMIT $limit
            """, limit=limit)

            print(f"\n🚨 Top {limit} High-Risk Transit Stops:")
            print("-" * 80)
            for record in result:
                print(f"  • {record['name']}")
                print(f"    Risk Score: {record['risk_score']:.3f}")
                print(f"    Location: ({record['lat']:.6f}, {record['lon']:.6f})")
                print()

    def get_risky_routes(self, limit=10):
        """Find routes with highest risk"""
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (r:Route)
                WHERE r.avg_risk_score IS NOT NULL
                RETURN r.short_name, r.long_name, r.avg_risk_score,
                       r.high_risk_stops, r.total_stops
                ORDER BY r.avg_risk_score DESC
                LIMIT $limit
            """, limit=limit)

            print(f"\n🚌 Top {limit} High-Risk Routes:")
            print("-" * 80)
            for record in result:
                print(f"  • Route {record['short_name']}: {record['long_name']}")
                print(f"    Avg Risk: {record['avg_risk_score']:.3f}")
                print(f"    High Risk Stops: {record['high_risk_stops']}/{record['total_stops']}")
                print()

    def get_stops_with_complaints(self, limit=10):
        """Find stops with most complaints nearby"""
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (s:Stop)<-[a:AFFECTS]-(rec:Reclamacao)
                RETURN s.name, s.risk_score,
                       count(rec) as complaint_count,
                       collect(DISTINCT rec.servico)[0..5] as complaint_types
                ORDER BY complaint_count DESC
                LIMIT $limit
            """, limit=limit)

            print(f"\n📍 Top {limit} Stops with Most Nearby Complaints:")
            print("-" * 80)
            for record in result:
                print(f"  • {record['name']}")
                print(f"    Complaints: {record['complaint_count']}")
                print(f"    Risk Score: {record['risk_score']:.3f if record['risk_score'] else 0:.3f}")
                print(f"    Types: {', '.join(record['complaint_types'])}")
                print()

    def get_critical_connections(self, limit=10):
        """Find most critical transit connections"""
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (s1:Stop)-[c:CONNECTS_TO]->(s2:Stop)
                WHERE c.combined_risk IS NOT NULL
                RETURN s1.name as from_stop, s2.name as to_stop,
                       c.distance_meters, c.combined_risk, c.risk_adjusted_cost
                ORDER BY c.combined_risk DESC
                LIMIT $limit
            """, limit=limit)

            print(f"\n🔗 Top {limit} High-Risk Connections:")
            print("-" * 80)
            for record in result:
                print(f"  • {record['from_stop']} → {record['to_stop']}")
                print(f"    Distance: {record['distance_meters']:.0f}m")
                print(f"    Combined Risk: {record['combined_risk']:.3f}")
                print(f"    Risk-Adjusted Cost: {record['risk_adjusted_cost']:.0f}")
                print()

    def get_complaint_stats(self):
        """Get complaint statistics from MongoDB"""
        collection = self.mongo_db.reclamacoes_1746_raw

        print("\n📊 Complaint Statistics:")
        print("-" * 80)

        # Total complaints
        total = collection.count_documents({})
        print(f"  Total Complaints: {total:,}")

        # By status
        pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}}
        ]
        print("\n  By Status:")
        for doc in collection.aggregate(pipeline):
            print(f"    • {doc['_id']}: {doc['count']:,}")

        # By category
        pipeline = [
            {"$group": {"_id": "$servico", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": 10}
        ]
        print("\n  Top 10 Categories:")
        for doc in collection.aggregate(pipeline):
            print(f"    • {doc['_id']}: {doc['count']:,}")

    def search_stop(self, name):
        """Search for a specific stop by name"""
        with self.neo4j_driver.session() as session:
            result = session.run("""
                MATCH (s:Stop)
                WHERE toLower(s.name) CONTAINS toLower($name)
                OPTIONAL MATCH (s)<-[a:AFFECTS]-(rec:Reclamacao)
                RETURN s.id, s.name, s.risk_score, s.lat, s.lon,
                       count(rec) as complaint_count
                ORDER BY s.risk_score DESC
                LIMIT 5
            """, name=name)

            print(f"\n🔍 Search Results for '{name}':")
            print("-" * 80)
            for record in result:
                print(f"  • {record['name']}")
                print(f"    ID: {record['id']}")
                print(f"    Risk Score: {record['risk_score']:.3f if record['risk_score'] else 0:.3f}")
                print(f"    Nearby Complaints: {record['complaint_count']}")
                print(f"    Location: ({record['lat']:.6f}, {record['lon']:.6f})")
                print()


def main():
    queries = QueryExamples()

    try:
        # Run example queries
        queries.get_high_risk_stops(limit=5)
        queries.get_risky_routes(limit=5)
        queries.get_stops_with_complaints(limit=5)
        queries.get_critical_connections(limit=5)
        queries.get_complaint_stats()

        # Example search
        # queries.search_stop("Copacabana")

    finally:
        queries.close()


if __name__ == "__main__":
    main()
