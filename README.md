# RioMobiAnalytics

Transit analytics system that integrates Rio de Janeiro's public transportation data (GTFS format) with citizen complaint data (1746 service) to identify high-risk transit stops and analyze transportation network vulnerabilities.

## Overview

RioMobiAnalytics uses a hybrid database architecture to combine transit network data with urban complaint reports, enabling risk assessment and graph-based analysis of Rio's public transportation system.

### Key Features

- **Risk Scoring**: Complaints near transit stops contribute to risk scores based on category weight, criticality, and proximity
- **Graph Analytics**: Betweenness centrality, PageRank, and community detection using Neo4j GDS
- **Spatial Analysis**: Geospatial indexing and proximity-based relationship mapping
- **Network Visualization**: Identify critical stops, vulnerable routes, and complaint clusters

## Architecture

### Hybrid Database System

**MongoDB**
- Raw storage for 1746 complaint data
- GeoJSON support for spatial queries
- Geospatial 2dsphere indexing

**Neo4j**
- Graph representation of GTFS transit network
- Stop, Route, Trip, and Complaint nodes
- Relationship tracking (CONNECTS_TO, SERVES, AFFECTS, HAS_STOP)
- Graph Data Science library for analytics

### Data Flow

```
1746 Complaints (MongoDB) → Spatial Linking → Neo4j Graph
GTFS Data → Neo4j Graph → Risk Scoring → Analytics
```

## Requirements

- Python 3.8+
- MongoDB 4.4+
- Neo4j 5.0+ with Graph Data Science (GDS) plugin
- 4GB+ RAM recommended

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/thigorqueiroz/riomobianalytics.git
cd riomobianalytics
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your database credentials:

```
MONGO_URI=mongodb://localhost:27017/
MONGO_DB=riomobianalytics

NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password
```

### 4. Install Neo4j GDS Plugin

Download the Neo4j Graph Data Science plugin from:
https://neo4j.com/deployment-center/

Extract to `$NEO4J_HOME/plugins/`

### 5. Prepare Data

Place data files in the following structure:

```
data/
  gtfs/
    gtfs_rio-de-janeiro.zip
  1746/
    chamados_v2.csv  (or reclamacoes.csv)
```

## Usage

### Run Complete ETL Pipeline

```bash
./run_all.sh
```

Or execute scripts individually:

```bash
python scripts/01_setup_databases.py
python scripts/02_load_gtfs_to_neo4j.py
python scripts/03_load_1746_to_mongodb.py
python scripts/04_sync_1746_to_neo4j.py
python scripts/05_calculate_metrics.py
python scripts/06_run_analyses.py
```

### Docker Setup (Optional)

```bash
docker-compose up -d
```

## ETL Pipeline

### 1. Setup Databases (01_setup_databases.py)
- Creates MongoDB collections and indexes
- Creates Neo4j constraints and indexes
- Clears existing data

### 2. Load GTFS Data (02_load_gtfs_to_neo4j.py)
- Extracts GTFS zip file if needed
- Loads stops, routes, trips (15,917 trips)
- Creates stop-to-stop connections
- Establishes route-to-stop relationships

### 3. Load 1746 Complaints (03_load_1746_to_mongodb.py)
- Reads CSV data (auto-detects format)
- Normalizes categories and criticality levels
- Creates GeoJSON location fields
- Handles duplicates via unique protocolo index

### 4. Sync to Neo4j (04_sync_1746_to_neo4j.py)
- Transfers complaints from MongoDB to Neo4j
- Creates AFFECTS relationships (100m radius)
- Links complaints to nearby stops
- Updates stop complaint counters

### 5. Calculate Metrics (05_calculate_metrics.py)
- Computes risk scores for stops (last 30 days)
- Updates connection costs based on risk
- Aggregates route-level metrics

### 6. Run Analytics (06_run_analyses.py)
- Betweenness centrality (identifies bottlenecks)
- Louvain community detection
- PageRank (network importance)
- Complaint cluster identification

