# RioMobiAnalytics Web Application

Interactive web interface for visualizing and managing RioMobiAnalytics transit risk data.

## Features

### 1. Interactive Map
- View transit stops colored by risk level
- Display complaint locations on map
- Filter by risk level, category, and status
- Interactive markers with detailed information

### 2. Risk Dashboard
- Comprehensive analytics with interactive charts
- Stop risk analysis and distribution
- Route metrics and comparisons
- Complaint category breakdowns
- Top critical stops identification

### 3. Network Graph
- Interactive graph visualization of transit network
- Color nodes by risk, centrality, PageRank, or community
- Multiple layout algorithms (Spring, Kamada-Kawai, Circular)
- Network statistics and top connected nodes

### 4. Data Management
- Upload GTFS and complaint data files
- Trigger ETL pipeline steps individually or complete pipeline
- Monitor system status (MongoDB and Neo4j)
- View data directory contents

## Installation

1. Install web dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure MongoDB and Neo4j are running:
```bash
# Check MongoDB
mongosh

# Check Neo4j
cypher-shell
```

3. Load data using ETL pipeline:
```bash
./run_all.sh
```

## Running the Application

### Quick Start

```bash
./run_webapp.sh
```

The application will be available at: http://localhost:8501

### Manual Start

```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
streamlit run webapp/app.py
```

### Custom Port

```bash
streamlit run webapp/app.py --server.port=8080
```

## Configuration

The web app uses the same configuration as the ETL pipeline from `config.py`:

- MongoDB connection settings
- Neo4j connection settings
- Risk calculation parameters
- Data paths

Ensure your `.env` file is properly configured before running.

## Architecture

```
webapp/
├── app.py                      # Main entry point
├── pages/                      # Multi-page app
│   ├── 01_🗺️_Interactive_Map.py
│   ├── 02_📊_Risk_Dashboard.py
│   ├── 03_🕸️_Network_Graph.py
│   └── 04_📤_Data_Management.py
├── utils/                      # Utility modules
│   ├── db_connections.py       # Database connections
│   └── data_fetchers.py        # Data querying functions
└── static/                     # Static assets
```

## Features by Page

### Interactive Map
- **Folium** for interactive mapping
- Geospatial visualization of risk levels
- Complaint distribution maps
- Filter and search capabilities

### Risk Dashboard
- **Plotly** for interactive charts
- Risk score distributions
- Correlation analysis (risk vs complaints, risk vs centrality)
- Top critical stops and routes
- Complaint category analysis

### Network Graph
- **NetworkX** for graph operations
- **Plotly** for interactive graph visualization
- Multiple layout algorithms
- Color coding by various metrics
- Network statistics (density, degree centrality)

### Data Management
- File upload functionality
- ETL pipeline triggers
- System status monitoring
- Database connection testing

## Caching

The application uses Streamlit's caching to optimize performance:

- **Data caching**: Query results cached for 5 minutes (TTL=300)
- **Resource caching**: Database connections cached and reused
- Automatic cache invalidation on data updates

To clear cache:
- Press 'C' in the app, or
- Use the hamburger menu → "Clear cache"

## Performance Tips

1. **Network Graph**: Limit edges to 200-300 for better performance
2. **Map**: Use filters to reduce the number of markers displayed
3. **Data Management**: Run ETL steps during off-peak hours
4. **Caching**: Refresh data every 5 minutes by reloading the page

## Troubleshooting

### Database Connection Errors

Check if databases are running:
```bash
# MongoDB
ps aux | grep mongod

# Neo4j
ps aux | grep neo4j
```

Verify connection settings in `.env`

### No Data Displayed

1. Run the ETL pipeline first: `./run_all.sh`
2. Check System Status page for data counts
3. Verify data files exist in `data/` directory

### Slow Performance

1. Reduce the number of edges in Network Graph
2. Use filters to limit data displayed on maps
3. Check database query performance
4. Ensure adequate system resources

### Import Errors

Ensure PYTHONPATH is set:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

Or use the provided launch script:
```bash
./run_webapp.sh
```

## Development

### Adding New Pages

1. Create a new file in `webapp/pages/` with format: `NN_emoji_Page_Name.py`
2. Use the same imports and setup as existing pages
3. Access database utilities from `webapp.utils`

### Adding New Visualizations

1. Add data fetcher function in `webapp/utils/data_fetchers.py`
2. Use `@st.cache_data(ttl=300)` decorator for caching
3. Return pandas DataFrame for easy plotting
4. Use Plotly for interactive charts

### Modifying Database Queries

Edit `webapp/utils/data_fetchers.py` to add or modify Neo4j Cypher queries or MongoDB aggregation pipelines.

## Security Notes

- The web app connects directly to MongoDB and Neo4j
- Ensure databases are not exposed to untrusted networks
- Use authentication for production deployments
- Consider using a reverse proxy (nginx) for SSL/TLS

## Production Deployment

For production use:

1. Use a production WSGI server
2. Enable authentication
3. Configure SSL/TLS
4. Set up monitoring and logging
5. Use environment-specific `.env` files
6. Consider containerization with Docker

## Technology Stack

- **Streamlit**: Web framework
- **Plotly**: Interactive visualizations
- **Folium**: Interactive maps
- **NetworkX**: Graph algorithms
- **Pandas**: Data manipulation
- **PyMongo**: MongoDB driver
- **Neo4j Python Driver**: Neo4j connectivity
