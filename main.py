from git import Repo
import shutil
import os
from bs4 import BeautifulSoup
import markdown
import stat
from dotenv import load_dotenv
import requests
import re
import json
from pathlib import Path

load_dotenv()  # Load variables from .env
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_BASE = "https://api.groq.com/openai/v1"

def handle_remove_readonly(func, path, exc):
    # Windows: fix for read-only file deletion error
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

        # Convert markdown to HTML
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

def map_repo_structure(repo_path="cloned_repo", max_depth=4, exclude_dirs=['.git']):
    """Create a map of the repository structure (files and folders)"""
    repo_map = {}
    
    def _explore_dir(path, current_dict, current_depth=0):
        if current_depth > max_depth:
            return
        
        # Skip excluded directories
        path_name = os.path.basename(path)
        if path_name in exclude_dirs:
            return
            
        try:
            for item in os.listdir(path):
                item_path = os.path.join(path, item)
                
                # Skip hidden files/directories
                if item.startswith('.'):
                    continue
                    
                if os.path.isdir(item_path):
                    # Create a new dictionary for the subdirectory
                    current_dict[item] = {}
                    _explore_dir(item_path, current_dict[item], current_depth + 1)
                else:
                    # Store file with its extension
                    current_dict[item] = "file"
        except Exception as e:
            print(f"Error exploring directory {path}: {e}")
    
    _explore_dir(repo_path, repo_map)
    return repo_map

def get_important_files(repo_path="cloned_repo"):
    """Identify important files in the repository (package.json, requirements.txt, etc.)"""
    important_files = []
    important_patterns = [
        'package.json', 'requirements.txt', 'setup.py', 'Dockerfile', 
        'docker-compose.yml', 'Makefile', 'CMakeLists.txt', 'build.gradle',
        'pom.xml', 'Gemfile', 'Cargo.toml', 'go.mod', '.env.example'
    ]
    
    for root, _, files in os.walk(repo_path):
        if '.git' in root:  # Skip .git directory
            continue
            
        for file in files:
            if file in important_patterns:
                rel_path = os.path.relpath(os.path.join(root, file), repo_path)
                important_files.append(rel_path)
                
    return important_files

def analyze_file_types(repo_path="cloned_repo"):
    """Analyze the types of files in the repo to understand the tech stack"""
    extension_count = {}
    ignore_dirs = ['.git']
    
    for root, dirs, files in os.walk(repo_path):
        # Skip ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs and not d.startswith('.')]
        
        for file in files:
            if file.startswith('.'):
                continue
                
            _, ext = os.path.splitext(file)
            if ext:
                extension_count[ext] = extension_count.get(ext, 0) + 1
    
    # Sort by frequency
    return dict(sorted(extension_count.items(), key=lambda x: x[1], reverse=True))

def generate_project_structure_visualization(repo_map, important_files=None, output_file="project_structure.md"):
    """Generate a Mermaid flowchart visualization of the project structure"""
    if important_files is None:
        important_files = []
    
    # Start building the Mermaid diagram
    mermaid_diagram = ["```mermaid", "flowchart TD"]
    
    # Add main project node
    project_name = os.path.basename(os.path.abspath("cloned_repo"))
    mermaid_diagram.append(f"    Project[\"{project_name}\"]")
    
    # Helper function to process the repo map
    def process_directory(parent_id, directory, path_prefix=""):
        node_ids = []
        
        for name, content in directory.items():
            # Create a unique ID for this node
            node_id = f"{parent_id}_{name.replace('.', '_').replace('-', '_').replace(' ', '_')}"
            full_path = f"{path_prefix}/{name}" if path_prefix else name
            
            if content == "file":
                # Check if this is an important file
                if full_path in important_files:
                    mermaid_diagram.append(f"    {node_id}[\"{name}\"] --> |Important File|")
                    mermaid_diagram.append(f"    {node_id}_link([\"Link to {full_path}\"])")
                else:
                    mermaid_diagram.append(f"    {node_id}[\"{name}\"]")
                
                node_ids.append(node_id)
            else:
                # Directory
                mermaid_diagram.append(f"    {node_id}[\"📁 {name}\"]")
                child_ids = process_directory(node_id, content, full_path)
                
                # Connect children to this directory
                for child_id in child_ids:
                    mermaid_diagram.append(f"    {node_id} --> {child_id}")
                
                node_ids.append(node_id)
        
        return node_ids
    
    # Process the root directories
    root_node_ids = []
    for name, content in repo_map.items():
        node_id = f"dir_{name.replace('.', '_').replace('-', '_').replace(' ', '_')}"
        
        if content == "file":
            mermaid_diagram.append(f"    {node_id}[\"{name}\"]")
        else:
            mermaid_diagram.append(f"    {node_id}[\"📁 {name}\"]")
            child_ids = process_directory(node_id, content, name)
            
            # Connect children to this directory
            for child_id in child_ids:
                mermaid_diagram.append(f"    {node_id} --> {child_id}")
                
        root_node_ids.append(node_id)
    
    # Connect project to root directories
    for node_id in root_node_ids:
        mermaid_diagram.append(f"    Project --> {node_id}")
    
    # Close the diagram
    mermaid_diagram.append("```")
    
    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(mermaid_diagram))
    
    return mermaid_diagram

