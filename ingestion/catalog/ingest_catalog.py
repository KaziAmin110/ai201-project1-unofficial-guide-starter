import os
import json
import re
import sys

# Setup paths relative to script location
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def slugify(text):
    s = text.lower()
    s = re.sub(r'[^a-z0-9]', '_', s)
    s = re.sub(r'_+', '_', s)
    return s.strip('_')

def parse_frontmatter(content_str):
    frontmatter_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
    match = frontmatter_pattern.match(content_str)
    if not match:
        return {}, content_str
    
    frontmatter_text = match.group(1)
    body_text = content_str[match.end():]
    
    metadata = {}
    for line in frontmatter_text.splitlines():
        if ':' in line:
            key, val = line.split(':', 1)
            metadata[key.strip()] = val.strip()
            
    return metadata, body_text

def parse_markdown_sections(body_text, doc_title):
    lines = body_text.splitlines()
    sections = []
    
    current_h2 = ""
    current_h3 = ""
    current_heading = "Overview"
    current_level = 0
    current_lines = []
    
    def flush_section():
        text = "\n".join(current_lines).strip()
        if text:
            if current_level == 0:
                breadcrumbs = ["Undergraduate Catalog", doc_title, "Overview"]
            elif current_level == 2:
                breadcrumbs = ["Undergraduate Catalog", doc_title, current_h2]
            else: # level 3
                if current_h2:
                    breadcrumbs = ["Undergraduate Catalog", doc_title, current_h2, current_h3]
                else:
                    breadcrumbs = ["Undergraduate Catalog", doc_title, current_h3]
            
            sections.append({
                "heading": current_heading,
                "level": current_level,
                "breadcrumbs": breadcrumbs,
                "text": text
            })
            
    for line in lines:
        m2 = re.match(r'^##\s+(.+)$', line)
        m3 = re.match(r'^###\s+(.+)$', line)
        if m2:
            flush_section()
            current_h2 = m2.group(1).strip()
            current_h3 = ""
            current_heading = current_h2
            current_level = 2
            current_lines = []
        elif m3:
            flush_section()
            current_h3 = m3.group(1).strip()
            current_heading = current_h3
            current_level = 3
            current_lines = []
        else:
            current_lines.append(line)
            
    flush_section()
    return sections

def create_parent_chunks(blocks, max_parent_chars=2000):
    parents = []
    current_parent_blocks = []
    current_len = 0
    
    for block in blocks:
        block_len = len(block)
        if current_parent_blocks and current_len + block_len + 2 > max_parent_chars:
            parents.append(current_parent_blocks)
            current_parent_blocks = [block]
            current_len = block_len
        else:
            current_parent_blocks.append(block)
            current_len += block_len + (2 if len(current_parent_blocks) > 1 else 0)
            
    if current_parent_blocks:
        parents.append(current_parent_blocks)
        
    return parents

