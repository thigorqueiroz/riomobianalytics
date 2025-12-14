import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/')
MONGO_DB = os.getenv('MONGO_DB', 'riomobianalytics')

NEO4J_URI = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
NEO4J_USER = os.getenv('NEO4J_USER', 'neo4j')
NEO4J_PASSWORD = os.getenv('NEO4J_PASSWORD', 'password')

GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', '')

GTFS_DIR = os.getenv('GTFS_DIR', './data/gtfs/')
RECLAMACOES_1746_FILE = os.getenv('RECLAMACOES_FILE', './data/1746/chamados_v2.csv')

BATCH_SIZE = 1000
MAX_DISTANCE_AFFECTS_METERS = 100

CATEGORIA_PESOS = {
    'Segurança Pública': 1.5,
    'Iluminação Pública': 0.6,
    'Conservação de Vias': 0.5,
    'Limpeza Urbana': 0.4,
    'Trânsito e Transporte': 0.8,
    'Outros': 0.3
}

CRITICIDADE_MAP = {
    'Alta': 1.5,
    'Média': 1.0,
    'Media': 1.0,
    'Baixa': 0.5
}

CHAMADOS_V2_COLUMN_MAPPING = {
    'id_chamado': 'protocolo',
    'data_inicio': 'data_abertura',
    'categoria': 'servico',
    'latitude': 'latitude',
    'longitude': 'longitude',
}

CHAMADOS_V2_DEFAULTS = {
    'status': 'Aberto',
    'criticidade': 'Baixa',
    'descricao': '',
    'bairro': ''
}
