from git import Repo
import shutil
import os
from bs4 import BeautifulSoup
import markdown
import stat
from dotenv import load_dotenv
import requests
import re

load_dotenv()  # Load variables from .env
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_BASE = "https://api.groq.com/openai/v1"

def handle_remove_readonly(func, path, exc):
    
    os.chmod(path, stat.S_IWRITE)
    func(path)

def clean_git_url(repo_url):
    """Remove fragments like #readme from the URL"""
    return repo_url.split('#')[0]

def clone_repo(repo_url, dest_folder="cloned_repo"):
    try:
        # Clean the URL to remove any fragments
        clean_url = clean_git_url(repo_url)
        
        if os.path.exists(dest_folder):
            print("Repo already cloned. Deleting old one...")
            shutil.rmtree(dest_folder, onerror=handle_remove_readonly)
        print(f"Cloning from {clean_url}...")
        Repo.clone_from(clean_url, dest_folder)
        print(f"Repo cloned to {dest_folder}")
        return True
    except Exception as e:
        print(f"Error cloning repository: {e}")
        return False

def extract_readme_text(repo_path="cloned_repo"):
    # Try to find any README file with case insensitive matching
    readme_path = None
    for file in os.listdir(repo_path):
        if file.lower().startswith("readme") and (file.lower().endswith(".md") or file.lower().endswith(".txt")):
            readme_path = os.path.join(repo_path, file)
            break
    
    if not readme_path:
        print("README file not found.")
        return ""

    try:
        with open(readme_path, "r", encoding="utf-8") as file:
            md_content = file.read()

        
        html = markdown.markdown(md_content)

        # Clean HTML to plain text
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")
        return text
    except Exception as e:
        print(f"Error extracting README text: {e}")
        return ""

def truncate_text(text, max_chars=3000):
    """Truncate text to a maximum number of characters while preserving complete sentences."""
    if len(text) <= max_chars:
        return text
    
    # Find the last period, question mark, or exclamation point before max_chars
    last_sentence_end = max(
        text[:max_chars].rfind('.'),
        text[:max_chars].rfind('?'),
        text[:max_chars].rfind('!')
    )
    
    if last_sentence_end == -1:
        # If no sentence end found, just cut at max_chars
        return text[:max_chars] + "..."
    else:
        return text[:last_sentence_end+1] + " [truncated for API limits]"

def summarize_readme(readme_text):
    # Truncate the text to avoid exceeding API limits
    truncated_text = truncate_text(readme_text)
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    prompt = f"""
Summarize the following GitHub README. Focus on:
1) What the project does
2) Key features
3) How to install/use it
4) Any important requirements

README:
{truncated_text}
"""
    
    payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "You are a technical writer who creates concise, accurate summaries of GitHub repositories."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.3,
        "max_tokens": 1000
    }

    try:
        response = requests.post(f"{GROQ_API_BASE}/chat/completions", json=payload, headers=headers)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error with Groq API: {e}")
        if 'response' in locals():
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text}")
        return None

def estimate_tokens(text):
    """Roughly estimate the number of tokens in the text (4 chars ≈ 1 token)"""
    return len(text) // 4

if __name__ == "__main__":
    url = input("Enter GitHub repo URL: ")
    
    if clone_repo(url):
        readme_text = extract_readme_text()
        
        if readme_text:
            # Print only the first 500 characters
            preview = readme_text[:500] + "..." if len(readme_text) > 500 else readme_text
            print("\n📘 Extracted README Content (preview):\n")
            print(preview)
            
            # Estimate tokens
            estimated_tokens = estimate_tokens(readme_text)
            print(f"\nEstimated tokens in full README: ~{estimated_tokens}")
            
            if GROQ_API_KEY:
                print("\nSending truncated README to Groq API for summarization...")
                summary = summarize_readme(readme_text)
                if summary:
                    print("\n📘 Summary of README:\n")
                    print(summary)
            else:
                print("\nError: GROQ_API_KEY not found in environment variables")
        else:
            print("No README content was extracted")