def generate_repo_analysis(summary, repo_map, important_files, file_types, repo_url, output_file="repo_analysis.md"):
    """Generate a comprehensive analysis of the repository"""
    analysis = [
        "# Repository Analysis Report",
        f"\nRepository URL: {repo_url}",
        "\n## Summary",
        summary,
        "\n## Important Files",
    ]
    
    # Add important files section
    if important_files:
        for file in important_files:
            analysis.append(f"- `{file}`")
    else:
        analysis.append("No standard configuration files detected.")
    
    # Add technology stack based on file extensions
    analysis.append("\n## Technology Stack (Based on File Extensions)")
    if file_types:
        for ext, count in list(file_types.items())[:10]:  # Top 10 extensions
            analysis.append(f"- {ext}: {count} files")
    
    # Add project structure visualization
    analysis.append("\n## Project Structure")
    analysis.append("The following diagram shows the main structure of the repository:")
    
    # Include the mermaid diagram
    with open("project_structure.md", "r", encoding="utf-8") as f:
        structure_diagram = f.read()
    
    analysis.append(structure_diagram)
    
    # Add contribution suggestions
    analysis.append("\n## Getting Started for Contributors")
    analysis.append("""
Based on the repository structure, here are some suggestions for new contributors:

1. Explore the important files listed above to understand the project configuration
2. Check for CONTRIBUTING.md or similar files that may contain contribution guidelines
3. Look for tests directories to understand how to test your changes
4. Set up the development environment according to the README instructions
5. Start with small, well-defined issues or improvements
""")
    
    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(analysis))
    
    return output_file

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
            
            summary = None
            
            if GROQ_API_KEY:
                print("\nSending truncated README to Groq API for summarization...")
                summary = summarize_readme(readme_text)
                if summary:
                    print("\n📘 Summary of README:\n")
                    print(summary)
            else:
                print("\nWARNING: GROQ_API_KEY not found in environment variables - skipping summary generation")
                summary = "No summary generated (API key missing). Please provide GROQ_API_KEY in .env file."
            
            print("\nGenerating repository structure visualization...")
            
            # Map repository structure
            repo_map = map_repo_structure()
            
            # Get important files
            important_files = get_important_files()
            print(f"\nFound {len(important_files)} important configuration files.")
            
            # Analyze file types
            file_types = analyze_file_types()
            print("\nFile extension analysis (top 5):")
            for ext, count in list(file_types.items())[:5]:
                print(f"- {ext}: {count} files")
            
            # Generate visualization
            mermaid_diagram = generate_project_structure_visualization(repo_map, important_files)
            print("\nGenerated project structure diagram in project_structure.md")
            
            # Generate comprehensive analysis
            analysis_file = generate_repo_analysis(summary, repo_map, important_files, file_types, url)
            print(f"\nComplete repository analysis saved to {analysis_file}")
            print(f"\nOpen {analysis_file} to view the complete analysis with repository structure visualization.")
        else:
            print("No README content was extracted")