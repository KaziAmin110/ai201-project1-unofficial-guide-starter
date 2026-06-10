import os
import json
import re

def normalize_course(course: str, department: str = "") -> str:
    if not course:
        return ""
    
    # Strip spaces, dashes, convert to upper
    c = re.sub(r'[\s\-]', '', course).upper()
    
    # Map common UCF aliases
    aliases = {
        "CS1": "COP3502C",
        "CS2": "COP3503C",
        "DISCRETE": "COT3100",
        "DISCRETE1": "COT3100",
        "DISCRETESTRUCT": "COT3100",
        "DISCRETESTUCTURES": "COT3100",
        "OOP": "COP3330",
        "SYSSEC": "CIS3360",
        "SYSTEMSECURITY": "CIS3360",
        "INTROTOC": "COP3223C",
    }
    
    if c in aliases:
        return aliases[c]
    
    # Match 3 or 4 digits followed by optional suffix letters (e.g. 3502C, 3502, 3223)
    m = re.match(r'^(\d{3,4})([A-Z]*)$', c)
    if m:
        digits = m.group(1)
        suffix = m.group(2)
        # Prefixes based on department or default to COP
        dept_lower = department.lower() if department else ""
        if "computer science" in dept_lower or "cs" in dept_lower:
            if digits.startswith("3100") or digits.startswith("3100"):
                return f"COT{digits}{suffix}"
            else:
                return f"COP{digits}{suffix}"
        else:
            return f"COP{digits}{suffix}" # fallback prefix
            
    return c

def process_school_reviews(filepath: str) -> list:
    chunks = []
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found.")
        return chunks
        
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for idx, review in enumerate(data):
        comment = review.get("comment", "").strip()
        if not comment:
            continue
            
        overall = review.get("overall_rating")
        date = review.get("date", "Unknown Date")
        sub_ratings = review.get("sub_ratings", {})
        
        # Build sub-ratings key-value string
        sub_ratings_str = ", ".join(f"{k.capitalize()}: {v}" for k, v in sub_ratings.items())
        
        # Format chunk text
        text_parts = [
            "University: University of Central Florida",
            f"Overall Rating: {overall}"
        ]
        if sub_ratings_str:
            text_parts.append(f"Ratings: {sub_ratings_str}")
        text_parts.append(f"Review: {comment}")
        
        chunk_text = " | ".join(text_parts)
        
        # Construct chunk object
        chunk = {
          "id": f"rmp_school_{idx:03d}",
          "text": chunk_text,
          "source": "Rate My Professor - UCF Overall",
          "source_type": "rmp",
          "metadata": {
            "review_type": "school",
            "source_file": os.path.basename(filepath),
            "overall_rating": overall,
            "date": date
          }
        }
        chunks.append(chunk)
        
    return chunks

def process_professor_reviews(filepath: str) -> list:
    chunks = []
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found.")
        return chunks
        
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    for idx, review in enumerate(data):
        prof_name = review.get("professor_name", "Unknown Professor")
        dept = review.get("department", "")
        school = review.get("school_name", "University of Central Florida")
        raw_course = review.get("course_code", "")
        normalized_course = normalize_course(raw_course, dept)
        
        quality = review.get("quality_rating")
        difficulty = review.get("difficulty_rating")
        date = review.get("date", "Unknown Date")
        comment = review.get("comment", "").strip()
        if not comment:
            continue
            
        details = review.get("details", {})
        
        # Format chunk text
        text_parts = [
            f"Professor: {prof_name}",
            f"Course: {normalized_course}"
        ]
        
        if quality is not None:
            text_parts.append(f"Quality: {quality}")
        if difficulty is not None:
            text_parts.append(f"Difficulty: {difficulty}")
            
        # Add details if present and valid
        for detail_key, detail_val in details.items():
            if detail_val not in (None, "", "N/A", "n/a"):
                # Clean up labels (e.g. attendance_mandatory -> Attendance)
                label = detail_key.replace("_", " ").title()
                # Special casing cleanups
                if label == "Attendance Mandatory":
                    label = "Attendance"
                    detail_val = "Mandatory" if detail_val is True else "Not Mandatory"
                elif label == "For Credit":
                    label = "For Credit"
                    detail_val = "Yes" if detail_val is True else "No"
                
                text_parts.append(f"{label}: {detail_val}")
                
        text_parts.append(f"Review: {comment}")
        chunk_text = " | ".join(text_parts)
        
        # Clean prof name slug for chunk ID
        prof_slug = re.sub(r'[^a-zA-Z0-9]', '_', prof_name.lower())
        
        chunk = {
          "id": f"rmp_prof_{prof_slug}_{idx:03d}",
          "text": chunk_text,
          "source": f"Rate My Professor - {prof_name}",
          "source_type": "rmp",
          "metadata": {
            "review_type": "professor",
            "source_file": os.path.basename(filepath),
            "professor_name": prof_name,
            "department": dept,
            "course_code": normalized_course,
            "original_course_code": raw_course,
            "quality_rating": quality,
            "difficulty_rating": difficulty,
            "date": date
          }
        }
        chunks.append(chunk)
        
    return chunks

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    documents_dir = os.path.join(project_root, "documents")
    
    school_filepath = os.path.join(documents_dir, "raw", "rmp_school.json")
    prof_filepath = os.path.join(documents_dir, "raw", "rmp_professors.json")
    output_filepath = os.path.join(documents_dir, "chunks", "rmp_chunks.json")
    
    print("Starting Rate My Professor ingestion pipeline...")
    
    school_chunks = process_school_reviews(school_filepath)
    print(f"Parsed {len(school_chunks)} school overall review chunks.")
    
    prof_chunks = process_professor_reviews(prof_filepath)
    print(f"Parsed {len(prof_chunks)} professor review chunks.")
    
    all_chunks = school_chunks + prof_chunks
    
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully wrote {len(all_chunks)} total chunks to {output_filepath}")

if __name__ == "__main__":
    main()
