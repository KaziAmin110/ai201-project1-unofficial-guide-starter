import os
import json
import re
import sys

# Add the parent directory of this script's directory to sys.path to import modules
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(script_dir))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from ingestion.rmp.ingest_rmp import normalize_course

# Section matchers (compiled regex and the section label to use)
SECTION_HEADERS = [
    (re.compile(r'^\s*(?:course\s+)?description\b', re.I), "Course Description"),
    (re.compile(r'^\s*prerequisites?\b', re.I), "Prerequisites"),
    (re.compile(r'^\s*(?:course\s+)?objectives?\b', re.I), "Course Objectives"),
    (re.compile(r'^\s*(?:required\s+)?textbooks?\b|^\s*(?:required\s+)?materials?\b', re.I), "Required Materials"),
    (re.compile(r'^\s*(?:grading\s+)(?:scale|policy|criteria)\b|^\s*evaluation\b|^\s*grading\b', re.I), "Grading Policy"),
    (re.compile(r'^\s*(?:course\s+)?schedule\b|^\s*weekly\s+schedule\b|^\s*calendar\b|^\s*topics?\s+covered\b', re.I), "Course Schedule"),
    (re.compile(r'^\s*office\s+hours\b|^\s*contact\s+info(?:rmation)?\b|^\s*instructor\s+info(?:rmation)?\b', re.I), "Contact Information"),
    (re.compile(r'^\s*academic\s+integrity\b|^\s*honesty\s+policy\b|^\s*cheating\b', re.I), "Academic Integrity"),
    (re.compile(r'^\s*accommodations?\b|^\s*accessibility\s+statement\b|^\s*ada\s+statement\b', re.I), "Accommodations"),
    (re.compile(r'^\s*late\s+work\b|^\s*late\s+policy\b|^\s*makeup\s+policy\b|^\s*attendance\s+policy\b', re.I), "Course Policies"),
]

def find_matching_section(line):
    """
    Checks if a short line matches any known syllabus section header.
    """
    stripped = line.strip()
    if not stripped or len(stripped) > 50:
        return None
    
    for pattern, section_label in SECTION_HEADERS:
        if pattern.match(stripped):
            return section_label
    return None

def split_text_into_subchunks(text, max_chars=1800, overlap=150):
    """
    Splits long section text into smaller subchunks to stay under character limits,
    attempting to split on paragraph boundaries or newlines.
    """
    if len(text) <= max_chars:
        return [text]
        
    subchunks = []
    paragraphs = text.split("\n\n")
    current_chunk = []
    current_length = 0
    
    for p in paragraphs:
        p_len = len(p)
        if current_length + p_len + (2 if current_chunk else 0) <= max_chars:
            current_chunk.append(p)
            current_length += p_len + (2 if current_chunk else 0)
        else:
            # Flush current chunk
            if current_chunk:
                subchunks.append("\n\n".join(current_chunk))
            # Start new chunk
            current_chunk = [p]
            current_length = p_len
            
    if current_chunk:
        subchunks.append("\n\n".join(current_chunk))
        
    # If a single paragraph is larger than max_chars, split it by simple lines
    final_subchunks = []
    for chunk in subchunks:
        if len(chunk) > max_chars:
            lines = chunk.split("\n")
            temp_lines = []
            temp_len = 0
            for line in lines:
                l_len = len(line)
                if temp_len + l_len + (1 if temp_lines else 0) <= max_chars:
                    temp_lines.append(line)
                    temp_len += l_len + (1 if temp_lines else 0)
                else:
                    if temp_lines:
                        final_subchunks.append("\n".join(temp_lines))
                    temp_lines = [line]
                    temp_len = l_len
            if temp_lines:
                final_subchunks.append("\n".join(temp_lines))
        else:
            final_subchunks.append(chunk)
            
    return final_subchunks

