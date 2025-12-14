#!/usr/bin/env python3
"""
Quick script to create CONNECTS_TO relationships after fixing the Cypher query.
This runs only the connection creation part without reloading all data.
"""
from neo4j import GraphDatabase
import config
import sys

def create_connections():
    print("🔗 Criando conexões CONNECTS_TO entre paradas consecutivas...")

    driver = GraphDatabase.driver(
        config.NEO4J_URI,
        auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
    )

    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (t:Trip)-[hs1:HAS_STOP]->(s1:Stop)
                MATCH (t)-[hs2:HAS_STOP]->(s2:Stop)
                WHERE hs2.stop_sequence = hs1.stop_sequence + 1

                WITH s1, s2, t, hs1.stop_sequence AS sequence,
                     point({latitude: s1.lat, longitude: s1.lon}) AS p1,
                     point({latitude: s2.lat, longitude: s2.lon}) AS p2

                MERGE (s1)-[c:CONNECTS_TO {route_id: t.route_id}]->(s2)
                ON CREATE SET
                    c.distance_meters = round(point.distance(p1, p2)),
                    c.sequence = sequence,
                    c.travel_time_seconds = 120,
                    c.risk_adjusted_cost = round(point.distance(p1, p2))

                RETURN count(c) as total
            """)

            record = result.single()
            print(f"  ✅ {record['total']} conexões criadas com sucesso!")
            return True

    except Exception as e:
        print(f"  ❌ Erro ao criar conexões: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        driver.close()


if __name__ == "__main__":
    print("🚀 Executando correção de conexões CONNECTS_TO...\n")
    success = create_connections()

    if success:
        print("\n✅ Conexões criadas com sucesso!")
        print("Você pode agora continuar com o script 03 (load_1746_to_mongodb.py)")
        sys.exit(0)
    else:
        print("\n❌ Falha ao criar conexões")
        sys.exit(1)
