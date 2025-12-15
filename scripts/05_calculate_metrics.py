#!/usr/bin/env python3
from neo4j import GraphDatabase
import config
import sys

class MetricsCalculator:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            config.NEO4J_URI,
            auth=(config.NEO4J_USER, config.NEO4J_PASSWORD)
        )

    def calculate_risk_scores(self):
        print("Calculating risk scores...")

        with self.driver.session() as session:
            result = session.run("""
                MATCH (s:Stop)<-[a:AFFECTS]-(rec:Reclamacao)
                WHERE rec.status IN ['Aberto', 'Em Atendimento']
                  AND rec.data_abertura >= datetime() - duration({days: 30})

                WITH s,
                     count(rec) AS total_reclamacoes,
                     count(CASE WHEN rec.status = 'Aberto' THEN 1 END) AS abertas,
                     sum(a.risk_contribution) AS risk_sum

                SET s.total_reclamacoes = total_reclamacoes,
                    s.reclamacoes_abertas = abertas,
                    s.risk_score = risk_sum / (risk_sum + 10.0),
                    s.risk_level = CASE
                      WHEN risk_sum >= 5.0 THEN 'Alto'
                      WHEN risk_sum >= 2.0 THEN 'Medio'
                      ELSE 'Baixo'
                    END,
                    s.last_risk_update = datetime()

                RETURN count(s) AS paradas_atualizadas,
                       avg(s.risk_score) AS avg_risk,
                       max(s.risk_score) AS max_risk
            """)

            record = result.single()

            if record:
                print(f"{record['paradas_atualizadas']} stops updated")
                if record['avg_risk'] is not None:
                    print(f"Avg: {record['avg_risk']:.3f}, Max: {record['max_risk']:.3f}")

            return True

    def update_connection_costs(self):
        print("Updating connections...")

        with self.driver.session() as session:
            result = session.run("""
                MATCH (s1:Stop)-[c:CONNECTS_TO]->(s2:Stop)
                SET c.combined_risk = (s1.risk_score + s2.risk_score) / 2,
                    c.risk_adjusted_cost = c.distance_meters *
                        (1 + (s1.risk_score + s2.risk_score) / 2)

                RETURN count(c) AS conexoes_atualizadas
            """)

            record = result.single()
            print(f"{record['conexoes_atualizadas']} connections updated")

            return True

    def update_route_metrics(self):
        print("Updating routes...")

        with self.driver.session() as session:
            result = session.run("""
                MATCH (r:Route)-[:SERVES]->(s:Stop)
                WITH r,
                     count(s) AS total_stops,
                     avg(s.risk_score) AS avg_risk,
                     count(CASE WHEN s.risk_score >= 0.6 THEN 1 END) AS high_risk

                SET r.total_stops = total_stops,
                    r.avg_risk_score = avg_risk,
                    r.high_risk_stops = high_risk

                RETURN count(r) AS rotas_atualizadas
            """)

            record = result.single()
            print(f"{record['rotas_atualizadas']} routes updated")

            return True

    def close(self):
        self.driver.close()

    def run(self):
        print("Metrics Calculator\n")

        try:
            self.calculate_risk_scores()
            self.update_connection_costs()
            self.update_route_metrics()

            print("\nMetrics updated successfully")
            return True

        except Exception as e:
            print(f"\nCalculation failed: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            self.close()


if __name__ == "__main__":
    calc = MetricsCalculator()
    success = calc.run()
    sys.exit(0 if success else 1)
