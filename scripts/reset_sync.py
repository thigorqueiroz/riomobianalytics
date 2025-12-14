#!/usr/bin/env python3
"""
Reset sync flags in MongoDB to allow re-syncing to Neo4j
"""
from pymongo import MongoClient
import config

def reset_sync_flags():
    print("🔄 Resetting sync flags in MongoDB...")

    client = MongoClient(config.MONGO_URI)
    db = client[config.MONGO_DB]
    collection = db.reclamacoes_1746_raw

    result = collection.update_many(
        {'synced_to_neo4j': True},
        {'$set': {'synced_to_neo4j': False}}
    )

    print(f"  ✅ Reset {result.modified_count:,} records")

    client.close()

if __name__ == "__main__":
    reset_sync_flags()