def is_noise_line(line):
    """
    Identifies common Simple Syllabus header/footer noise lines.
    """
    stripped = line.strip()
    if not stripped:
        return False
    # Simple Syllabus URL footer (with optional page number like 1/26)
    if re.search(r'https?://[^\s]*simplesyllabus\.com[^\s]*(?:\s+\d+/\d+)?', stripped, re.I):
        return True
    # Simple Syllabus print header with timestamp and course info
    if re.search(r'^\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}\s*(?:AM|PM)?\s+.*?-\s*Simple Syllabus', stripped, re.I):
        return True
    # Page break placeholder
    if "--- PAGE BREAK ---" in stripped:
        return True
    return False

def process_syllabus_sections(raw_record):
    """
    Parses a single raw syllabus record into chunks by section.
    """
    source_file = raw_record.get("source_file", "")
    raw_course = raw_record.get("course_code", "UNKNOWN")
    instructor = raw_record.get("instructor", "UNKNOWN")
    term = raw_record.get("term", "UNKNOWN")
    raw_text = raw_record.get("raw_text", "")
    
    # Normalize course code (e.g. COP3502C)
    normalized_course = normalize_course(raw_course, "Computer Science")
    
    chunks = []
    lines = raw_text.split("\n")
    
    current_section = "Course Overview"
    current_lines = []
    
    # Keep track of indices per section_slug to prevent duplicate IDs
    section_index_map = {}
    
    def flush_current_section():
        if not current_lines:
            return
        
        section_text = "\n".join(current_lines).strip()
        section_text = re.sub(r'\n{3,}', '\n\n', section_text).strip()
        
        if not section_text or len(section_text) < 20:
            return
            
        subchunks = split_text_into_subchunks(section_text)
        
        for sub_idx, sub_text in enumerate(subchunks):
            # Format target chunk text
            chunk_prefix = f"Course: {normalized_course} | Instructor: {instructor} | Section: {current_section}"
            if len(subchunks) > 1:
                chunk_prefix += f" (Part {sub_idx + 1})"
            
            chunk_text = f"{chunk_prefix} | {sub_text}"
            
            # Slugify identifiers for ID
            course_slug = normalized_course.lower()
            section_slug = re.sub(r'[^a-zA-Z0-9]', '_', current_section.lower())
            
            # Get and increment index for this section to prevent duplicates
            idx = section_index_map.get(section_slug, 0)
            section_index_map[section_slug] = idx + 1
            
            chunk_id = f"syllabus_{course_slug}_{section_slug}_{idx}"
            
            chunk_obj = {
                "id": chunk_id,
                "text": chunk_text,
                "source": f"Syllabus - {normalized_course} ({term})",
                "source_type": "syllabus",
                "metadata": {
                    "review_type": "syllabus",
                    "course_code": normalized_course,
                    "original_course_code": raw_course,
                    "instructor": instructor,
                    "term": term,
                    "section_name": current_section,
                    "source_file": source_file
                }
            }
            chunks.append(chunk_obj)
 
    for line in lines:
        if is_noise_line(line):
            continue
        matched_section = find_matching_section(line)
        if matched_section:
            # Flush existing section
            flush_current_section()
            # Start new section
            current_section = matched_section
            current_lines = []
        else:
            current_lines.append(line)
            
    # Flush the final section
    flush_current_section()
    
    return chunks

def main():
    print("Starting Syllabus Ingestion and Chunker script...")
    
    documents_dir = os.path.join(project_root, "documents")
    raw_filepath = os.path.join(documents_dir, "raw", "syllabus_raw.json")
    output_filepath = os.path.join(documents_dir, "chunks", "syllabus_chunks.json")
    
    if not os.path.exists(raw_filepath):
        print(f"Error: Raw file {raw_filepath} not found. Please run parse_pdf.py first.")
        sys.exit(1)
        
    with open(raw_filepath, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
        
    print(f"Loaded {len(raw_data)} raw syllabus files from {raw_filepath}")
    
    all_chunks = []
    for record in raw_data:
        file_chunks = process_syllabus_sections(record)
        print(f"Generated {len(file_chunks)} chunks for {record.get('source_file')}")
        all_chunks.extend(file_chunks)
        
    # Write chunks to output JSON
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
        
    print(f"\nSyllabus processing complete! Wrote {len(all_chunks)} chunks to {output_filepath}")

if __name__ == "__main__":
    main()
