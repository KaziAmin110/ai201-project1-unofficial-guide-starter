import sys
import logging
from retriever import Retriever

# Configure logging
logging.basicConfig(level=logging.WARNING, format="%(asctime)s [%(levelname)s] %(message)s")

# Define evaluation questions from planning.md
EVAL_QUESTIONS = [
    "What are some things which a new student can expect to be provided with at UCF Orientations ?",
    "Where can new students make reservations for visiting campus ?",
    "How are the dining halls at UCF ?",
    "How is the internet generally at UCF ?",
    "How good is the professor Travis Meade for COP3502C ?"
]

def format_hit(index, hit):
    metadata = hit.get("metadata", {})
    text = hit.get("text", "")
    distance = hit.get("distance", 0.0)
    chunk_id = hit.get("id", "unknown")
    source = metadata.get("source", metadata.get("source_file", "unknown"))
    source_type = metadata.get("source_type", metadata.get("review_type", "unknown"))
    
    output = []
    output.append(f"  [{index}] ID: {chunk_id} (Cosine Distance: {distance:.4f})")
    output.append(f"      Source: {source} | Type: {source_type}")
    
    # Surface source-specific metadata properties
    meta_props = []
    for k in ["professor_name", "course_code", "instructor", "post_title", "breadcrumbs"]:
        if k in metadata:
            meta_props.append(f"{k}: {metadata[k]}")
    if meta_props:
        output.append(f"      Metadata -> {', '.join(meta_props)}")
        
    # Preview text content (showing complete text for parent policy replacement comparison)
    text_lines = text.strip().split("\n")
    cleaned_lines = [line.strip() for line in text_lines if line.strip()]
    preview_text = " ".join(cleaned_lines)
    
    if len(preview_text) > 400:
        preview_text = preview_text[:397] + "..."
        
    output.append(f"      Text: \"{preview_text}\"")
    return "\n".join(output)

def run_evaluation(retriever):
    print("=" * 80)
    print("Running Automated Retrieval Evaluation Suite (5 Questions from planning.md)")
    print("=" * 80)
    
    for i, q in enumerate(EVAL_QUESTIONS):
        print(f"\nQuestion {i+1}: {q}")
        print("-" * 80)
        hits = retriever.retrieve(q, top_k=5)
        
        if not hits:
            print("  No hits retrieved.")
            continue
            
        for idx, hit in enumerate(hits):
            print(format_hit(idx + 1, hit))
            
    print("\n" + "=" * 80)
    print("Evaluation Complete!")
    print("=" * 80)

def run_single_query(retriever, query):
    print(f"\nQuery: {query}")
    print("-" * 80)
    hits = retriever.retrieve(query, top_k=5)
    
    if not hits:
        print("  No hits retrieved.")
        return
        
    for idx, hit in enumerate(hits):
        print(format_hit(idx + 1, hit))

def main():
    try:
        retriever = Retriever()
    except Exception as e:
        print(f"Error initializing retriever: {e}")
        print("Make sure you run the database build script first to generate the ChromaDB collection.")
        sys.exit(1)
        
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        run_single_query(retriever, query)
    else:
        run_evaluation(retriever)

if __name__ == "__main__":
    main()
