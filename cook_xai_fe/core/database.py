import os
from pymongo import MongoClient
from core.logger import logger
from core.config import settings

# MongoDB Connection
client = None
db = None
collection = None

# Fallback in-memory store if MongoDB isn't configured yet
_memory_store = {}

def init_db():
    global client, db, collection
    if not settings.MONGO_URI:
        logger.warning("MONGO_URI not found in .env. Falling back to in-memory temporary token storage.")
        return

    try:
        client = MongoClient(settings.MONGO_URI, serverSelectionTimeoutMS=5000)
        # Test connection
        client.server_info()
        db = client.get_database("enterprise_xai")
        collection = db.get_collection("repo_tokens")
        
        # Ensure we have a unique index on repo_name
        collection.create_index("repo_name", unique=True)
        logger.info("✅ Connected to MongoDB Atlas for Multi-Tenant Token Storage.")
    except Exception as e:
        logger.error(f"❌ Failed to connect to MongoDB Atlas: {e}")
        client = None

def save_repo_token(repo_name: str, token: str):
    if client and collection is not None:
        try:
            collection.update_one(
                {"repo_name": repo_name},
                {"$set": {"token": token}},
                upsert=True
            )
        except Exception as e:
            logger.error(f"Failed to save token to MongoDB for {repo_name}: {e}")
    else:
        _memory_store[repo_name] = token

def get_repo_token(repo_name: str) -> str:
    if client and collection is not None:
        try:
            result = collection.find_one({"repo_name": repo_name})
            return result["token"] if result else None
        except Exception as e:
            logger.error(f"Failed to fetch token from MongoDB for {repo_name}: {e}")
            return None
    else:
        return _memory_store.get(repo_name)

def get_all_connected_repos() -> set:
    """Returns a set of all repo_names that have been connected."""
    if client and collection is not None:
        try:
            cursor = collection.find({}, {"repo_name": 1})
            return {doc["repo_name"] for doc in cursor if "repo_name" in doc}
        except Exception as e:
            logger.error(f"Failed to fetch all connected repos from MongoDB: {e}")
            return set()
    else:
        return set(_memory_store.keys())

def remove_repo_token(repo_name: str):
    if client and collection is not None:
        try:
            collection.delete_one({"repo_name": repo_name})
        except Exception as e:
            logger.error(f"Failed to remove token from MongoDB for {repo_name}: {e}")
    else:
        _memory_store.pop(repo_name, None)

# Initialize on import
init_db()