## Configuration

Edit `config.py` to adjust:

- `MAX_DISTANCE_AFFECTS_METERS`: Radius for linking complaints to stops (default: 100m)
- `CATEGORIA_PESOS`: Category weights for risk calculation
- `CRITICIDADE_MAP`: Criticality multipliers (Alta/Média/Baixa)
- `BATCH_SIZE`: Batch processing size (default: 1000)

### Risk Scoring Formula

```
risk_score = risk_sum / (risk_sum + 10.0)

where:
  risk_sum = sum(complaint.peso * criticidade_multiplier)
```

Risk levels:
- Alto: >= 5.0
- Medio: >= 2.0
- Baixo: < 2.0

## Data Structures

### Neo4j Node Labels

- **Stop**: Transit stops with risk_score, betweenness_centrality, pagerank, community_id
- **Route**: Transit routes with avg_risk_score, total_stops, high_risk_stops
- **Trip**: Individual trips with route_id, headsign, direction
- **Reclamacao**: Complaints with protocolo, servico, lat/lon, peso, criticidade
- **Categoria**: Complaint categories with peso_base, total_ocorrencias

### Neo4j Relationships

- `CONNECTS_TO`: Sequential stops on routes (with distance, travel time)
- `SERVES`: Routes serving stops (with frequency)
- `HAS_STOP`: Trips to stops (with sequence, arrival/departure times)
- `AFFECTS`: Complaints affecting nearby stops (with distance, impact level)
- `HAS_TYPE`: Complaints to categories
- `CLUSTERS_WITH`: Spatially/temporally clustered complaints

## CSV Format Support

The system auto-detects two CSV formats:

**Format 1: reclamacoes.csv**
- protocolo, data_abertura, servico, latitude, longitude, status, descricao, criticidade, bairro

**Format 2: chamados_v2.csv**
- id_chamado, data_inicio, categoria, latitude, longitude
- Auto-mapped to standard format with defaults

## Graph Analytics

### Betweenness Centrality
Identifies structurally critical stops (network bottlenecks)

### Community Detection (Louvain)
Groups stops into communities based on connection patterns

### PageRank
Ranks stops by network importance and connectivity

### Cluster Analysis
Identifies spatially (200m radius) and temporally (7-day window) clustered complaints

## Performance Notes

- GTFS extraction handles large files (stop_times.txt ~80MB)
- Batch processing for large datasets (configurable batch size)
- Incremental complaint loading (synced_to_neo4j flag)
- Graph projection caching for repeated analytics

## Troubleshooting

**Database Connection Issues**
- Verify MongoDB is running: `mongosh`
- Verify Neo4j is running: `cypher-shell`
- Check credentials in `.env`

**Missing Neo4j GDS Plugin**
- Download from https://neo4j.com/deployment-center/
- Install to `$NEO4J_HOME/plugins/`
- Restart Neo4j

**GTFS Extraction Errors**
- Verify `gtfs_rio-de-janeiro.zip` exists in `data/gtfs/`
- Check zip file integrity
- Ensure sufficient disk space

## Project Structure

```
riomobianalytics/
├── config.py              # Configuration and constants
├── requirements.txt       # Python dependencies
├── run_all.sh            # Execute full pipeline
├── docker-compose.yml    # Docker setup
├── Makefile              # Build commands
├── scripts/
│   ├── 01_setup_databases.py
│   ├── 02_load_gtfs_to_neo4j.py
│   ├── 03_load_1746_to_mongodb.py
│   ├── 04_sync_1746_to_neo4j.py
│   ├── 05_calculate_metrics.py
│   └── 06_run_analyses.py
└── data/
    ├── gtfs/             # GTFS transit data
    └── 1746/             # Complaint data
```

## License

MIT

## Contributing

Contributions are welcome. Please open an issue or submit a pull request.

## Acknowledgments

- Rio de Janeiro GTFS data
- 1746 Citizen Service System
- Neo4j Graph Data Science Library
