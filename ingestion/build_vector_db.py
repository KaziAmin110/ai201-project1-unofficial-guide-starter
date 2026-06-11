import os
import json
import logging
import chromadb
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)

def build_db():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    documents_dir = os.path.join(project_root, "documents")
    chunks_dir = os.path.join(documents_dir, "chunks")
    db_path = os.path.join(documents_dir, "chromadb")
    
    logger.info(f"Initializing ChromaDB PersistentClient at: {db_path}")
    client = chromadb.PersistentClient(path=db_path)
    
    # 1. Load all chunk manifests
    chunk_files = {
        "rmp": "rmp_chunks.json",
        "reddit": "reddit_chunks.json",
        "syllabus": "syllabus_chunks.json",
        "catalog": "catalog_chunks.json"
    }
    
    all_chunks = []
    for source_key, filename in chunk_files.items():
        filepath = os.path.join(chunks_dir, filename)
        if not os.path.exists(filepath):
            logger.warning(f"Chunk manifest not found: {filepath}. Skipping.")
            continue
            
        logger.info(f"Loading chunks from: {filename}")
        with open(filepath, "r", encoding="utf-8") as f:
            chunks = json.load(f)
            logger.info(f"Loaded {len(chunks)} chunks from {filename}")
            all_chunks.extend(chunks)
            
    if not all_chunks:
        logger.error("No chunks loaded from any source file. Aborting.")
        raise ValueError("No chunks found to ingest.")
        
    logger.info(f"Total chunks loaded for ingestion: {len(all_chunks)}")
    
    # 2. Reset or recreate collection ucf_unofficial_guide
    collection_name = "ucf_unofficial_guide"
    
    # Check if collection exists and delete it to rebuild from scratch
    existing_collections = [col.name for col in client.list_collections()]
    if collection_name in existing_collections:
        logger.info(f"Collection '{collection_name}' already exists. Deleting it for a clean rebuild.")
        client.delete_collection(name=collection_name)
        
    emb_fn = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
    
    logger.info(f"Creating collection '{collection_name}' with cosine distance metric...")
    collection = client.create_collection(
        name=collection_name,
        embedding_function=emb_fn,
        metadata={"hnsw:space": "cosine"}
    )
    
    # 3. Clean chunks and prepare data arrays for ingestion
    ids = []
    documents = []
    metadatas = []
    
    for idx, chunk in enumerate(all_chunks):
        chunk_id = chunk.get("id") or f"chunk_gen_{idx}"
        text = chunk.get("text")
        source = chunk.get("source", "unknown")
        source_type = chunk.get("source_type", "unknown")
        metadata = chunk.get("metadata") or {}
        
        if not text or not text.strip():
            logger.warning(f"Skipping empty text chunk with ID: {chunk_id}")
            continue
            
        # Standardize metadata keys. We must make sure all top-level keys match Chroma compatibility
        # Add source and source_type to metadata too so they are searchable/filterable
        clean_metadata = {
            "source": source,
            "source_type": source_type,
            **metadata
        }
        
        # Ensure any dict/list items other than simple types or flat lists are cast to strings.
        # Flat lists of strings are supported natively by Chroma v1.5.9.
        # But we'll cast any dict values or other complex structures (if any) to string.
        final_metadata = {}
        for k, v in clean_metadata.items():
            if isinstance(v, dict):
                final_metadata[k] = json.dumps(v, ensure_ascii=False)
            elif isinstance(v, list):
                # Ensure elements are strings/primitives
                final_metadata[k] = [str(item) if not isinstance(item, (int, float, bool, str)) else item for item in v]
            elif v is None:
                final_metadata[k] = ""
            else:
                final_metadata[k] = v
                
        ids.append(chunk_id)
        documents.append(text)
        metadatas.append(final_metadata)
        
    # 4. Batch addition to vector DB
    batch_size = 200
    total_chunks = len(ids)
    logger.info(f"Starting database insertion of {total_chunks} chunks in batches of {batch_size}...")
    
    for i in range(0, total_chunks, batch_size):
        batch_ids = ids[i : i + batch_size]
        batch_docs = documents[i : i + batch_size]
        batch_metas = metadatas[i : i + batch_size]
        
        logger.info(f"Inserting batch {i // batch_size + 1}/{(total_chunks + batch_size - 1) // batch_size} (indices {i} to {min(i + batch_size, total_chunks)})...")
        collection.add(
            ids=batch_ids,
            documents=batch_docs,
            metadatas=batch_metas
        )
        
    logger.info("Successfully ingested all chunks into ChromaDB!")

def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    build_db()

if __name__ == "__main__":
    main()
