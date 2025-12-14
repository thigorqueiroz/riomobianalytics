#!/usr/bin/env python3
"""
Complete the remaining steps of GTFS loading:
1. Create Route->Stop (SERVES) relationships
2. Create neighborhoods
"""
from neo4j import GraphDatabase
import config
import sys

def create_route_serves_relationships(driver):
    print("\n🔗 Criando relacionamentos Route->Stop (SERVES)...")

    with driver.session() as session:
        result = session.run("""
            MATCH (r:Route)<-[:BELONGS_TO]-(t:Trip)-[:HAS_STOP]->(s:Stop)
            WITH r, s, count(DISTINCT t) AS trips_count
            MERGE (r)-[:SERVES {
                total_trips_daily: trips_count,
                avg_frequency_minutes: 15
            }]->(s)
            RETURN count(*) as total
        """)

        record = result.single()
        print(f"  ✅ {record['total']} relacionamentos criados!")


def create_neighborhoods(driver):
    print("\n🏘️  Criando bairros e relacionamentos...")

    # Bairros principais do Rio (exemplo)
    neighborhoods = [
        {"name": "Copacabana", "regiao": "Zona Sul", "populacao": 146392},
        {"name": "Ipanema", "regiao": "Zona Sul", "populacao": 42080},
        {"name": "Centro", "regiao": "Centro", "populacao": 41142},
        {"name": "Botafogo", "regiao": "Zona Sul", "populacao": 82890},
        {"name": "Tijuca", "regiao": "Zona Norte", "populacao": 181839},
        {"name": "Barra da Tijuca", "regiao": "Zona Oeste", "populacao": 300823},
    ]

    with driver.session() as session:
        for n in neighborhoods:
            session.run("""
                CREATE (:Neighborhood {
                    name: $name,
                    regiao: $regiao,
                    populacao: $populacao,
                    total_stops: 0,
                    total_reclamacoes: 0,
                    avg_risk_score: 0.0
                })
            """, **n)

    print(f"  ✅ {len(neighborhoods)} bairros criados!")


def main():
    print("🚀 Completando carga GTFS para Neo4j...\n")

    driver = GraphDatabase.driver(
        config.NEO4J_URI,
        auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
    )

    try:
        create_route_serves_relationships(driver)
        create_neighborhoods(driver)

        print("\n✅ Carga GTFS concluída com sucesso!")
        print("\nPróximo passo: python scripts/03_load_1746_to_mongodb.py")
        return True

    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        driver.close()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
