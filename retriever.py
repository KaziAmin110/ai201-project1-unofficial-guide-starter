import os
import json
import logging
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class Retriever:
    def __init__(self, db_path: str = None, parents_path: str = None):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = script_dir
        
        # Resolve default paths
        if db_path is None:
            db_path = os.path.join(project_root, "documents", "chromadb")
        if parents_path is None:
            parents_path = os.path.join(project_root, "documents", "chunks", "catalog_parents.json")
            
        logger.info(f"Connecting to ChromaDB client at: {db_path}")
        self.client = chromadb.PersistentClient(path=db_path)
        
        logger.info("Initializing SentenceTransformerEmbeddingFunction for all-MiniLM-L6-v2")
        self.emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        
        self.collection_name = "ucf_unofficial_guide"
        logger.info(f"Loading collection: {self.collection_name}")
        self.collection = self.client.get_collection(
            name=self.collection_name,
            embedding_function=self.emb_fn
        )
        
        # Load parent policies from json file
        self.parents = {}
        if os.path.exists(parents_path):
            logger.info(f"Loading catalog parents from: {parents_path}")
            with open(parents_path, "r", encoding="utf-8") as f:
                self.parents = json.load(f)
            logger.info(f"Loaded {len(self.parents)} catalog parent policies")
        else:
            logger.warning(f"Catalog parents file not found at: {parents_path}. Parent-child resolution will not function.")

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Query ChromaDB for top_k results and return resolved list of dicts.
        Catalog chunks matching a parent_id are resolved to their full parent policies.
        Duplicate parent policies or identical chunks are de-duplicated to preserve context window.
        """
        # Execute query against ChromaDB
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k
        )
        
        # Extract components (safely checking if results are returned)
        if not results or not results["ids"] or not results["ids"][0]:
            return []
            
        ids = results["ids"][0]
        documents = results["documents"][0]
        metadatas = results["metadatas"][0]
        distances = results["distances"][0]
        
        retrieved_items = []
        seen_parents = set()
        seen_texts = set()
        
        for i in range(len(ids)):
            chunk_id = ids[i]
            text = documents[i]
            metadata = metadatas[i]
            distance = distances[i]
            
            # Check if this is a catalog chunk that needs parent policy resolution
            review_type = metadata.get("review_type")
            parent_id = metadata.get("parent_id")
            
            is_catalog = (review_type == "catalog") or (parent_id is not None)
            
            if is_catalog and parent_id:
                # Resolve to parent text if available in parent mapping
                if parent_id in self.parents:
                    # De-duplicate parent policies to avoid returning duplicate large blocks
                    if parent_id in seen_parents:
                        logger.debug(f"Skipping duplicate catalog parent block: {parent_id}")
                        continue
                    seen_parents.add(parent_id)
                    
                    parent_data = self.parents[parent_id]
                    # Replace text with parent policy text
                    text = parent_data.get("text", text)
                else:
                    logger.warning(f"Parent ID '{parent_id}' not found in parent catalog map. Using child text.")
            
            # General text-based de-duplication to prevent duplicate chunks of other types
            text_hash = text.strip()
            if text_hash in seen_texts:
                continue
            seen_texts.add(text_hash)
            
            retrieved_items.append({
                "id": chunk_id,
                "text": text,
                "metadata": metadata,
                "distance": distance
            })
            
        return retrieved_items

if __name__ == "__main__":
    # Setup simple logging for testing
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    retriever = Retriever()
    query = "What are the rules for computer science foundation exam?"
    logger.info(f"Running retrieval test with query: '{query}'")
    hits = retriever.retrieve(query, top_k=3)
    for index, hit in enumerate(hits):
        print(f"\n[Hit {index+1}] ID: {hit['id']} | Distance: {hit['distance']:.4f}")
        print(f"Source: {hit['metadata'].get('source')} | Type: {hit['metadata'].get('source_type')}")
        print(f"Text Preview: {hit['text'][:200]}...")
