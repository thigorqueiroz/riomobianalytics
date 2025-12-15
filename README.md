# RioMobiAnalytics: Technical Documentation

## Table of Contents
1. [Project Overview](#project-overview)
2. [Hybrid Database Architecture](#hybrid-database-architecture)
3. [Neo4j Graph Model](#neo4j-graph-model)
4. [MongoDB Document Model](#mongodb-document-model)
5. [Data Flow Pipeline](#data-flow-pipeline)
6. [Neo4j Core Concepts Demonstrated](#neo4j-core-concepts-demonstrated)
7. [Key Cypher Queries Explained](#key-cypher-queries-explained)
8. [Graph Algorithms](#graph-algorithms)
9. [Risk Scoring Methodology](#risk-scoring-methodology)
10. [Performance Considerations](#performance-considerations)

---

## Project Overview

RioMobiAnalytics is an academic project demonstrating advanced graph database concepts using Neo4j in combination with MongoDB. The system analyzes Rio de Janeiro's public transit network by integrating:

- **GTFS (General Transit Feed Specification)** data representing the transit network
- **1746 citizen complaints** data representing service issues

**Core Problem**: Identify high-risk transit stops by correlating geographic proximity of complaints with network topology and analyzing structural importance of stops in the transit graph.

**Why Two Databases?**
- **MongoDB**: Optimized for geospatial queries and storing raw, semi-structured complaint data
- **Neo4j**: Optimized for graph traversal, relationship queries, and network analysis

---

## Hybrid Database Architecture

### Architecture Decision Rationale

```
┌─────────────────────────────────────────────────────────────┐
│                     Data Sources                             │
│  ┌──────────────────┐         ┌─────────────────────┐      │
│  │   GTFS Files     │         │  1746 Complaints    │      │
│  │   (CSV/ZIP)      │         │      (CSV)          │      │
│  └──────────────────┘         └─────────────────────┘      │
│           │                              │                   │
└───────────┼──────────────────────────────┼──────────────────┘
            │                              │
            ▼                              ▼
   ┌────────────────┐           ┌──────────────────┐
   │     Neo4j      │           │     MongoDB      │
   │  Graph Model   │◄──────────│  Document Store  │
   │                │   Sync    │                  │
   │ • Stops        │           │ • Complaints     │
   │ • Routes       │           │ • Geospatial     │
   │ • Trips        │           │   Index          │
   │ • Connections  │           │ • Sync Flag      │
   │ • Relationships│           │                  │
   └────────────────┘           └──────────────────┘
            │                              │
            └──────────────┬───────────────┘
                           ▼
                    ┌──────────────┐
                    │  Analytics   │
                    │   Layer      │
                    └──────────────┘
```

### MongoDB Responsibilities

1. **Primary Storage**: Raw complaint data with all original fields
2. **Geospatial Indexing**: 2dsphere index on location field for proximity queries
3. **Sync Management**: Tracks which complaints have been synced to Neo4j
4. **Data Validation**: Handles CSV format detection and column mapping

**Why MongoDB for Complaints?**
- Geospatial queries (`$near`, `$geoWithin`) are highly optimized
- Flexible schema accommodates different CSV formats
- Efficient for incremental data loading (duplicate detection via unique index)
- Fast for simple aggregations (complaints by category, status)

### Neo4j Responsibilities

1. **Graph Representation**: Models transit network as nodes and relationships
2. **Network Analysis**: Calculates centrality, PageRank, communities
3. **Risk Scoring**: Combines complaints with network topology
4. **Relationship Queries**: Finds paths, connected components, affected routes

**Why Neo4j for Transit Network?**
- Natural representation of "Stop A connects to Stop B"
- Efficient traversal queries (find all stops on a route, shortest paths)
- Built-in graph algorithms (centrality, community detection)
- Relationship properties (distance, travel time, risk-adjusted cost)

---

## Neo4j Graph Model

### Node Types (Labels)

#### 1. Stop Node
Represents a physical transit stop location.

```cypher
(:Stop {
  id: String,                      // Unique stop identifier from GTFS
  name: String,                    // Human-readable stop name
  lat: Float,                      // Latitude
  lon: Float,                      // Longitude
  wheelchair_accessible: Boolean,

  // Calculated Risk Metrics
  risk_score: Float,               // 0.0 - 1.0 normalized risk
  risk_level: String,              // 'Alto', 'Medio', 'Baixo'
  total_reclamacoes: Integer,      // Total complaints within radius
  reclamacoes_abertas: Integer,    // Open complaints

  // Graph Analytics Results
  betweenness_centrality: Float,   // Structural importance
  pagerank: Float,                 // Network importance
  community_id: Integer,           // Community assignment

  created_at: DateTime,
  last_risk_update: DateTime
})
```

**Key Concept**: Stops are the primary nodes because they are the connection points in the transit network. Every route passes through stops, and every complaint affects stops.

#### 2. Route Node
Represents a transit line (bus route, metro line, etc.).

```cypher
(:Route {
  id: String,
  short_name: String,             // e.g., "474"
  long_name: String,              // e.g., "Urca - Central"
  type: String,                   // Bus, Metro, BRT
  color: String,                  // Hex color for visualization

  // Aggregated Metrics
  avg_risk_score: Float,
  total_stops: Integer,
  high_risk_stops: Integer        // Count with risk >= 0.6
})
```

#### 3. Trip Node
Represents a specific trip instance of a route.

```cypher
(:Trip {
  id: String,
  route_id: String,               // Foreign key to Route
  headsign: String,               // Destination display
  direction: Integer,             // 0 or 1 (outbound/inbound)
  service_type: String            // weekday, weekend, etc.
})
```

**Why separate Trips from Routes?** In GTFS, a single route can have multiple trips with different stop sequences (express vs local, different times of day). This allows accurate modeling of the actual service.

#### 4. Reclamacao (Complaint) Node
Represents a citizen complaint synced from MongoDB.

```cypher
(:Reclamacao {
  id: String,                     // "REC_{protocolo}"
  protocolo: String,              // Original complaint ID
  data_abertura: DateTime,
  servico: String,                // Category (normalized)
  descricao: String,
  status: String,                 // 'Aberto', 'Em Atendimento', 'Fechado'
  lat: Float,
  lon: Float,
  peso: Float,                    // Category weight
  criticidade: String,            // 'Alta', 'Média', 'Baixa'
  bairro: String
})
```

#### 5. Categoria Node
Aggregates complaints by service category.

```cypher
(:Categoria {
  nome: String,                   // e.g., 'Segurança Pública'
  peso_base: Float,               // Base weight for risk calculation
  total_ocorrencias: Integer      // Total complaints in this category
})
```

#### 6. Neighborhood Node
Geographic regions for spatial aggregation.

```cypher
(:Neighborhood {
  name: String,
  regiao: String,                 // Zona Sul, Norte, Oeste, Centro
  populacao: Integer,
  total_stops: Integer,
  total_reclamacoes: Integer,
  avg_risk_score: Float
})
```

### Relationship Types

#### 1. CONNECTS_TO
Links consecutive stops on a route. This is the **core relationship** for network analysis.

```cypher
(:Stop)-[:CONNECTS_TO {
  route_id: String,               // Which route creates this connection
  distance_meters: Float,         // Physical distance
  sequence: Integer,              // Order in trip
  travel_time_seconds: Integer,   // Estimated travel time

  // Risk-Adjusted Metrics
  combined_risk: Float,           // (source_risk + target_risk) / 2
  risk_adjusted_cost: Float       // distance * (1 + combined_risk)
}]->(:Stop)
```

**Key Concept - Risk-Adjusted Cost**: Traditional routing finds shortest paths by distance. This system calculates a **risk-adjusted cost** that makes high-risk paths "more expensive" to traverse, enabling queries like "find safest path from A to B."

**Formula**:
```
risk_adjusted_cost = distance_meters × (1 + combined_risk)
```

If two stops each have risk_score = 0.8:
```
combined_risk = (0.8 + 0.8) / 2 = 0.8
risk_adjusted_cost = 1000m × (1 + 0.8) = 1800m
```

This makes the connection "feel" 80% longer due to risk.

#### 2. SERVES
Links routes to the stops they serve.

```cypher
(:Route)-[:SERVES {
  total_trips_daily: Integer,     // How many trips stop here
  avg_frequency_minutes: Integer  // Average time between trips
}]->(:Stop)
```

**Purpose**: Quickly find "which routes serve this stop?" or "which stops does this route serve?" without traversing all trips.

#### 3. HAS_STOP
Links trips to stops in sequence.

```cypher
(:Trip)-[:HAS_STOP {
  stop_sequence: Integer,         // Order: 1, 2, 3, ...
  arrival_time: String,           // "08:30:00"
  departure_time: String          // "08:31:00"
}]->(:Stop)
```

**Key Concept**: This relationship enables building CONNECTS_TO relationships by finding sequential stops within the same trip.

#### 4. BELONGS_TO
Links trips to their parent route.

```cypher
(:Trip)-[:BELONGS_TO]->(:Route)
```

#### 5. AFFECTS
Links complaints to nearby stops (within 100m by default).

```cypher
(:Reclamacao)-[:AFFECTS {
  distance_meters: Float,         // Distance from complaint to stop
  impact_level: String,           // Criticidade of complaint
  risk_contribution: Float,       // peso value
  started_affecting: DateTime
}]->(:Stop)
```

**Key Concept - Spatial Linking**: This is created during sync using Neo4j's `point.distance()` function:

```cypher
MATCH (s:Stop)
WHERE point.distance(
  point({latitude: $complaint_lat, longitude: $complaint_lon}),
  point({latitude: s.lat, longitude: s.lon})
) <= 100  // MAX_DISTANCE_AFFECTS_METERS
MERGE (rec)-[:AFFECTS]->(s)
```

A single complaint can affect multiple stops if they're all within 100m.

#### 6. HAS_TYPE
Links complaints to their category.

```cypher
(:Reclamacao)-[:HAS_TYPE]->(:Categoria)
```

#### 7. CLUSTERS_WITH
Links similar complaints that occur close together in time and space.

```cypher
(:Reclamacao)-[:CLUSTERS_WITH {
  spatial_proximity_meters: Float,    // Distance between complaints
  temporal_proximity_hours: Integer   // Hours between occurrences
}]->(:Reclamacao)
```

**Purpose**: Identify systemic problems (e.g., 10 lighting complaints in the same area within a week might indicate a broken street light cluster affecting multiple stops).

---

## MongoDB Document Model

### reclamacoes_1746_raw Collection

```javascript
{
  _id: ObjectId("..."),
  protocolo: "2024001234",           // Unique complaint ID
  data_abertura: ISODate("2024-01-15T14:30:00Z"),
  servico: "Segurança Pública",      // Normalized category
  descricao: "Falta de iluminação...",
  status: "Aberto",
  lat: -22.9068,
  lon: -43.1729,
  peso: 1.5,                         // From CATEGORIA_PESOS
  criticidade: "Alta",               // Normalized
  bairro: "Copacabana",

  // Geospatial Index Field
  localizacao: {
    type: "Point",
    coordinates: [-43.1729, -22.9068]  // [longitude, latitude]
  },

  // Sync Management
  synced_to_neo4j: false,
  sync_timestamp: ISODate("2024-01-15T15:00:00Z"),
  imported_at: ISODate("2024-01-15T14:45:00Z")
}
```

### Indexes

```javascript
// Unique constraint on complaint ID
db.reclamacoes_1746_raw.createIndex({ "protocolo": 1 }, { unique: true })

// Sync queue index
db.reclamacoes_1746_raw.createIndex({ "synced_to_neo4j": 1 })

// Date range queries
db.reclamacoes_1746_raw.createIndex({ "data_abertura": 1 })

// Geospatial queries
db.reclamacoes_1746_raw.createIndex({ "localizacao": "2dsphere" })
```

**Key Concept - 2dsphere Index**: Enables spherical geometry queries on Earth's surface. This is crucial for finding "all complaints within 100m of a point."

---

## Data Flow Pipeline

### Pipeline Execution Order

The ETL pipeline must run in this specific order due to dependencies:

```
┌─────────────────────────────────────────────────────────────┐
│ 01_setup_databases.py                                        │
│ • Creates MongoDB indexes                                    │
│ • Creates Neo4j constraints and indexes                      │
│ • Clears existing Neo4j data                                 │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 02_load_gtfs_to_neo4j.py                                    │
│ • Loads Stops, Routes, Trips                                 │
│ • Creates BELONGS_TO relationships                           │
│ • Creates CONNECTS_TO relationships (from stop sequences)    │
│ • Creates SERVES relationships                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 03_load_1746_to_mongodb.py                                  │
│ • Loads complaints into MongoDB                              │
│ • Normalizes categories and criticality                      │
│ • Creates GeoJSON location field                             │
│ • Sets synced_to_neo4j = false                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 04_sync_1746_to_neo4j.py                                    │
│ • Queries MongoDB for unsynced complaints                    │
│ • Creates Reclamacao nodes in Neo4j                          │
│ • Creates AFFECTS relationships (geospatial)                 │
│ • Creates Categoria nodes and HAS_TYPE relationships         │
│ • Updates synced_to_neo4j = true in MongoDB                  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 05_calculate_metrics.py                                     │
│ • Calculates risk scores for stops                           │
│ • Updates risk_adjusted_cost on CONNECTS_TO relationships    │
│ • Aggregates metrics to routes                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 06_run_analyses.py                                          │
│ • Creates graph projection for GDS algorithms                │
│ • Calculates betweenness centrality                          │
│ • Detects communities (Louvain)                              │
│ • Calculates PageRank                                        │
│ • Identifies complaint clusters                              │
└─────────────────────────────────────────────────────────────┘
```

### Detailed Step-by-Step Process

#### Step 1: Database Setup (01_setup_databases.py)

**Neo4j Constraints**:
```cypher
// Ensures no duplicate stops
CREATE CONSTRAINT stop_id_unique IF NOT EXISTS
FOR (s:Stop) REQUIRE s.id IS UNIQUE

// Enables fast lookups
CREATE INDEX stop_name IF NOT EXISTS
FOR (s:Stop) ON (s.name)

// Risk queries
CREATE INDEX stop_risk IF NOT EXISTS
FOR (s:Stop) ON (s.risk_score)

// Geospatial point index
CREATE INDEX stop_location IF NOT EXISTS
FOR (s:Stop) ON (s.lat, s.lon)
```

**Why Constraints Matter**: Without unique constraints, you could accidentally create duplicate stops with the same ID, breaking the graph model.

#### Step 2: GTFS Loading (02_load_gtfs_to_neo4j.py)

**Creating CONNECTS_TO Relationships**:

This is the most complex part of GTFS loading. The logic:

1. Find all stops in a trip in sequence order
2. Connect each stop to the next stop
3. Calculate distance using Neo4j's spatial functions

```cypher
MATCH (t:Trip)-[hs1:HAS_STOP]->(s1:Stop)
MATCH (t)-[hs2:HAS_STOP]->(s2:Stop)
WHERE hs2.stop_sequence = hs1.stop_sequence + 1  // Next stop

WITH s1, s2, t, hs1.stop_sequence AS sequence,
     point({latitude: s1.lat, longitude: s1.lon}) AS p1,
     point({latitude: s2.lat, longitude: s2.lon}) AS p2

MERGE (s1)-[c:CONNECTS_TO {route_id: t.route_id}]->(s2)
ON CREATE SET
    c.distance_meters = round(point.distance(p1, p2)),
    c.sequence = sequence,
    c.travel_time_seconds = 120,
    c.risk_adjusted_cost = round(point.distance(p1, p2))
```

**Key Concept - point.distance()**: Neo4j's built-in function calculates great-circle distance (haversine formula) between two points on Earth's surface. Returns meters by default.

**Why MERGE instead of CREATE?**: Multiple trips may create the same connection (Stop A → Stop B on Route 474). MERGE ensures we create it only once.

#### Step 3: Complaint Loading (03_load_1746_to_mongodb.py)

**Category Normalization**:

```python
def normalize_categoria(self, servico):
    for categoria in config.CATEGORIA_PESOS.keys():
        if categoria.lower() in servico.lower():
            return categoria
    return 'Outros'
```

This maps various complaint descriptions to standardized categories:
- "Policiamento" → "Segurança Pública"
- "Luminária quebrada" → "Iluminação Pública"
- "Buraco na via" → "Conservação de Vias"

**GeoJSON Format for MongoDB**:

```python
doc['localizacao'] = {
    'type': 'Point',
    'coordinates': [longitude, latitude]  # Note: lon, lat order!
}
```

**Common Mistake**: GeoJSON uses [longitude, latitude], while most systems use [latitude, longitude]. MongoDB requires GeoJSON format for 2dsphere indexes.

#### Step 4: Sync to Neo4j (04_sync_1746_to_neo4j.py)

**The Sync Query** (most complex query in the system):

```cypher
MERGE (rec:Reclamacao {id: $rec_id})
SET rec.protocolo = $protocolo,
    rec.data_abertura = datetime($data_abertura),
    rec.servico = $servico,
    rec.status = $status,
    rec.lat = $lat,
    rec.lon = $lon,
    rec.peso = $peso,
    rec.criticidade = $criticidade

MERGE (cat:Categoria {nome: $servico})
ON CREATE SET
    cat.peso_base = $peso,
    cat.total_ocorrencias = 0
ON MATCH SET
    cat.total_ocorrencias = cat.total_ocorrencias + 1

MERGE (rec)-[:HAS_TYPE]->(cat)

WITH rec
MATCH (s:Stop)
WHERE point.distance(
  point({latitude: rec.lat, longitude: rec.lon}),
  point({latitude: s.lat, longitude: s.lon})
) <= $max_distance  // 100m

MERGE (rec)-[a:AFFECTS]->(s)
SET a.distance_meters = round(point.distance(
      point({latitude: rec.lat, longitude: rec.lon}),
      point({latitude: s.lat, longitude: s.lon})
    )),
    a.impact_level = rec.criticidade,
    a.risk_contribution = rec.peso,
    a.started_affecting = rec.data_abertura

WITH s
SET s.total_reclamacoes = s.total_reclamacoes + 1

RETURN count(s) AS paradas_afetadas
```

**What This Query Does**:

1. **Creates/updates complaint node** (MERGE is idempotent)
2. **Manages category node** (increments counter if exists, creates if new)
3. **Links complaint to category**
4. **Finds all stops within 100m** using spatial distance function
5. **Creates AFFECTS relationships** with distance and risk data
6. **Increments complaint counter** on each affected stop
7. **Returns count** for logging

**Key Neo4j Concept - Transaction Composition**: This single query does multiple operations atomically. Either all succeed, or all roll back.

#### Step 5: Risk Calculation (05_calculate_metrics.py)

**Stop Risk Score Query**:

```cypher
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
```

**Key Concepts**:

1. **Temporal Filtering**: Only recent complaints (30 days) affect risk
2. **Status Filtering**: Closed complaints don't contribute
3. **Risk Formula**: `risk_sum / (risk_sum + 10.0)` creates a normalized score (0-1) with diminishing returns

**Why This Formula?**

```
risk_sum = 1  → score = 1/11  = 0.091
risk_sum = 5  → score = 5/15  = 0.333
risk_sum = 10 → score = 10/20 = 0.500
risk_sum = 20 → score = 20/30 = 0.667
risk_sum = 50 → score = 50/60 = 0.833
```

The "+10" denominator prevents a single high-weight complaint from maxing out the score. It requires sustained problems to reach high risk.

**Connection Cost Update**:

```cypher
MATCH (s1:Stop)-[c:CONNECTS_TO]->(s2:Stop)
SET c.combined_risk = (s1.risk_score + s2.risk_score) / 2,
    c.risk_adjusted_cost = c.distance_meters * (1 + (s1.risk_score + s2.risk_score) / 2)
```

This propagates risk from stops to connections, enabling safety-aware routing.

#### Step 6: Graph Analytics (06_run_analyses.py)

**Creating Graph Projection**:

```cypher
CALL gds.graph.project(
  'transportNetwork',
  'Stop',
  'CONNECTS_TO',
  {
    nodeProperties: ['risk_score', 'lat', 'lon'],
    relationshipProperties: ['distance_meters', 'risk_adjusted_cost']
  }
)
```

**Key Concept - GDS Library**: Neo4j's Graph Data Science library requires an in-memory projection of the graph. This is separate from the stored graph and optimized for algorithm execution.

**Why Project?** Algorithms run 10-100x faster on projections because:
- Data is stored in compressed columnar format
- No transaction overhead
- Optimized data structures for graph traversal

---

## Neo4j Core Concepts Demonstrated

### 1. Cypher Query Language

**Declarative Pattern Matching**:

```cypher
// Find all stops on Route 474
MATCH (r:Route {short_name: '474'})-[:SERVES]->(s:Stop)
RETURN s.name, s.risk_score
ORDER BY s.risk_score DESC
```

This is declarative (what you want) vs imperative (how to get it). You describe the pattern, Neo4j finds matches.

**Variable-Length Paths**:

```cypher
// Find all stops within 3 connections
MATCH (start:Stop {id: 'ABC123'})-[:CONNECTS_TO*1..3]->(nearby:Stop)
RETURN nearby.name, LENGTH(path) as hops
```

`*1..3` means "1 to 3 relationships of type CONNECTS_TO."

### 2. Spatial Functions

```cypher
// All stops within 500m of Copacabana
WITH point({latitude: -22.9707, longitude: -43.1823}) AS copacabana
MATCH (s:Stop)
WHERE point.distance(copacabana, point({latitude: s.lat, longitude: s.lon})) <= 500
RETURN s.name
```

### 3. Temporal Functions

```cypher
// Complaints in the last 7 days
MATCH (rec:Reclamacao)
WHERE rec.data_abertura >= datetime() - duration({days: 7})
RETURN count(rec)
```

### 4. Aggregation

```cypher
// Count stops per risk level
MATCH (s:Stop)
RETURN s.risk_level, count(*) as total
ORDER BY total DESC
```

### 5. Conditional Logic

```cypher
// Classify stops by importance
MATCH (s:Stop)
RETURN s.name,
       CASE
         WHEN s.centrality > 0.05 AND s.risk_score > 0.6 THEN 'CRITICAL'
         WHEN s.centrality > 0.05 THEN 'Structurally Important'
         WHEN s.risk_score > 0.6 THEN 'High Risk'
         ELSE 'Normal'
       END AS classification
```

### 6. Relationship Properties

```cypher
// Find connections with high risk adjustment
MATCH (s1:Stop)-[c:CONNECTS_TO]->(s2:Stop)
WHERE c.risk_adjusted_cost / c.distance_meters > 1.5  // 50% increase
RETURN s1.name, s2.name, c.combined_risk
ORDER BY c.combined_risk DESC
LIMIT 10
```

### 7. Shortest Path (Weighted)

```cypher
// Safest path between two stops
MATCH (start:Stop {id: 'A'}), (end:Stop {id: 'B'})
CALL gds.shortestPath.dijkstra.stream('transportNetwork', {
  sourceNode: start,
  targetNode: end,
  relationshipWeightProperty: 'risk_adjusted_cost'
})
YIELD totalCost, nodeIds, costs
RETURN totalCost, nodeIds
```

Uses Dijkstra's algorithm with risk-adjusted costs instead of pure distance.

---

## Graph Algorithms

### 1. Betweenness Centrality

**What it Measures**: How many shortest paths pass through this node.

**Formula**: For node v:
```
BC(v) = Σ (σ_st(v) / σ_st)
```
Where σ_st = total shortest paths from s to t, and σ_st(v) = paths that pass through v.

**Implementation**:

```cypher
CALL gds.betweenness.write('transportNetwork', {
  writeProperty: 'betweenness_centrality'
})
```

**Interpretation**:
- **High centrality** = structural bottleneck, many routes depend on this stop
- If a high-centrality stop fails, it impacts many trips
- High centrality + high risk = **critical vulnerability**

**Example**: A transfer hub where 5 bus routes meet will have high centrality because all paths using those routes pass through it.

### 2. Louvain Community Detection

**What it Finds**: Groups of densely connected stops that form "communities."

**Algorithm**:
1. Start with each node in its own community
2. Move nodes to neighboring communities to maximize modularity
3. Aggregate communities and repeat
4. Continue until modularity can't be improved

**Implementation**:

```cypher
CALL gds.louvain.write('transportNetwork', {
  writeProperty: 'community_id',
  relationshipWeightProperty: 'distance_meters'
})
```

**Interpretation**:
- Stops in the same community are well-connected (many routes between them)
- Communities often correspond to geographic neighborhoods
- Useful for analyzing "if this community has high risk, is it isolated or does it spread?"

**Why weight by distance?** Stops close together are more likely to be in the same functional neighborhood.

### 3. PageRank

**What it Measures**: Importance based on incoming connections.

**Formula**: Iterative calculation:
```
PR(v) = (1-d)/N + d × Σ(PR(u) / OutDegree(u))
```
Where d = damping factor (0.85), N = total nodes.

**Implementation**:

```cypher
CALL gds.pageRank.write('transportNetwork', {
  writeProperty: 'pagerank',
  dampingFactor: 0.85,
  maxIterations: 20
})
```

**Interpretation**:
- **High PageRank** = many stops connect TO this stop, or it's connected to by important stops
- Major transfer hubs have high PageRank
- Different from centrality: PageRank cares about being a destination, centrality about being on paths

**Example**: A central station where many routes terminate will have high PageRank even if paths don't go through it (unlike centrality).

### 4. Clustering Analysis

**Pattern**: Find complaints that cluster in space and time.

```cypher
MATCH (r1:Reclamacao), (r2:Reclamacao)
WHERE id(r1) < id(r2)
  AND r1.servico = r2.servico
  AND point.distance(
    point({latitude: r1.lat, longitude: r1.lon}),
    point({latitude: r2.lat, longitude: r2.lon})
  ) <= 200  // Within 200m
  AND duration.between(r1.data_abertura, r2.data_abertura).days <= 7  // Within 7 days

MERGE (r1)-[c:CLUSTERS_WITH]->(r2)
SET c.spatial_proximity_meters = round(point.distance(...)),
    c.temporal_proximity_hours = duration.between(...).hours
```

**Interpretation**:
- Complaint clusters suggest systemic issues (not isolated incidents)
- Can identify "hot spots" that need intervention
- Multiple complaints about lighting in one area = broken infrastructure

---

## Key Cypher Queries Explained

### Query 1: Find Most Vulnerable Routes

**Problem**: Which bus routes pass through the most high-risk stops?

```cypher
MATCH (r:Route)-[:SERVES]->(s:Stop)
WHERE s.risk_score >= 0.6
WITH r, collect(s.name) as high_risk_stops, count(s) as risk_count
WHERE risk_count >= 3
RETURN r.short_name, r.long_name, risk_count, high_risk_stops
ORDER BY risk_count DESC
LIMIT 10
```

**Breakdown**:
1. Find routes and stops they serve
2. Filter to high-risk stops (≥0.6)
3. Group by route, collect stop names, count
4. Filter to routes with 3+ high-risk stops
5. Return top 10

**Use Case**: Prioritize route inspection, consider re-routing.

### Query 2: Safest Path Between Two Points

```cypher
MATCH (start:Stop {name: 'Copacabana'}), (end:Stop {name: 'Centro'})
MATCH path = shortestPath((start)-[:CONNECTS_TO*]-(end))
WITH path,
     nodes(path) as stops,
     reduce(totalRisk = 0.0, s in nodes(path) | totalRisk + s.risk_score) as pathRisk
RETURN stops, pathRisk
ORDER BY pathRisk ASC
LIMIT 1
```

**Breakdown**:
1. Find start and end stops by name
2. Find shortest path (fewest hops)
3. Calculate total risk = sum of all stop risk scores
4. Return path with lowest risk

**Limitation**: This finds shortest path first, then calculates risk. Better: use weighted shortest path with `risk_adjusted_cost`.

### Query 3: Identify Transit Deserts with High Complaints

**Problem**: Areas with many complaints but few transit options.

```cypher
MATCH (s:Stop)
WITH s,
     s.total_reclamacoes as complaints,
     size((s)<-[:SERVES]-(:Route)) as route_count
WHERE complaints > 5 AND route_count < 3
RETURN s.name, s.lat, s.lon, complaints, route_count, s.risk_score
ORDER BY s.risk_score DESC
```

**Breakdown**:
1. For each stop, count complaints and serving routes
2. Filter: high complaints (>5), few routes (<3)
3. Return with coordinates for mapping

**Use Case**: Identify underserved high-risk areas, prioritize service expansion.

### Query 4: Cascade Analysis - If This Stop Fails

**Problem**: If stop X becomes unusable, which routes are affected?

```cypher
MATCH (critical:Stop {id: 'STOP_123'})
MATCH (r:Route)-[:SERVES]->(critical)
WITH r, critical
MATCH (r)-[:SERVES]->(other:Stop)
WHERE other <> critical
RETURN r.short_name as route,
       count(other) as remaining_stops,
       collect(other.name)[0..5] as sample_stops
```

**Breakdown**:
1. Identify the critical stop
2. Find routes serving it
3. For each route, count OTHER stops (excluding critical)
4. Return impact assessment

**Use Case**: Emergency planning, maintenance scheduling.

### Query 5: Temporal Risk Trends

**Problem**: Is risk increasing or decreasing at this stop?

```cypher
MATCH (s:Stop {id: 'STOP_123'})<-[a:AFFECTS]-(rec:Reclamacao)
WITH s,
     rec.data_abertura.year as year,
     rec.data_abertura.month as month,
     sum(a.risk_contribution) as monthly_risk
RETURN year, month, monthly_risk
ORDER BY year, month
```

**Breakdown**:
1. Find complaints affecting the stop
2. Extract year and month from complaint date
3. Sum risk contribution per month
4. Return time series

**Use Case**: Track effectiveness of interventions, predict future risk.

---

## Risk Scoring Methodology

### Design Rationale and Threshold Philosophy

**Core Objective**: Create a quantitative measure of transit stop vulnerability that balances:
- **Frequency**: How many complaints affect a stop
- **Severity**: Which types of complaints and their urgency
- **Recency**: Recent issues are more relevant than historical ones
- **Proximity**: Only complaints geographically close to the stop matter
- **Feasibility**: Thresholds must be actionable for urban planners

### Multi-Factor Risk Formula

**Components**:

1. **Category Weight** (peso): Different complaint types have different severity and impact
   ```python
   CATEGORIA_PESOS = {
       'Segurança Pública': 1.5,      # Highest: directly affects passenger safety
       'Trânsito e Transporte': 0.8,  # Service reliability issues
       'Iluminação Pública': 0.6,     # Safety at night, moderate impact
       'Conservação de Vias': 0.5,    # Infrastructure quality
       'Limpeza Urbana': 0.4,         # Environmental quality, lower direct impact
       'Outros': 0.3                  # Uncategorized, assumed lower severity
   }
   ```

   **Rationale**:
   - Security complaints (theft, violence) directly threaten passenger safety → highest weight
   - Service issues prevent people from using transit → high weight
   - Lighting affects perceived safety but not immediate danger → medium weight
   - Infrastructure and cleanliness affect experience but not immediate safety → lower weight
   - Weights are relative; absolute values matter less than the hierarchy

2. **Criticality Multiplier**: Complaint urgency assigned by the 1746 system
   ```python
   CRITICIDADE_MAP = {
       'Alta': 1.5,    # Urgent issues requiring immediate attention
       'Média': 1.0,   # Standard baseline
       'Baixa': 0.5    # Low urgency issues
   }
   ```

   **Rationale**:
   - Multiplier amplifies weight when system flagged complaint as urgent
   - Baseline = 1.0 (no amplification) for medium criticality
   - High criticality = 1.5x worse than medium
   - Low criticality = 0.5x severity of medium
   - Uses multiplication to scale within category, not to override category weight

3. **Individual Contribution**:
   ```
   risk_contribution = peso × criticidade
   ```

   **Example combinations**:
   ```
   Segurança (Alta)  = 1.5 × 1.5 = 2.25  (worst case)
   Segurança (Média) = 1.5 × 1.0 = 1.50
   Segurança (Baixa) = 1.5 × 0.5 = 0.75
   Iluminação (Alta) = 0.6 × 1.5 = 0.90
   Limpeza (Alta)    = 0.4 × 1.5 = 0.60
   ```

4. **Aggregated Risk Sum**:
   ```
   risk_sum = Σ(risk_contribution for all complaints within 100m)
   ```

   **Why aggregation matters**:
   - Single incident: risk_sum = 2.25 (not critical)
   - Pattern of issues: risk_sum = 2.25 × 5 = 11.25 (critical)
   - Distinguishes isolated complaints from systemic problems
   - Lower bound of ~0.3, no upper bound (unbounded sum allows detection of extreme risk)

5. **Normalized Risk Score** (0-1 scale):
   ```
   risk_score = risk_sum / (risk_sum + 10.0)
   ```

   **Why This Formula?** (Sigmoid-like normalization)

   This formula creates a normalized score with specific mathematical properties:

   ```
   risk_sum = 0   → score = 0.000  (no complaints)
   risk_sum = 1   → score = 0.091  (1 low complaint)
   risk_sum = 5   → score = 0.333  (multiple complaints)
   risk_sum = 10  → score = 0.500  (moderate problem)
   risk_sum = 20  → score = 0.667  (serious problem)
   risk_sum = 50  → score = 0.833  (critical)
   risk_sum = 100 → score = 0.909  (extreme)
   ```

   **Mathematical Properties**:
   - **Bounded**: Always produces 0 ≤ score < 1 (asymptotically approaches 1)
   - **Diminishing Returns**: Adding complaints has decreasing marginal impact
     - First 5 units of risk_sum: gain 0.333 points
     - Next 10 units of risk_sum: gain only 0.167 points (half the gain)
   - **No Saturation**: Never completely max out (no stop is "definitely safe")
   - **Requires Accumulation**: Single complaint can't cause high risk; requires pattern

   **Tuning Parameter Analysis**:

   The "+10" denominator is the key tuning parameter. Why 10?

   ```
   With "+10": A stop needs risk_sum ≈ 15 to reach high risk (0.6 score)
   With "+5":  A stop needs risk_sum ≈ 7.5 to reach high risk (more sensitive)
   With "+20": A stop needs risk_sum ≈ 30 to reach high risk (less sensitive)
   ```

   - **+10 is moderate**: Balances sensitivity to new problems with stability
   - **Too low (+5)**: Few complaints create high risk → volatility, false alarms
   - **Too high (+20)**: Many complaints needed for action → slow response
   - **Chosen value**: Requires 5-10 medium-severity complaints to be flagged high-risk

### Risk Level Thresholds

```cypher
CASE
  WHEN risk_score >= 0.6 THEN 'Alto'      # High risk
  WHEN risk_score >= 0.333 THEN 'Medio'   # Medium risk
  ELSE 'Baixo'                            # Low risk
END
```

**Threshold Rationale**:

1. **High Risk (≥ 0.6)**
   - Corresponds to risk_sum ≈ 15+ (5-10 significant complaints)
   - **Action**: Immediate inspection, prioritize for fixes
   - **Rationale**: 60% of maximum achievable score indicates systemic problem
   - **Affected Population**: Typically 5+ active complaints suggests widespread issue

2. **Medium Risk (≥ 0.333)**
   - Corresponds to risk_sum ≈ 5 (3-5 moderate complaints or 1-2 serious ones)
   - **Action**: Monitor closely, plan repairs
   - **Rationale**: 33% score indicates notable but not critical problems
   - **Affected Population**: Small but consistent group of complaints

3. **Low Risk (< 0.333)**
   - Corresponds to risk_sum < 5 (1-2 complaints or isolated incidents)
   - **Action**: No immediate action, track for patterns
   - **Rationale**: Sporadic complaints, likely isolated incidents
   - **Affected Population**: One or two people affected, not systemic

### Example Calculation

**Scenario**: Stop has 3 nearby complaints:

1. Segurança Pública (Alta): 1.5 × 1.5 = 2.25
2. Iluminação Pública (Média): 0.6 × 1.0 = 0.60
3. Limpeza Urbana (Baixa): 0.4 × 0.5 = 0.20

```
risk_sum = 2.25 + 0.60 + 0.20 = 3.05
risk_score = 3.05 / (3.05 + 10.0) = 3.05 / 13.05 = 0.234
risk_level = 'Baixo' (< 0.333)
```

**If we add 5 more Segurança Pública (Alta) complaints**:

```
risk_sum = 3.05 + (5 × 2.25) = 14.30
risk_score = 14.30 / (14.30 + 10.0) = 14.30 / 24.30 = 0.588
risk_level = 'Medio' (≥ 0.333, < 0.6)
```

**Key Insight**: Single complaint barely registers (0.234), but pattern of 8 complaints raises it to medium risk (0.588). This prevents reactive responses to noise while catching systemic issues.

### Spatial Filtering: 100-Meter Radius

Complaints are linked to stops within 100 meters:

```cypher
WHERE point.distance(
  point({latitude: rec.lat, longitude: rec.lon}),
  point({latitude: s.lat, longitude: s.lon})
) <= 100  // meters
```

**Rationale for 100m**:

1. **Urban Context**: Rio's bus stops are typically 200-500m apart
   - 100m is small enough to link to the specific stop, not the whole street
   - Large enough to capture complaints from nearby buildings/intersections

2. **Complaint Precision**: 1746 complaints often have imprecise location data
   - GPS from mobile may be off 50-100m
   - 100m accounts for this imprecision without over-linking

3. **Passenger Perspective**: People within 100m of a stop would use it
   - Problem at nearby intersection affects this stop's users
   - Beyond 100m, people would likely use different stop

4. **Balance**: 100m is conservative
   - Too small (50m): Miss legitimate stop-affecting issues
   - Too large (300m): Attribute problems to wrong stop
   - 100m is proven standard in urban accessibility metrics (100m = 1-2 min walk)

**Trade-off**: Some complaints might affect multiple overlapping stops, which is correct—if a problem spans an intersection, it affects several nearby stops.

### Temporal Filtering: 30-Day Window

Complaints older than 30 days are excluded from risk calculations:

```cypher
WHERE rec.data_abertura >= datetime() - duration({days: 30})
```

**Rationale for 30 days**:

1. **Problem Resolution**: Typical municipal repair cycles are 2-4 weeks
   - Issue reported → City reviews → Schedules repair → Completes work
   - By 30 days, properly tracked issues should be fixed or in progress

2. **Actionability**: Risk score should reflect current conditions
   - Old, unresolved complaints indicate bureaucratic failure, not current danger
   - Current score helps prioritize today's actions, not historical analysis

3. **Complaint Quality**: Older complaints have stale data
   - "Street light broken 2 months ago" might already be fixed
   - Status field may not be updated reliably
   - Recent complaints more reliable

4. **Prevent Accumulation**: Without decay, adding 1 old complaint is like adding new one
   - Unfair to stops with historical issues (even if resolved)
   - Creates "sticky" high risk that's hard to recover from

5. **Statistical Relevance**: 30 days = reasonable sample for patterns
   - Less than 7 days: Too noisy, random variations
   - More than 90 days: Misses recent deterioration
   - 30 days balances noise reduction with recency

**Trade-off**: Doesn't track long-term chronic problems
- Benefit: Focuses on current action items
- Cost: Historical context lost
- Mitigation: Could create separate "chronic issue" metric if needed

### Status Filtering: Open Complaints Only

Only complaints with status 'Aberto' (Open) or 'Em Atendimento' (In Progress) affect risk:

```cypher
WHERE rec.status IN ['Aberto', 'Em Atendimento']
```

**Rationale**:

1. **Unresolved Problems**: Closed/resolved issues no longer pose risk
   - Status 'Fechado' (Closed) = authority determined issue is resolved
   - Should not penalize a stop for fixed problems

2. **Current Conditions**: Risk score represents NOW, not history
   - If problem was fixed, current passengers don't face that risk
   - Keep historical data (for analysis) but exclude from current risk

3. **Motivation for Fixes**: Closed status = progress, removing weight
   - Gives city incentive to close complaints (mark resolved)
   - Positive feedback loop: fix problem → lower risk → look better

4. **Prevents Double-Counting**: Some systems create new complaint if reopened
   - Filtering by status prevents accumulating both old and new versions
   - Only active issues contribute to current risk

**Data Quality Issue**: Status field may not be reliably updated
- Some "closed" complaints were never actually fixed
- Some "open" issues have been waiting months
- **Mitigated by**: 30-day window (old issues drop naturally after 30 days anyway)
- **Better solution**: Use complaint resolution date when available

### Connection Cost Adjustment

Risk-adjusted costs propagate risk from stops to relationships:

```cypher
WITH c.distance_meters AS distance,
     (s1.risk_score + s2.risk_score) / 2 AS combined_risk
SET c.risk_adjusted_cost = distance × (1 + combined_risk)
```

**Example**:
```
Stops A→B: 1000m apart
Stop A risk: 0.2, Stop B risk: 0.8
combined_risk = (0.2 + 0.8) / 2 = 0.5
risk_adjusted_cost = 1000m × (1 + 0.5) = 1500m

This makes a high-risk path "feel" 50% longer
Routing algorithm avoids it when safer alternatives exist
```

**Rationale**:

1. **Safety-Aware Routing**: Different from "shortest path"
   - Pure distance routing ignores risk (unsafe for vulnerable populations)
   - Risk adjustment allows querying "safest path from A to B"

2. **Multiplicative Adjustment**: Preserves distance information
   - Risk doesn't replace distance, it modifies it
   - Still prefer nearby stops, but avoid dangerous ones
   - If both paths equally dangerous, pick shorter

3. **Averaging Stops**: Uses both endpoints' risk
   - Avoids high-risk stops on BOTH ends of connection
   - Traveling through high-risk areas increases perceived cost

4. **Unbounded Risk**: Cost can theoretically become very high
   - Combined_risk can exceed 1.0 if both stops have risk_score > 0.5
   - High-risk connections (1.5, 1.8x multiplier) strongly discouraged
   - But never completely blocked (1+risk is always positive)

---

## Summary: Risk Calculation Design Principles

| Principle | Mechanism | Benefit |
|-----------|-----------|---------|
| **Differentiate Severity** | Category weights (1.5 to 0.3) | Focus on serious issues |
| **Quantify Urgency** | Criticality multiplier (0.5 to 1.5) | Respect domain expertise |
| **Detect Patterns** | Aggregation (sum not just count) | Distinguish noise from systemic |
| **Normalize Scale** | Sigmoid formula (÷ risk_sum+10) | Bounded 0-1, diminishing returns |
| **Require Accumulation** | +10 denominator tuning | Avoid reactive responses |
| **Focus on Present** | 30-day temporal window | Ignore resolved/stale issues |
| **Exclude Resolved** | Status filtering | Don't penalize fixed problems |
| **Prioritize Current** | Only open/in-progress complaints | Risk reflects NOW situation |
| **Apply Spatial Context** | 100m radius | Link only genuinely affected stops |
| **Enable Routing** | Risk-adjusted costs | Support safety-aware planning |

These design choices create a system that:
- ✅ Responds to real systemic problems
- ✅ Ignores noise and isolated complaints
- ✅ Reflects current conditions, not history
- ✅ Guides actionable resource allocation
- ✅ Enables safety-aware transit routing

---

## Performance Considerations

### 1. Indexing Strategy

**Neo4j**:
- Unique constraints on IDs (also creates index)
- Range indexes on frequently filtered properties (risk_score, data_abertura)
- Composite index on (lat, lon) for spatial queries
- Full-text index on complaint descriptions

**MongoDB**:
- Unique index on protocolo (prevents duplicates)
- 2dsphere index on localizacao (geospatial queries)
- Compound index on (synced_to_neo4j, data_abertura) for sync queue

### 2. Batch Processing

**Loading GTFS stop_times.txt** (large file, ~1M records):

```python
batch_size = config.BATCH_SIZE  # 1000
for i in range(0, len(df), batch_size):
    batch = df.iloc[i:i+batch_size]
    for _, row in batch.iterrows():
        session.run("MERGE ...")
```

Commits every 1000 records instead of at the end, preventing transaction log overflow.

### 3. Graph Projection for Analytics

**Why Project?**

```cypher
// Without projection - slow
MATCH path = (s1:Stop)-[:CONNECTS_TO*1..5]->(s2:Stop)
WHERE s1.risk_score > 0.6 AND s2.risk_score > 0.6
RETURN count(path)
```

**With projection** - 10-100x faster:

```cypher
CALL gds.graph.project('transportNetwork', 'Stop', 'CONNECTS_TO')
// Now algorithms run on projected graph
```

### 4. Spatial Query Optimization

**Inefficient**:
```cypher
MATCH (s:Stop), (rec:Reclamacao)
WHERE point.distance(...) <= 100  // Cartesian product first!
```

**Efficient**:
```cypher
MATCH (rec:Reclamacao)
WITH rec
MATCH (s:Stop)
WHERE point.distance(...) <= 100  // Filtered per complaint
```

### 5. Avoiding Cartesian Products

**Bad** (creates every possible stop pair):
```cypher
MATCH (s1:Stop), (s2:Stop)
WHERE s1.id <> s2.id
AND point.distance(...) <= 500
```

**Good** (uses relationship to limit scope):
```cypher
MATCH (s1:Stop)-[:CONNECTS_TO*1..3]-(s2:Stop)
WHERE point.distance(...) <= 500
```

---

## Academic Learning Outcomes

This project demonstrates:

### Neo4j Concepts
- ✅ Graph modeling (nodes, relationships, properties)
- ✅ Cypher query language (MATCH, MERGE, WHERE, WITH)
- ✅ Indexing and constraints
- ✅ Spatial functions (point.distance)
- ✅ Temporal functions (datetime, duration)
- ✅ Path finding (shortest path, variable-length paths)
- ✅ Aggregations and grouping
- ✅ Graph algorithms (GDS library)
- ✅ Projections and in-memory graphs

### Database Design
- ✅ When to use graph vs document databases
- ✅ Hybrid architecture patterns
- ✅ Data synchronization between systems
- ✅ Geospatial indexing and queries
- ✅ Idempotent operations (MERGE)

### Real-World Applications
- ✅ Transit network analysis
- ✅ Risk assessment and scoring
- ✅ Spatial-temporal clustering
- ✅ Community detection
- ✅ Centrality analysis for infrastructure planning

---

## Further Exploration Ideas

1. **Shortest Path Variants**:
   - Implement A* algorithm with heuristic based on risk
   - Multi-criteria path finding (minimize time AND risk)

2. **Dynamic Risk Updates**:
   - Real-time complaint stream processing
   - Exponential decay instead of binary 30-day cutoff

3. **Predictive Analytics**:
   - Train model to predict future risk based on historical patterns
   - Identify stops likely to become high-risk

4. **Network Resilience**:
   - Simulate stop failures and measure network impact
   - Identify single points of failure

5. **Advanced GDS Algorithms**:
   - Node similarity (find stops with similar complaint patterns)
   - Link prediction (predict where new routes should be added)
   - Triangle counting (measure network clustering)

---

## Conclusion

RioMobiAnalytics demonstrates how Neo4j's graph model naturally represents transportation networks while MongoDB efficiently handles geospatial complaint data. The hybrid architecture leverages each database's strengths:

- **Neo4j**: Relationship-heavy queries, network analysis, graph algorithms
- **MongoDB**: Geospatial queries, flexible schema, fast inserts

The risk scoring methodology combines spatial proximity, complaint severity, and network topology to identify vulnerable transit infrastructure. Graph algorithms reveal structural importance (centrality), community structure (Louvain), and network influence (PageRank).

This academic project provides hands-on experience with:
- Production-grade graph database design
- Cypher query optimization
- Graph algorithm applications
- Hybrid database architectures
- Real-world transit analytics

The concepts learned here apply to any domain with networked data: social networks, supply chains, telecommunication networks, knowledge graphs, and more.
