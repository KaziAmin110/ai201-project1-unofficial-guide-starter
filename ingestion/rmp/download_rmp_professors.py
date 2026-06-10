import requests
import json
import time
import random
import sys
import os

# 1. Apply the User-Agent monkey-patch to requests.get to bypass Cloudflare/403 blocks
original_get = requests.get
def patched_get(url, *args, **kwargs):
    if "headers" not in kwargs or kwargs["headers"] is None:
        kwargs["headers"] = {}
    kwargs["headers"]["User-Agent"] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
    return original_get(url, *args, **kwargs)

requests.get = patched_get

import ratemyprofessor

def main():
    # List of UCF professors to search and download
    target_professors = [
        "Travis Meade",
        "Andrew Steinberg",
        "Arup Guha",
        "Mark Llewellyn",
        "Mark Heinrich",
        "Euripides Montagne",
        "Sarah Angell"
    ]
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    output_filepath = os.path.join(project_root, "documents", "raw", "rmp_professors.json")
    
    print("Initializing Rate My Professor UCF downloader...")
    
    # Resolve UCF School Object (UCF RMP ID is 1082 or 5567)
    # 1082 is the official school rating ID
    try:
        school = ratemyprofessor.School(1082)
        print(f"Set school to: {school.name} (ID: {school.id})")
    except Exception as e:
        print(f"Failed to load school ID 1082: {e}")
        print("Falling back to search...")
        schools = ratemyprofessor.get_schools_by_name("University of Central Florida")
        school = None
        for s in schools:
            if s.name == "University of Central Florida":
                school = s
                break
        if school is None:
            print("ERROR: Could not resolve UCF school object.")
            sys.exit(1)
            
    print(f"Using School: {school.name} (ID: {school.id})")
    
    all_professor_reviews = []
    
    for prof_name in target_professors:
        if not prof_name.strip():
            continue
        print(f"\nSearching for '{prof_name}'...")
        try:
            professors = ratemyprofessor.get_professors_by_school_and_name(school, prof_name)
            professor = None
            for p in professors:
                if p.name.strip().lower() == prof_name.strip().lower():
                    professor = p
                    break
                    
            if professor is None:
                print(f"WARNING: Could not find exact match for professor '{prof_name}' at UCF. Skipping.")
                continue
                
            print(f"Found: {professor.name} | Department: {professor.department} | Total Ratings: {professor.num_ratings}")
            print(f"Fetching ratings list...")
            
            ratings = professor.get_ratings()
            print(f"Successfully retrieved {len(ratings)} reviews.")
            
            for r in ratings:
                # Format match with raw schema expected by ingest_rmp.py
                review_data = {
                    "professor_name": professor.name,
                    "department": professor.department,
                    "school_name": school.name,
                    "course_code": r.class_name,
                    "quality_rating": r.rating,
                    "difficulty_rating": r.difficulty,
                    "date": r.date.strftime("%b %d, %Y") if hasattr(r.date, "strftime") else str(r.date),
                    "comment": r.comment,
                    "details": {
                        "attendance_mandatory": getattr(r, "attendance", "N/A"),
                        "grade_received": getattr(r, "grade", "N/A"),
                        "textbook_used": getattr(r, "textbook", "N/A"),
                        "for_credit": getattr(r, "taken_for_credit", "N/A")
                    }
                }
                all_professor_reviews.append(review_data)
                
            # Random delay to prevent IP blocking
            sleep_time = random.uniform(1.5, 3.5)
            print(f"Sleeping for {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
            
        except Exception as ex:
            print(f"Error fetching data for '{prof_name}': {ex}")
            continue
            
    # Write aggregated data to target raw file
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(all_professor_reviews, f, indent=2, ensure_ascii=False)
        
    print(f"\nDownloader complete. Saved {len(all_professor_reviews)} reviews to {output_filepath}")

if __name__ == "__main__":
    main()
