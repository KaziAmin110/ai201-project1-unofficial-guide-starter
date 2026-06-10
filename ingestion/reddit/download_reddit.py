import requests
import json
import time
import random
import os
import sys

def fetch_with_retry(url, headers, max_retries=5, timeout=30):
    for attempt in range(max_retries):
        try:
            r = requests.get(url, headers=headers, timeout=timeout)
            if r.status_code == 200:
                return r.json().get("data", [])
            print(f"WARNING: Server returned status {r.status_code} for URL: {url}. Retrying...")
        except (requests.exceptions.Timeout, requests.exceptions.RequestException) as e:
            print(f"WARNING: Request failed: {e} for URL: {url}. Retrying...")
        
        # Exponential backoff with jitter
        sleep_time = (2 ** attempt) + random.uniform(1, 3)
        print(f"Sleeping for {sleep_time:.2f} seconds before retrying...")
        time.sleep(sleep_time)
        
    print(f"ERROR: Failed to retrieve data from URL after {max_retries} attempts.")
    return None

def main():
    print("Starting UCF Subreddit PullPush downloader...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(script_dir))
    output_filepath = os.path.join(project_root, "documents", "raw", "reddit_raw.json")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Fetch 250 submissions to ensure we find plenty of academic-flaired posts
    submissions_url = "https://api.pullpush.io/reddit/search/submission/?subreddit=ucf&size=250"
    
    submissions = fetch_with_retry(submissions_url, headers)
    if submissions is None:
        print("ERROR: Could not fetch submissions from PullPush API. Exiting.")
        sys.exit(1)
        
    print(f"Fetched {len(submissions)} total submissions.")
    
    # Step 2: Filter submissions locally by link_flair_text
    filtered_submissions = []
    for sub in submissions:
        flair = (sub.get("link_flair_text") or "").lower()
        
        # Check if flair contains "academic" (matches "Academic ✏️", "Academic Program 🎓", etc.)
        if "academic" in flair:
            filtered_submissions.append(sub)
            
    print(f"Filtered down to {len(filtered_submissions)} submissions with 'Academic' flairs.")
    
    if not filtered_submissions:
        print("WARNING: No submissions matched the 'Academic' flair filter. Retrying with a search query fallback...")
        submissions_url_fallback = "https://api.pullpush.io/reddit/search/submission/?subreddit=ucf&q=academic&size=50"
        fallback_subs = fetch_with_retry(submissions_url_fallback, headers)
        if fallback_subs:
            filtered_submissions = fallback_subs
            print(f"Fallback matched {len(filtered_submissions)} submissions.")
        else:
            print("ERROR: Fallback search query also failed. Exiting.")
            sys.exit(1)
            
    # Step 3: Fetch comments for each filtered submission
    threads_data = []
    
    for idx, sub in enumerate(filtered_submissions):
        sub_id = sub.get("id")
        title = sub.get("title", "No Title")
        selftext = sub.get("selftext", "")
        author = sub.get("author", "unknown")
        flair = sub.get("link_flair_text", "None")
        score = sub.get("score", 0)
        url = sub.get("url", "")
        
        print(f"[{idx+1}/{len(filtered_submissions)}] Fetching comments for post: '{title[:50]}...' (ID: {sub_id})")
        
        comments_url = f"https://api.pullpush.io/reddit/search/comment/?link_id=t3_{sub_id}&size=100"
        
        # Fetch comments using the retry helper
        comments_data = fetch_with_retry(comments_url, headers, max_retries=3, timeout=20)
        comments = []
        
        if comments_data:
            for comment in comments_data:
                comments.append({
                    "id": comment.get("id"),
                    "parent_id": comment.get("parent_id"),
                    "author": comment.get("author", "unknown"),
                    "body": comment.get("body", ""),
                    "score": comment.get("score", 0),
                    "created_utc": comment.get("created_utc")
                })
        else:
            print(f"  WARNING: Failed to fetch comments for {sub_id} after retries.")
            
        threads_data.append({
            "id": sub_id,
            "title": title,
            "selftext": selftext,
            "author": author,
            "link_flair_text": flair,
            "score": score,
            "url": url,
            "created_utc": sub.get("created_utc"),
            "comments": comments
        })
        
        # Respect API rate limits between submissions
        time.sleep(random.uniform(0.5, 1.5))
        
    # Step 4: Write to documents/reddit_raw.json
    os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(threads_data, f, indent=2, ensure_ascii=False)
        
    print(f"\nDownloader complete. Successfully saved {len(threads_data)} threads to {output_filepath}")

if __name__ == "__main__":
    main()
