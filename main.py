from git import Repo
import shutil
import os
from bs4 import BeautifulSoup
import markdown
import stat
from dotenv import load_dotenv
import requests
import google.generativeai as genai
import openai

load_dotenv()  # Load variables from .env
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_BASE = "https://api.groq.com/openai/v1"



def handle_remove_readonly(func, path, exc):
    # Windows: fix for read-only file deletion error
    os.chmod(path, stat.S_IWRITE)
    func(path)

def clone_repo(repo_url, dest_folder="cloned_repo"):
    if os.path.exists(dest_folder):
        print("Repo already cloned. Deleting old one...")
        shutil.rmtree(dest_folder, onerror=handle_remove_readonly)
    print("Cloning...")
    Repo.clone_from(repo_url, dest_folder)
    print(f"Repo cloned to {dest_folder}")

def extract_readme_text(repo_path="cloned_repo"):
    readme_path = os.path.join(repo_path, "README.md")
    if not os.path.exists(readme_path):
        print("README.md not found.")
        return ""

    with open(readme_path, "r", encoding="utf-8") as file:
        md_content = file.read()

    # Convert markdown to HTML
    html = markdown.markdown(md_content)

    # Clean HTML to plain text
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator="\n")
    return text

def summarize_readme(readme_text):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "gpt-3.5-turbo",  # Replace with the desired model (e.g., llama3 or mixtral)
        "messages": [
            {"role": "system", "content": "You are a helpful assistant who summarizes README files."},
            {"role": "user", "content": f"Summarize the following README:\n\n{readme_text}"}
        ],
        "temperature": 0.5
    }

    response = requests.post(f"{GROQ_API_BASE}/chat/completions", json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

# Example usage
with open("README.md", "r", encoding="utf-8") as f:
    readme_text = f.read()
    

if __name__ == "__main__":
    url = input("Enter GitHub repo URL: ")
    clone_repo(url)
    readme_text = extract_readme_text()
    print("\n📘 Extracted README Content:\n")
    print(readme_text[:1000])  # Print only the first 1000 characters
    summary = summarize_readme(readme_text)
    
    if summary:
        print("\n📘 Summary of README:\n")
        print(summary)
