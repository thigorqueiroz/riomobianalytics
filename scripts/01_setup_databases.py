#!/usr/bin/env python3
import sys
from pymongo import MongoClient
from neo4j import GraphDatabase
import config

def setup_mongodb():
    print("Setting up MongoDB...")

    try:
        client = MongoClient(config.MONGO_URI)
        db = client[config.MONGO_DB]

        db.reclamacoes_1746_raw.create_index("protocolo", unique=True)
        db.reclamacoes_1746_raw.create_index("synced_to_neo4j")
        db.reclamacoes_1746_raw.create_index("data_abertura")
        db.reclamacoes_1746_raw.create_index([("localizacao", "2dsphere")])

        print("MongoDB configured")
        client.close()
        return True

    except Exception as e:
        print(f"Failed to configure MongoDB: {e}")
        return False


def setup_neo4j():
    print("Setting up Neo4j...")

    try:
        driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
        )

        with driver.session() as session:
            print("Clearing existing data...")
            deleted_total = 0
            while True:
                result = session.run("""
                    MATCH (n)
                    WITH n LIMIT 500
                    DETACH DELETE n
                    RETURN count(n) as deleted
                """)
                deleted = result.single()["deleted"]
                deleted_total += deleted
                if deleted == 0:
                    break
                if deleted_total % 5000 == 0:
                    print(f"Deleted {deleted_total} nodes so far...")
            print(f"Deleted {deleted_total} nodes total")

            print("Creating constraints...")
            constraints = [
                "CREATE CONSTRAINT stop_id_unique IF NOT EXISTS FOR (s:Stop) REQUIRE s.id IS UNIQUE",
                "CREATE CONSTRAINT route_id_unique IF NOT EXISTS FOR (r:Route) REQUIRE r.id IS UNIQUE",
                "CREATE CONSTRAINT trip_id_unique IF NOT EXISTS FOR (t:Trip) REQUIRE t.id IS UNIQUE",
                "CREATE CONSTRAINT reclamacao_id_unique IF NOT EXISTS FOR (rec:Reclamacao) REQUIRE rec.id IS UNIQUE",
                "CREATE CONSTRAINT neighborhood_name_unique IF NOT EXISTS FOR (n:Neighborhood) REQUIRE n.name IS UNIQUE",
                "CREATE CONSTRAINT categoria_nome_unique IF NOT EXISTS FOR (c:Categoria) REQUIRE c.nome IS UNIQUE"
            ]

            for constraint in constraints:
                session.run(constraint)

            print("Creating indexes...")
            indices = [
                "CREATE INDEX stop_name IF NOT EXISTS FOR (s:Stop) ON (s.name)",
                "CREATE INDEX stop_risk IF NOT EXISTS FOR (s:Stop) ON (s.risk_score)",
                "CREATE INDEX stop_location IF NOT EXISTS FOR (s:Stop) ON (s.lat, s.lon)",
                "CREATE INDEX rec_data IF NOT EXISTS FOR (r:Reclamacao) ON (r.data_abertura)",
                "CREATE INDEX rec_status IF NOT EXISTS FOR (r:Reclamacao) ON (r.status)",
                "CREATE INDEX route_name IF NOT EXISTS FOR (r:Route) ON (r.short_name)"
            ]

            for index in indices:
                session.run(index)

            session.run(
                "CREATE FULLTEXT INDEX reclamacao_search IF NOT EXISTS "
                "FOR (r:Reclamacao) ON EACH [r.descricao, r.servico]"
            )

            print("Neo4j configured")

        driver.close()
        return True

    except Exception as e:
        print(f"Failed to configure Neo4j: {e}")
        return False


if __name__ == "__main__":
    print("Starting database setup...\n")

    mongo_ok = setup_mongodb()
    neo4j_ok = setup_neo4j()

    if mongo_ok and neo4j_ok:
        print("\nSetup complete")
        sys.exit(0)
    else:
        print("\nSetup failed")
        sys.exit(1)
