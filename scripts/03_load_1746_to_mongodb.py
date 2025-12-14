#!/usr/bin/env python3
import pandas as pd
from pymongo import MongoClient
from datetime import datetime
from tqdm import tqdm
import config
import sys

class Reclamacoes1746Loader:
    def __init__(self):
        self.client = MongoClient(config.MONGO_URI)
        self.db = self.client[config.MONGO_DB]
        self.collection = self.db.reclamacoes_1746_raw

    def detect_csv_format(self, df):
        if 'protocolo' in df.columns:
            return 'reclamacoes'
        elif 'id_chamado' in df.columns:
            return 'chamados_v2'
        else:
            raise ValueError(f"Unknown CSV format. Columns: {df.columns.tolist()}")

    def map_chamados_v2(self, df):
        print("Mapping chamados_v2 columns...")

        mapped_df = df.copy()

        rename_dict = {}
        for old_col, new_col in config.CHAMADOS_V2_COLUMN_MAPPING.items():
            if old_col in mapped_df.columns:
                rename_dict[old_col] = new_col

        mapped_df = mapped_df.rename(columns=rename_dict)

        for col, default_value in config.CHAMADOS_V2_DEFAULTS.items():
            if col not in mapped_df.columns:
                mapped_df[col] = default_value

        required = ['protocolo', 'data_abertura', 'servico', 'latitude', 'longitude']
        missing = [col for col in required if col not in mapped_df.columns]

        if missing:
            raise ValueError(f"Missing required columns after mapping: {missing}")

        null_coords = mapped_df[['latitude', 'longitude']].isnull().any(axis=1).sum()
        if null_coords > 0:
            print(f"Ignoring {null_coords} records with null coordinates")
            mapped_df = mapped_df.dropna(subset=['latitude', 'longitude'])

        print(f"Mapping complete: {len(mapped_df)} valid records")
        return mapped_df

    def normalize_categoria(self, servico):
        for categoria in config.CATEGORIA_PESOS.keys():
            if categoria.lower() in servico.lower():
                return categoria
        return 'Outros'

    def get_peso_categoria(self, categoria):
        return config.CATEGORIA_PESOS.get(categoria, 0.3)

    def normalize_criticidade(self, criticidade):
        if pd.isna(criticidade):
            return 'Baixa'

        crit = str(criticidade).strip().title()
        if crit in ['Alta', 'Média', 'Media', 'Baixa']:
            return crit
        return 'Baixa'

    def load_from_csv(self):
        print("Loading 1746 complaints from CSV...")

        df = pd.read_csv(config.RECLAMACOES_1746_FILE)
        print(f"Found {len(df)} complaints in file")

        csv_format = self.detect_csv_format(df)
        print(f"Detected format: {csv_format}")

        if csv_format == 'chamados_v2':
            df = self.map_chamados_v2(df)
        else:
            required_columns = ['protocolo', 'data_abertura', 'servico', 'latitude', 'longitude']
            missing = [col for col in required_columns if col not in df.columns]

            if missing:
                print(f"Missing columns: {missing}")
                print(f"Available columns: {df.columns.tolist()}")
                return False

        print("\nProcessing and inserting to MongoDB...")

        inserted_count = 0
        duplicates_count = 0
        errors_count = 0

        for _, row in tqdm(df.iterrows(), total=len(df), desc="Inserting"):
            try:
                if pd.notna(row['data_abertura']):
                    data_abertura = pd.to_datetime(row['data_abertura'])
                else:
                    data_abertura = datetime.now()

                categoria = self.normalize_categoria(row['servico'])
                peso = self.get_peso_categoria(categoria)
                criticidade = self.normalize_criticidade(
                    row.get('criticidade', 'Baixa')
                )

                doc = {
                    'protocolo': str(row['protocolo']),
                    'data_abertura': data_abertura,
                    'servico': categoria,
                    'descricao': str(row.get('descricao', '')),
                    'status': str(row.get('status', 'Aberto')),
                    'lat': float(row['latitude']),
                    'lon': float(row['longitude']),
                    'peso': peso,
                    'criticidade': criticidade,
                    'bairro': str(row.get('bairro', '')),
                    'synced_to_neo4j': False,
                    'imported_at': datetime.now()
                }

                doc['localizacao'] = {
                    'type': 'Point',
                    'coordinates': [float(row['longitude']), float(row['latitude'])]
                }

                try:
                    self.collection.insert_one(doc)
                    inserted_count += 1
                except Exception as e:
                    if 'duplicate key' in str(e):
                        duplicates_count += 1
                    else:
                        errors_count += 1

            except Exception as e:
                errors_count += 1
                continue

        print(f"\nInserted: {inserted_count}")
        print(f"Duplicates: {duplicates_count}")
        print(f"Errors: {errors_count}")

        return True

    def create_summary(self):
        print("\nData summary:")

        total = self.collection.count_documents({})
        print(f"Total complaints: {total}")

        pipeline = [
            {'$group': {
                '_id': '$servico',
                'count': {'$sum': 1}
            }},
            {'$sort': {'count': -1}}
        ]

        print("\nBy category:")
        for doc in self.collection.aggregate(pipeline):
            print(f"  {doc['_id']}: {doc['count']}")

        pipeline = [
            {'$group': {
                '_id': '$status',
                'count': {'$sum': 1}
            }}
        ]

        print("\nBy status:")
        for doc in self.collection.aggregate(pipeline):
            print(f"  {doc['_id']}: {doc['count']}")

    def close(self):
        self.client.close()

    def run(self):
        print("Loading 1746 complaints to MongoDB...\n")

        try:
            success = self.load_from_csv()
            if success:
                self.create_summary()
                print("\n1746 load complete")
                return True
            return False

        except Exception as e:
            print(f"\n1746 load error: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            self.close()


if __name__ == "__main__":
    loader = Reclamacoes1746Loader()
    success = loader.run()
    sys.exit(0 if success else 1)
