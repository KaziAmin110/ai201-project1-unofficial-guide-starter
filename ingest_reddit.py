import os
import json
import re
from datetime import datetime

def clean_reddit_text(text: str) -> str:
    if not text:
        return ""
    # Strip common reddit placeholders
    cleaned = text.strip()
    if cleaned in ("[deleted]", "[removed]"):
        return ""
    # Normalize multiple newlines/spaces
    cleaned = re.sub(r'\s+', ' ', cleaned)
    return cleaned

def process_reddit_threads(filepath: str) -> list:
    chunks = []
    if not os.path.exists(filepath):
        print(f"Warning: {filepath} not found.")
        return chunks
        
    with open(filepath, "r", encoding="utf-8") as f:
        threads = json.load(f)
        
    for thread in threads:
        post_id = thread.get("id")
        title = thread.get("title", "No Title").strip()
        selftext = clean_reddit_text(thread.get("selftext", ""))
        post_author = thread.get("author", "unknown")
        flair = thread.get("link_flair_text", "None")
        post_score = thread.get("score", 0)
        post_url = thread.get("url", "")
        
        # Convert created_utc to standard date string
        created_utc = thread.get("created_utc")
        if created_utc:
            try:
                post_date = datetime.fromtimestamp(created_utc).strftime("%b %d, %Y")
            except Exception:
                post_date = "Unknown Date"
        else:
            post_date = "Unknown Date"
            
        comments = thread.get("comments", [])
        
        # Build map of comment ID -> comment dict
        comments_map = {c["id"]: c for c in comments if c.get("id")}
        
        # Identify top-level comments (parent_id starts with t3_ representing the post)
        top_level_comments = [
            c for c in comments 
            if c.get("parent_id", "").startswith("t3_")
        ]
        
        # Group replies by their parent top-level comment ID
        replies_by_parent = {}
        for c in comments:
            parent_id = c.get("parent_id", "")
            if parent_id.startswith("t1_"):
                parent_comment_id = parent_id.split("_")[1]
                if parent_comment_id in comments_map:
                    replies_by_parent.setdefault(parent_comment_id, []).append(c)
                    
        # Check if we have any valid top-level comments
        valid_comments_found = False
        
        for t_com in top_level_comments:
            comment_id = t_com["id"]
            com_author = t_com.get("author", "unknown")
            com_body = clean_reddit_text(t_com.get("body", ""))
            com_score = t_com.get("score", 0)
            
            # Skip empty or deleted comments
            if not com_body or com_author in ("[deleted]", "[removed]"):
                continue
                
            valid_comments_found = True
            
            # Gather replies to this comment
            replies = replies_by_parent.get(comment_id, [])
            replies_text_list = []
            
            for reply in replies:
                rep_author = reply.get("author", "unknown")
                rep_body = clean_reddit_text(reply.get("body", ""))
                if rep_body and rep_author not in ("[deleted]", "[removed]"):
                    replies_text_list.append(f"\n\t -> {rep_author}: {rep_body}")
                    
            replies_str = "".join(replies_text_list)
            
            # Construct chunk text according to spec:
            # "Subreddit: r/ucf | Thread: [Post Title] | Post: [Post Content] | Discussion: [Comment Author]: [Comment Text] \n\t -> [Reply Author]: [Reply Text]"
            text_parts = [
                "Subreddit: r/ucf",
                f"Thread: {title}"
            ]
            if selftext:
                text_parts.append(f"Post: {selftext}")
            
            discussion_str = f"Discussion: {com_author}: {com_body}{replies_str}"
            text_parts.append(discussion_str)
            
            chunk_text = " | ".join(text_parts)
            
            chunk = {
                "id": f"reddit_thread_{post_id}_{comment_id}",
                "text": chunk_text,
                "source": f"Reddit r/ucf - {title}",
                "source_type": "reddit",
                "metadata": {
                    "review_type": "reddit_thread",
                    "source_file": os.path.basename(filepath),
                    "post_id": post_id,
                    "post_title": title,
                    "post_url": post_url,
                    "post_flair": flair,
                    "post_score": post_score,
                    "post_date": post_date,
                    "comment_id": comment_id,
                    "comment_author": com_author,
                    "comment_score": com_score
                }
            }
            chunks.append(chunk)
            
        # If no valid comments were found, index the post alone to prevent losing context
        if not valid_comments_found:
            text_parts = [
                "Subreddit: r/ucf",
                f"Thread: {title}"
            ]
            if selftext:
                text_parts.append(f"Post: {selftext}")
            text_parts.append("Discussion: No comments on this thread.")
            
            chunk_text = " | ".join(text_parts)
            
            chunk = {
                "id": f"reddit_post_{post_id}",
                "text": chunk_text,
                "source": f"Reddit r/ucf - {title}",
                "source_type": "reddit",
                "metadata": {
                    "review_type": "reddit_thread",
                    "source_file": os.path.basename(filepath),
                    "post_id": post_id,
                    "post_title": title,
                    "post_url": post_url,
                    "post_flair": flair,
                    "post_score": post_score,
                    "post_date": post_date,
                    "comment_id": "None",
                    "comment_author": "None",
                    "comment_score": 0
                }
            }
            chunks.append(chunk)
            
    return chunks

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    documents_dir = os.path.join(script_dir, "documents")
    
    raw_filepath = os.path.join(documents_dir, "reddit_raw.json")
    output_filepath = os.path.join(documents_dir, "reddit_chunks.json")
    
    print("Starting UCF Subreddit ingestion pipeline...")
    
    reddit_chunks = process_reddit_threads(raw_filepath)
    print(f"Parsed {len(reddit_chunks)} reddit chunks.")
    
    with open(output_filepath, "w", encoding="utf-8") as f:
        json.dump(reddit_chunks, f, indent=2, ensure_ascii=False)
        
    print(f"Successfully wrote {len(reddit_chunks)} chunks to {output_filepath}")

if __name__ == "__main__":
    main()
