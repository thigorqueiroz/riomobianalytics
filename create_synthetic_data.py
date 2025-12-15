#!/usr/bin/env python3
"""
Generate synthetic high-risk complaint data for testing RioMobiAnalytics.
Creates complaints concentrated near key stops in Rio de Janeiro.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random

# Define high-risk areas in Rio with coordinates
HIGH_RISK_AREAS = [
    {
        "name": "Copacabana Central",
        "lat": -22.9707,
        "lon": -43.1823,
        "complaints": 50
    },
    {
        "name": "Centro - Saara",
        "lat": -22.9040,
        "lon": -43.1804,
        "complaints": 45
    },
    {
        "name": "Barra da Tijuca - Shopping",
        "lat": -23.0160,
        "lon": -43.3601,
        "complaints": 40
    },
    {
        "name": "Botafogo - Praia",
        "lat": -22.9447,
        "lon": -43.1957,
        "complaints": 35
    },
    {
        "name": "Ipanema - Arpoador",
        "lat": -22.9830,
        "lon": -43.1922,
        "complaints": 30
    },
    {
        "name": "Maracanã - Estádio",
        "lat": -22.9122,
        "lon": -43.2296,
        "complaints": 35
    },
    {
        "name": "Santa Teresa - Escadaria",
        "lat": -22.9155,
        "lon": -43.1609,
        "complaints": 28
    },
    {
        "name": "Lapa - Arcos",
        "lat": -22.9187,
        "lon": -43.1782,
        "complaints": 40
    }
]

# High-risk complaint categories
HIGH_RISK_CATEGORIES = {
    "Segurança Pública": {"weight": 1.5, "percentage": 40},
    "Iluminação Pública": {"weight": 0.6, "percentage": 30},
    "Conservação de Vias": {"weight": 0.5, "percentage": 20},
    "Trânsito e Transporte": {"weight": 0.8, "percentage": 10}
}

CRITICALITY = ["Alta", "Alta", "Média", "Média"]  # Bias towards high criticality

def generate_complaints(num_complaints=300):
    """Generate synthetic complaint data."""

    complaints = []
    protocolo_counter = 10000

    # Get date range (last 30 days)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)

    for area in HIGH_RISK_AREAS:
        num_area_complaints = area["complaints"]

        for i in range(num_area_complaints):
            # Add some randomness to coordinates (within ~500m radius)
            lat_offset = np.random.normal(0, 0.003)  # ~300m
            lon_offset = np.random.normal(0, 0.003)

            lat = area["lat"] + lat_offset
            lon = area["lon"] + lon_offset

            # Random date within last 30 days
            days_ago = random.randint(0, 29)
            complaint_date = end_date - timedelta(days=days_ago)

            # Pick high-risk category
            category = random.choices(
                list(HIGH_RISK_CATEGORIES.keys()),
                weights=[HIGH_RISK_CATEGORIES[c]["percentage"] for c in HIGH_RISK_CATEGORIES.keys()],
                k=1
            )[0]

            # Create complaint record
            complaint = {
                "protocolo": f"SYN{protocolo_counter:06d}",
                "data_abertura": complaint_date.strftime("%Y-%m-%d %H:%M:%S"),
                "servico": category,
                "latitude": round(lat, 6),
                "longitude": round(lon, 6),
                "status": "Aberto",  # All open
                "criticidade": random.choice(CRITICALITY),
                "descricao": f"Reclamação sintética em {area['name']} - {category}",
                "bairro": area["name"]
            }

            complaints.append(complaint)
            protocolo_counter += 1

    return pd.DataFrame(complaints)

def main():
    print("=" * 70)
    print("RioMobiAnalytics - Synthetic Data Generator")
    print("=" * 70)
    print()

    # Generate complaints
    print("Generating synthetic complaint data...")
    df = generate_complaints()

    print(f"✓ Created {len(df)} synthetic complaints")
    print()

    # Statistics
    print("Complaint Statistics:")
    print(f"  Date Range: Last 30 days")
    print(f"  Total Complaints: {len(df)}")
    print()

    print("By Category:")
    category_counts = df["servico"].value_counts()
    for category, count in category_counts.items():
        print(f"  • {category}: {count}")
    print()

    print("By Criticality:")
    crit_counts = df["criticidade"].value_counts()
    for crit, count in crit_counts.items():
        print(f"  • {crit}: {count}")
    print()

    print("By Area:")
    area_counts = df["bairro"].value_counts()
    for area, count in area_counts.items():
        print(f"  • {area}: {count}")
    print()

    # Save to file
    output_path = "data/1746/synthetic_complaints.csv"
    df.to_csv(output_path, index=False)

    print(f"✓ Saved to: {output_path}")
    print()

    # Show sample
    print("Sample records:")
    print(df.head(10).to_string())
    print()

    print("=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print()
    print("1. Go to webapp → 'Gerenciamento de Dados'")
    print()
    print("2. Run the pipeline steps in order:")
    print("   ✓ Step 3: Carregar Reclamações")
    print("   ✓ Step 4: Sincronizar com Neo4j")
    print("   ✓ Step 5: Calcular Métricas")
    print("   ✓ Step 6: Executar Análises")
    print()
    print("OR run from command line:")
    print()
    print("   python scripts/03_load_1746_to_mongodb.py")
    print("   python scripts/04_sync_1746_to_neo4j.py")
    print("   python scripts/05_calculate_metrics.py")
    print("   python scripts/06_run_analyses.py")
    print()
    print("After running, check the maps for high-risk stops!")
    print("=" * 70)

if __name__ == "__main__":
    main()
