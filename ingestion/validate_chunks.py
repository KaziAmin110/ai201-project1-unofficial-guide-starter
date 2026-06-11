import os
import json
import sys
import re
import random

def validate_chunks(filepath: str) -> bool:
    if not os.path.exists(filepath):
        print(f"Error: Output chunk manifest {filepath} does not exist!")
        return False
        
    with open(filepath, "r", encoding="utf-8") as f:
        chunks = json.load(f)
        
    print(f"Loaded {len(chunks)} chunks from {filepath} for validation.")
    
    errors = 0
    warnings = 0
    
    required_keys = {"id", "text", "source", "source_type", "metadata"}
    
    for idx, chunk in enumerate(chunks):
        chunk_id = chunk.get('id', f'chunk_index_{idx}')
        
        # 1. Check top-level keys
        missing_keys = required_keys - set(chunk.keys())
        if missing_keys:
            print(f"ERROR [Chunk {chunk_id}]: Missing top-level keys: {missing_keys}")
            errors += 1
            continue
            
        # 2. Check value types
        if not isinstance(chunk["id"], str):
            print(f"ERROR [Chunk {chunk_id}]: 'id' must be a string, got {type(chunk['id'])}")
            errors += 1
        if not isinstance(chunk["text"], str):
            print(f"ERROR [Chunk {chunk_id}]: 'text' must be a string, got {type(chunk['text'])}")
            errors += 1
        if not isinstance(chunk["source"], str):
            print(f"ERROR [Chunk {chunk_id}]: 'source' must be a string, got {type(chunk['source'])}")
            errors += 1
        if not isinstance(chunk["source_type"], str):
            print(f"ERROR [Chunk {chunk_id}]: 'source_type' must be a string, got {type(chunk['source_type'])}")
            errors += 1
        if not isinstance(chunk["metadata"], dict):
            print(f"ERROR [Chunk {chunk_id}]: 'metadata' must be a dictionary, got {type(chunk['metadata'])}")
            errors += 1
            continue
            
        # 3. Check metadata keys
        metadata = chunk["metadata"]
        review_type = metadata.get("review_type")
        if review_type not in ("school", "professor", "reddit_thread", "syllabus", "catalog"):
            print(f"ERROR [Chunk {chunk_id}]: 'review_type' must be 'school', 'professor', 'reddit_thread', 'syllabus' or 'catalog', got {review_type}")
            errors += 1
            
        if "source_file" not in metadata:
            print(f"ERROR [Chunk {chunk_id}]: 'source_file' missing in metadata")
            errors += 1
            
        if review_type == "professor":
            if "date" not in metadata:
                print(f"ERROR [Chunk {chunk_id}]: 'date' missing in metadata")
                errors += 1
            prof_req_keys = {"professor_name", "department", "course_code", "original_course_code", "quality_rating", "difficulty_rating"}
            missing_prof_keys = prof_req_keys - set(metadata.keys())
            if missing_prof_keys:
                print(f"ERROR [Chunk {chunk_id}]: Professor metadata missing keys: {missing_prof_keys}")
                errors += 1
                
        elif review_type == "school":
            if "date" not in metadata:
                print(f"ERROR [Chunk {chunk_id}]: 'date' missing in metadata")
                errors += 1
                
        elif review_type == "reddit_thread":
            reddit_req_keys = {"post_id", "post_title", "post_url", "comment_id", "comment_author", "comment_score", "post_date"}
            missing_reddit_keys = reddit_req_keys - set(metadata.keys())
            if missing_reddit_keys:
                print(f"ERROR [Chunk {chunk_id}]: Reddit metadata missing keys: {missing_reddit_keys}")
                errors += 1
                
        elif review_type == "syllabus":
            syllabus_req_keys = {"course_code", "original_course_code", "instructor", "term", "section_name"}
            missing_syllabus_keys = syllabus_req_keys - set(metadata.keys())
            if missing_syllabus_keys:
                print(f"ERROR [Chunk {chunk_id}]: Syllabus metadata missing keys: {missing_syllabus_keys}")
                errors += 1
                
        elif review_type == "catalog":
            catalog_req_keys = {"url", "breadcrumbs", "parent_id", "heading"}
            missing_catalog_keys = catalog_req_keys - set(metadata.keys())
            if missing_catalog_keys:
                print(f"ERROR [Chunk {chunk_id}]: Catalog metadata missing keys: {missing_catalog_keys}")
                errors += 1
            else:
                if not isinstance(metadata["url"], str):
                    print(f"ERROR [Chunk {chunk_id}]: Metadata 'url' must be a string, got {type(metadata['url'])}")
                    errors += 1
                if not isinstance(metadata["breadcrumbs"], list):
                    print(f"ERROR [Chunk {chunk_id}]: Metadata 'breadcrumbs' must be a list, got {type(metadata['breadcrumbs'])}")
                    errors += 1
                if not isinstance(metadata["parent_id"], str):
                    print(f"ERROR [Chunk {chunk_id}]: Metadata 'parent_id' must be a string, got {type(metadata['parent_id'])}")
                    errors += 1
                if not isinstance(metadata["heading"], str):
                    print(f"ERROR [Chunk {chunk_id}]: Metadata 'heading' must be a string, got {type(metadata['heading'])}")
                    errors += 1
                
        # 4. Check text length and quality
        text = chunk["text"]
        
        if not text.strip():
            print(f"ERROR [Chunk {chunk_id}]: Chunk text is empty or only whitespace!")
            errors += 1
            continue
            
        # Check for HTML tag artifacts (e.g. <div, <p, </p>, <a, <span, etc.)
        html_patterns = [r'<[a-zA-Z]+/?>', r'</[a-zA-Z]+>', r'<[a-zA-Z]+\s+[^>]*>']
        has_html = False
        for p in html_patterns:
            if re.search(p, text):
                has_html = True
                break
        if has_html:
            print(f"ERROR [Chunk {chunk_id}]: Found potential HTML tag artifacts in text: '{text}'")
            errors += 1
            
        # Check that the source file name matches the source field or metadata
        source_file = metadata.get("source_file", "")
        if source_file:
            cleaned_filename = re.sub(r'[^a-zA-Z0-9]', ' ', os.path.splitext(source_file)[0]).lower()
            source_lower = chunk["source"].lower()
            filename_words = [w for w in cleaned_filename.split() if len(w) > 3]
            generic_terms = {'school', 'professors', 'reddit', 'syllabus', 'catalog'}
            filename_words = [w for w in filename_words if w not in generic_terms]
            if filename_words and not any(w in source_lower for w in filename_words):
                print(f"WARNING [Chunk {chunk_id}]: Metadata source_file '{source_file}' might not match source description '{chunk['source']}'")
                warnings += 1

        char_count = len(text)
        
        if char_count < 40:
            print(f"WARNING [Chunk {chunk_id}]: Chunk text is suspiciously short ({char_count} chars): '{text}'")
            warnings += 1
        elif char_count > 3000:
            print(f"WARNING [Chunk {chunk_id}]: Chunk text is very long ({char_count} chars)")
            warnings += 1
            
        # 5. Check prefix formatting matches expectation
        if review_type == "school" and not text.startswith("University: "):
            print(f"WARNING [Chunk {chunk_id}]: School chunk text should start with 'University: ' prefix")
            warnings += 1
        elif review_type == "professor" and not text.startswith("Professor: "):
            print(f"WARNING [Chunk {chunk_id}]: Professor chunk text should start with 'Professor: ' prefix")
            warnings += 1
        elif review_type == "reddit_thread" and not text.startswith("Subreddit: "):
            print(f"WARNING [Chunk {chunk_id}]: Reddit chunk text should start with 'Subreddit: ' prefix")
            warnings += 1
        elif review_type == "syllabus" and not text.startswith("Course: "):
            print(f"WARNING [Chunk {chunk_id}]: Syllabus chunk text should start with 'Course: ' prefix")
            warnings += 1
        elif review_type == "catalog" and not text.startswith("[Undergraduate Catalog"):
            print(f"WARNING [Chunk {chunk_id}]: Catalog chunk text should start with '[Undergraduate Catalog' prefix")
            warnings += 1

            
    # Check for mechanical splitting (all chunks having the exact same length)
    if len(chunks) > 5:
        lengths = [len(c["text"]) for c in chunks]
        unique_lengths = set(lengths)
        if len(unique_lengths) == 1:
            print(f"WARNING: All chunks in {filepath} have the exact same length ({list(unique_lengths)[0]} chars). This might indicate mechanical splitting without respecting content boundaries.")
            warnings += 1
            
    # Print 5 random chunks for manual readability and substance check
    if chunks:
        print("\n--- 5 Random Chunks for Manual Inspection ---")
        sample_size = min(len(chunks), 5)
        random_samples = random.sample(chunks, sample_size)
        for i, sample in enumerate(random_samples):
            print(f"\n[Sample Chunk {i+1}] ID: {sample.get('id')}")
            print(f"Source: {sample.get('source')} | Type: {sample.get('source_type')}")
            print(f"Text Preview:\n---\n{sample.get('text')}\n---")
            
    # Write debug file containing a summary of parsed chunks
    debug_filepath = os.path.join(os.path.dirname(filepath), "debug_chunks.json")
    with open(debug_filepath, "w", encoding="utf-8") as f:
        json.dump(chunks[:5], f, indent=2, ensure_ascii=False)
    print(f"Wrote top {min(len(chunks), 5)} chunks to debug file: {debug_filepath}")
        
    print("\n--- Validation Summary ---")
    print(f"Errors found: {errors}")
    print(f"Warnings found: {warnings}")
    
    return errors == 0

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    if len(sys.argv) > 1:
        chunks_filepath = sys.argv[1]
    else:
        chunks_filepath = os.path.join(project_root, "documents", "chunks", "rmp_chunks.json")
        
    success = validate_chunks(chunks_filepath)
    if success:
        print("Validation PASSED successfully.")
    else:
        print("Validation FAILED due to errors. Please correct the ingestion parser.")
        sys.exit(1)

if __name__ == "__main__":
    main()