def get_child_chunks_with_tables(parent_text, table_ranges, target_size=450, overlap=80):
    chunks = []
    start = 0
    while start < len(parent_text):
        end = start + target_size
        if end >= len(parent_text):
            end = len(parent_text)
            chunks.append(parent_text[start:end].strip())
            break
            
        inside_table = False
        for t_start, t_end in table_ranges:
            if t_start < end < t_end:
                inside_table = True
                if t_start == start:
                    end = t_end
                else:
                    end = t_start
                break
                
        if not inside_table:
            last_space = parent_text.rfind(' ', start, end)
            if last_space > start + (target_size // 2):
                end = last_space
                
        chunk = parent_text[start:end].strip()
        if chunk:
            chunks.append(chunk)
            
        next_start = end - overlap
        for t_start, t_end in table_ranges:
            if t_start < next_start < t_end:
                next_start = t_start
                break
                
        start = max(start + 1, next_start)
        
    return chunks

def main():
    print("Starting Undergraduate Catalog Ingestion and Hierarchical Chunking...")
    
    raw_catalog_dir = os.path.join(project_root, "documents", "raw", "catalog")
    output_chunks_filepath = os.path.join(project_root, "documents", "chunks", "catalog_chunks.json")
    output_parents_filepath = os.path.join(project_root, "documents", "chunks", "catalog_parents.json")
    
    if not os.path.exists(raw_catalog_dir):
        print(f"Error: Catalog directory {raw_catalog_dir} not found.")
        sys.exit(1)
        
    files = [f for f in os.listdir(raw_catalog_dir) if f.endswith(".md")]
    files.sort()
    
    print(f"Found {len(files)} catalog markdown files for processing.")
    
    all_child_chunks = []
    parents_map = {}
    
    for filename in files:
        filepath = os.path.join(raw_catalog_dir, filename)
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
            
        metadata, body_text = parse_frontmatter(content)
        title = metadata.get("title", filename.replace(".md", "").replace("_", " ").title())
        url = metadata.get("url", "")
        
        file_slug = slugify(title)
        
        sections = parse_markdown_sections(body_text, title)
        print(f"Processed {filename} -> {len(sections)} logical sections.")
        
        for sec_idx, section in enumerate(sections):
            heading = section["heading"]
            breadcrumbs = section["breadcrumbs"]
            sec_text = section["text"]
            
            heading_slug = slugify(heading)
            
            # Split into paragraphs and tables
            blocks = [b.strip() for b in sec_text.split("\n\n") if b.strip()]
            if not blocks:
                continue
                
            # Group blocks into parent chunks
            parent_blocks_list = create_parent_chunks(blocks, max_parent_chars=2000)
            
            for parent_idx, parent_blocks in enumerate(parent_blocks_list):
                parent_id = f"parent_catalog_{file_slug}_{heading_slug}_{sec_idx}_{parent_idx}"
                parent_text = "\n\n".join(parent_blocks)
                
                # Save parent text in mapping
                parents_map[parent_id] = {
                    "id": parent_id,
                    "text": parent_text,
                    "metadata": {
                        "url": url,
                        "breadcrumbs": breadcrumbs,
                        "heading": heading,
                        "source_file": filename
                    }
                }
                
                # Calculate table ranges in parent_text
                table_ranges = []
                current_idx = 0
                for block in parent_blocks:
                    block_len = len(block)
                    is_tbl = block.startswith('|') and '| ---' in block
                    if is_tbl:
                        table_ranges.append((current_idx, current_idx + block_len))
                    current_idx += block_len + 2
                    
                # Generate child chunks
                child_texts = get_child_chunks_with_tables(
                    parent_text, table_ranges, target_size=450, overlap=80
                )
                
                # Build child objects
                for child_idx, child_text in enumerate(child_texts):
                    child_id = f"catalog_{file_slug}_{heading_slug}_{sec_idx}_{parent_idx}_child_{child_idx}"
                    
                    # Prefix the text with the breadcrumb path
                    prefix = "[" + " > ".join(breadcrumbs) + "] "
                    prefixed_text = prefix + child_text
                    
                    child_obj = {
                        "id": child_id,
                        "text": prefixed_text,
                        "source": f"Undergraduate Catalog - {title}",
                        "source_type": "catalog",
                        "metadata": {
                            "review_type": "catalog",
                            "url": url,
                            "breadcrumbs": breadcrumbs,
                            "parent_id": parent_id,
                            "heading": heading,
                            "source_file": filename
                        }
                    }
                    all_child_chunks.append(child_obj)
                    
    # Write output files
    os.makedirs(os.path.dirname(output_chunks_filepath), exist_ok=True)
    
    with open(output_chunks_filepath, "w", encoding="utf-8") as f:
        json.dump(all_child_chunks, f, indent=2, ensure_ascii=False)
        
    with open(output_parents_filepath, "w", encoding="utf-8") as f:
        json.dump(parents_map, f, indent=2, ensure_ascii=False)
        
    print(f"\nProcessing complete!")
    print(f"Generated {len(all_child_chunks)} child chunks in {output_chunks_filepath}")
    print(f"Generated {len(parents_map)} parent mapping entries in {output_parents_filepath}")

if __name__ == "__main__":
    main()
