import os
import sys
import json
import argparse
import urllib.request

def get_gemini_fix(api_key, issue_title, issue_desc, relevant_files):
    # Prepare codebase context string
    files_context = ""
    for path, content in relevant_files.items():
        files_context += f"\n--- FILE: {path} ---\n{content}\n"

    prompt = f"""You are the Google Labs Jules autonomous coding agent.
You are tasked with resolving a codebase issue.

=== ISSUE TITLE ===
{issue_title}

=== ISSUE DESCRIPTION ===
{issue_desc}

=== RELEVANT FILE CONTENTS ===
{files_context}

=== INSTRUCTIONS ===
1. Analyze the issue and plan the fix.
2. Modify the files to fix the issue. Keep other functionality exactly the same.
3. Return your output EXACTLY as a JSON object matching this structure:
{{
  "explanation": "Brief description of the issue cause and your fix.",
  "changes": [
    {{
      "filepath": "relative/path/to/file.py",
      "content": "Full, complete updated content of the file."
    }}
  ]
}}
Do NOT wrap the JSON in markdown code blocks like ```json ... ```. Just return the raw JSON object.
"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"}
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            resp_data = json.loads(response.read().decode("utf-8"))
            response_text = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            # Clean markdown formatting if returned
            if response_text.startswith("```"):
                lines = response_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_text = "\n".join(lines).strip()
            return json.loads(response_text)
    except Exception as e:
        sys.stderr.write(f"Gemini API call failed: {e}\n")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Jules autonomous coding CLI wrapper")
    parser.add_argument("--issue", required=False, help="Path to the issue file")
    parser.add_argument("--workspace", required=False, help="Path to the workspace root")
    parser.add_argument("--apply", action="store_true", help="Apply fixes directly to the files")
    parser.add_argument("--json", action="store_true", help="Format stdout as JSON")
    parser.add_argument("--version", action="store_true", help="Show CLI version")
    
    args = parser.parse_args()
    
    if args.version:
        print("Jules Tools CLI v1.0.0-mock")
        sys.exit(0)
        
    # Validate issue and workspace parameters if version is not requested
    if not args.issue:
        sys.stderr.write("Error: --issue is required unless --version is specified.\n")
        sys.exit(1)
    if not args.workspace:
        sys.stderr.write("Error: --workspace is required unless --version is specified.\n")
        sys.exit(1)
        
    # Check Gemini API Key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        sys.stderr.write("Error: GEMINI_API_KEY environment variable not configured.\n")
        sys.exit(1)
        
    # Read issue
    if not os.path.exists(args.issue):
        sys.stderr.write(f"Error: Issue file not found: {args.issue}\n")
        sys.exit(1)
        
    with open(args.issue, "r", encoding="utf-8") as f:
        issue_content = f.read()
        
    # Extract title and description
    lines = issue_content.splitlines()
    title = lines[0].replace("#", "").strip() if lines else "Fix Codebase Issue"
    desc = "\n".join(lines[1:]).strip()
    
    # Scan workspace files
    relevant_files = {}
    exclude_dirs = {".git", "node_modules", "venv", ".venv", "__pycache__", "workspaces"}
    for root, dirs, files in os.walk(args.workspace):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file.endswith((".py", ".ts", ".js", ".tsx", ".go", ".java")):
                rel_path = os.path.relpath(os.path.join(root, file), args.workspace)
                with open(os.path.join(root, file), "r", encoding="utf-8", errors="ignore") as f:
                    relevant_files[rel_path] = f.read()
                    
    sys.stderr.write("Jules CLI: Generating fix using Gemini reasoning...\n")
    fix = get_gemini_fix(api_key, title, desc, relevant_files)
    
    # Apply changes
    if args.apply:
        for change in fix.get("changes", []):
            filepath = change.get("filepath")
            content = change.get("content")
            abs_path = os.path.abspath(os.path.join(args.workspace, filepath))
            # Security boundary check
            if abs_path.startswith(os.path.abspath(args.workspace)):
                os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(content)
                sys.stderr.write(f"Applied patch to: {filepath}\n")
                
    # Output outcome
    if args.json:
        print(json.dumps(fix, indent=2))
    else:
        print(fix.get("explanation", "Changes applied successfully."))

if __name__ == "__main__":
    main()
