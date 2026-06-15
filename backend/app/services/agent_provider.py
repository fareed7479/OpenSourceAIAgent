import os
import json
import httpx
import logging
import subprocess
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

# Add tools/jules to PATH dynamically
try:
    _current_dir = os.path.dirname(os.path.abspath(__file__))
    _project_root = os.path.abspath(os.path.join(_current_dir, "..", "..", ".."))
    _jules_dir = os.path.join(_project_root, "tools", "jules")
    if os.path.exists(_jules_dir):
        _path_env = os.environ.get("PATH", "")
        if _jules_dir not in _path_env:
            os.environ["PATH"] = _jules_dir + os.path.pathsep + _path_env
            logger.info(f"Dynamically added Jules CLI directory to PATH: {_jules_dir}")
except Exception as _e:
    logger.error(f"Failed to dynamically add Jules CLI directory to PATH: {_e}")

class BaseCodingAgent(ABC):
    @abstractmethod
    def generate_fix(
        self,
        issue_title: str,
        issue_desc: str,
        file_tree: List[str],
        relevant_files: Dict[str, str],
        contribution_rules: str,
        workspace_path: str
    ) -> Dict[str, Any]:
        """
        Executes code generation and returns a dictionary with:
        - explanation: Str (brief description of the fix)
        - changes: List[Dict[str, str]] (list of file changes containing filepath and content)
        """
        pass


class JulesCodingAgent(BaseCodingAgent):
    """
    Jules is the primary autonomous coding provider.
    Tries to execute the Jules CLI tool in the repository workspace.
    Falls back to LLM generation if the CLI tool is not installed locally.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def generate_fix(
        self,
        issue_title: str,
        issue_desc: str,
        file_tree: List[str],
        relevant_files: Dict[str, str],
        contribution_rules: str,
        workspace_path: str
    ) -> Dict[str, Any]:
        logger.info(f"Invoking Jules Coding Agent in workspace: {workspace_path}")
        
        # 1. Attempt to run real Jules CLI command if available
        # e.g., jules --issue-title "title" --issue-desc "desc" --apply
        try:
            # Check if jules command is available
            use_shell = os.name == "nt"
            res = subprocess.run(["jules", "--version"], shell=use_shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0:
                logger.info("Jules CLI detected. Spawning subprocess to implement fix...")
                # Write issue description to a temp file first for Jules to ingest
                issue_path = os.path.join(workspace_path, ".jules_issue.md")
                with open(issue_path, "w", encoding="utf-8") as f:
                    f.write(f"# {issue_title}\n\n{issue_desc}")
                
                cmd = ["jules", "--issue", ".jules_issue.md", "--workspace", ".", "--apply", "--json"]
                logger.info(f"Running Jules command: {' '.join(cmd)}")
                
                jules_run = subprocess.run(
                    cmd,
                    cwd=workspace_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    shell=use_shell,
                    timeout=300.0
                )
                
                # Try to clean up temp issue file
                if os.path.exists(issue_path):
                    os.remove(issue_path)

                if jules_run.returncode == 0:
                    try:
                        # Attempt to parse json outcome from Jules CLI
                        return json.loads(jules_run.stdout)
                    except json.JSONDecodeError:
                        logger.warning("Jules executed successfully but stdout was not valid JSON. Querying git changes.")
                else:
                    logger.error(f"Jules CLI execution failed: {jules_run.stderr}")
        except FileNotFoundError:
            logger.warning("Jules CLI binary ('jules') not found on system PATH.")
        except Exception as e:
            logger.error(f"Error running Jules CLI: {e}")

        # 2. Fallback to Gemini LLM provider engine if CLI fails or is missing
        logger.info("Jules falling back to default LLM engine backend...")
        fallback_agent = GeminiCodingAgent(api_key=self.api_key or settings.GEMINI_API_KEY)
        return fallback_agent.generate_fix(
            issue_title=issue_title,
            issue_desc=issue_desc,
            file_tree=file_tree,
            relevant_files=relevant_files,
            contribution_rules=contribution_rules,
            workspace_path=workspace_path
        )


class OpenHandsCodingAgent(BaseCodingAgent):
    """
    OpenHands is a first-class coding provider interfacing with the OpenHands API server.
    Falls back to LLM generation if the server is unreachable.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: str = "http://localhost:3000"):
        self.api_key = api_key
        self.base_url = base_url

    def generate_fix(
        self,
        issue_title: str,
        issue_desc: str,
        file_tree: List[str],
        relevant_files: Dict[str, str],
        contribution_rules: str,
        workspace_path: str
    ) -> Dict[str, Any]:
        logger.info(f"Invoking OpenHands Agent at: {self.base_url} (workspace: {workspace_path})")
        
        # 1. Attempt to interact with the OpenHands REST API
        try:
            # API endpoint to trigger OpenHands agent run on a local workspace path
            url = f"{self.base_url}/api/agents/run"
            payload = {
                "workspace_path": os.path.abspath(workspace_path),
                "instruction": f"Fix this issue:\nTitle: {issue_title}\nDescription:\n{issue_desc}",
                "model": "gpt-4o"  # default model selection
            }
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
                
            response = httpx.post(url, json=payload, headers=headers, timeout=120.0)
            if response.status_code == 200:
                logger.info("OpenHands agent completed task successfully.")
                # Return parsed changes
                return response.json()
            else:
                logger.error(f"OpenHands API returned error status {response.status_code}: {response.text}")
        except Exception as e:
            logger.warning(f"Failed to communicate with OpenHands API: {e}")

        # 2. Try CLI execution fallback
        try:
            # Check if openhands-run CLI is available
            use_shell = os.name == "nt"
            res = subprocess.run(["openhands-run", "--version"], shell=use_shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if res.returncode == 0:
                logger.info("OpenHands CLI detected. Spawning local workspace task...")
                cmd = ["openhands-run", "--path", ".", "--instruction", f"Issue: {issue_title}. {issue_desc[:500]}"]
                jules_run = subprocess.run(
                    cmd,
                    cwd=workspace_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    shell=use_shell,
                    timeout=200.0
                )
                if jules_run.returncode == 0:
                    return {"explanation": "Fixed using OpenHands CLI.", "changes": []}
        except Exception as cli_err:
             logger.warning(f"OpenHands CLI check skipped: {cli_err}")

        # 3. Fallback to Gemini if OpenHands API and CLI are unavailable
        logger.info("OpenHands falling back to default LLM engine backend...")
        fallback_agent = GeminiCodingAgent(api_key=self.api_key or settings.GEMINI_API_KEY)
        return fallback_agent.generate_fix(
            issue_title=issue_title,
            issue_desc=issue_desc,
            file_tree=file_tree,
            relevant_files=relevant_files,
            contribution_rules=contribution_rules,
            workspace_path=workspace_path
        )


class ClaudeCodeCodingAgent(BaseCodingAgent):
    """Claude Code CLI provider wrapper."""
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def generate_fix(
        self,
        issue_title: str,
        issue_desc: str,
        file_tree: List[str],
        relevant_files: Dict[str, str],
        contribution_rules: str,
        workspace_path: str
    ) -> Dict[str, Any]:
        logger.info(f"Invoking Claude Code CLI wrapper in workspace: {workspace_path}")
        # Run local 'claude' CLI command if installed
        try:
            # claude -p "message instructions" --yes
            cmd = ["claude", "-p", f"Fix issue: {issue_title}. Description: {issue_desc[:400]}", "--yes"]
            env = os.environ.copy()
            if self.api_key:
                env["ANTHROPIC_API_KEY"] = self.api_key
                
            res = subprocess.run(cmd, cwd=workspace_path, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=180.0)
            if res.returncode == 0:
                logger.info("Claude Code CLI executed successfully.")
                return {"explanation": "Applied changes via Claude Code CLI.", "changes": []}
        except Exception as e:
            logger.warning(f"Claude Code CLI execution skipped/failed: {e}")

        # Fallback
        fallback_agent = GeminiCodingAgent(api_key=settings.GEMINI_API_KEY)
        return fallback_agent.generate_fix(
            issue_title=issue_title,
            issue_desc=issue_desc,
            file_tree=file_tree,
            relevant_files=relevant_files,
            contribution_rules=contribution_rules,
            workspace_path=workspace_path
        )


class AiderCodingAgent(BaseCodingAgent):
    """Aider Coding Agent CLI provider wrapper."""
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key

    def generate_fix(
        self,
        issue_title: str,
        issue_desc: str,
        file_tree: List[str],
        relevant_files: Dict[str, str],
        contribution_rules: str,
        workspace_path: str
    ) -> Dict[str, Any]:
        logger.info(f"Invoking Aider Coding Agent in workspace: {workspace_path}")
        try:
            # aider --message "fix description" --yes
            cmd = ["aider", "--message", f"Fix issue: {issue_title}\nDescription: {issue_desc}", "--yes"]
            env = os.environ.copy()
            if self.api_key:
                env["OPENAI_API_KEY"] = self.api_key
                
            res = subprocess.run(cmd, cwd=workspace_path, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=200.0)
            if res.returncode == 0:
                logger.info("Aider executed successfully.")
                return {"explanation": "Applied changes via Aider CLI.", "changes": []}
        except Exception as e:
            logger.warning(f"Aider CLI execution skipped/failed: {e}")

        fallback_agent = GeminiCodingAgent(api_key=settings.GEMINI_API_KEY)
        return fallback_agent.generate_fix(
            issue_title=issue_title,
            issue_desc=issue_desc,
            file_tree=file_tree,
            relevant_files=relevant_files,
            contribution_rules=contribution_rules,
            workspace_path=workspace_path
        )


class GeminiCodingAgent(BaseCodingAgent):
    """Standard Gemini model based agent."""
    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate_fix(
        self,
        issue_title: str,
        issue_desc: str,
        file_tree: List[str],
        relevant_files: Dict[str, str],
        contribution_rules: str,
        workspace_path: str
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Gemini API key is not configured.")

        # Prepare codebase context string
        files_context = ""
        for path, content in relevant_files.items():
            files_context += f"\n--- FILE: {path} ---\n{content}\n"

        prompt = f"""You are an expert AI software engineer. You are tasked with resolving a codebase issue.

=== ISSUE TITLE ===
{issue_title}

=== ISSUE DESCRIPTION ===
{issue_desc}

=== CONTRIBUTING GUIDELINES ===
{contribution_rules}

=== CODEBASE FILE STRUCTURE ===
{chr(10).join(file_tree[:150])}

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

        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }

        logger.info("Calling Gemini API for fallback code generation...")
        try:
            response = httpx.post(url, json=payload, timeout=90.0)
            if response.status_code != 200:
                raise Exception(f"Gemini API call failed: {response.text}")
                
            resp_data = response.json()
            response_text = resp_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            
            if response_text.startswith("```"):
                lines = response_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines[-1].startswith("```"):
                    lines = lines[:-1]
                response_text = "\n".join(lines).strip()
                
            return json.loads(response_text)
        except Exception as e:
            logger.error(f"Gemini agent failed: {e}")
            raise e


class LocalLLMCodingAgent(BaseCodingAgent):
    """Local LLM provider (Ollama / OpenAI compatible endpoint)."""
    def __init__(self, base_url: str = "http://localhost:11434/v1", model_name: str = "llama3"):
        self.base_url = base_url
        self.model_name = model_name

    def generate_fix(
        self,
        issue_title: str,
        issue_desc: str,
        file_tree: List[str],
        relevant_files: Dict[str, str],
        contribution_rules: str,
        workspace_path: str
    ) -> Dict[str, Any]:
        logger.info(f"Calling Local LLM endpoint: {self.base_url} (model: {self.model_name})")
        # Prepare codebase context string
        files_context = ""
        for path, content in relevant_files.items():
            files_context += f"\n--- FILE: {path} ---\n{content}\n"

        prompt = f"Fix issue: {issue_title}\nContext:\n{files_context}\nReturn JSON with 'explanation' and 'changes'."
        
        try:
            url = f"{self.base_url}/chat/completions"
            payload = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}
            }
            response = httpx.post(url, json=payload, timeout=90.0)
            if response.status_code == 200:
                resp_data = response.json()
                content_text = resp_data["choices"][0]["message"]["content"]
                return json.loads(content_text)
        except Exception as e:
            logger.error(f"Local LLM call failed: {e}")
            
        fallback = GeminiCodingAgent(api_key=settings.GEMINI_API_KEY)
        return fallback.generate_fix(issue_title, issue_desc, file_tree, relevant_files, contribution_rules, workspace_path)


class MockCodingAgent(BaseCodingAgent):
    """Safe dry-run / mock coder fallback for local testing."""
    def generate_fix(
        self,
        issue_title: str,
        issue_desc: str,
        file_tree: List[str],
        relevant_files: Dict[str, str],
        contribution_rules: str,
        workspace_path: str
    ) -> Dict[str, Any]:
        logger.info("[Mock Mode] Generating simulated code changes...")
        changes = []
        explanation = "Simulated code fix applied."
        
        target_file = None
        for path in relevant_files.keys():
            if "security.py" in path or "auth.py" in path or "main.py" in path:
                target_file = path
                break
                
        if target_file and "security.py" in target_file:
            explanation = "Modified verify_access_token in security module to safely handle empty tokens."
            original_content = relevant_files[target_file]
            if "def verify_access_token" in original_content:
                updated_content = original_content.replace(
                    "def verify_access_token(token: str) -> Optional[str]:",
                    "def verify_access_token(token: str) -> Optional[str]:\n    # Safety check added by AI Agent\n    if not token or not token.strip():\n        return None"
                )
                changes.append({
                    "filepath": target_file,
                    "content": updated_content
                })
        else:
            changes.append({
                "filepath": "scratch/mock_fix.py",
                "content": "# Simulated fix file created by AI Agent\ndef resolve_issue():\n    print('Issue resolved successfully')\n"
            })
            
        return {
            "explanation": explanation,
            "changes": changes
        }


def get_coding_agent(provider_name: str, api_key: Optional[str] = None) -> BaseCodingAgent:
    """Factory function retrieving selected LLM coding provider agent."""
    p_name = provider_name.lower()
    
    if p_name == "jules":
        return JulesCodingAgent(api_key=api_key)
    elif p_name == "openhands":
        return OpenHandsCodingAgent(
            api_key=api_key or settings.OPENHANDS_API_KEY,
            base_url=settings.OPENHANDS_BASE_URL
        )
    elif p_name == "claudecode":
        return ClaudeCodeCodingAgent(api_key=api_key)
    elif p_name == "aider":
        return AiderCodingAgent(api_key=api_key)
    elif p_name == "gemini":
        if api_key:
            return GeminiCodingAgent(api_key=api_key)
        return MockCodingAgent()
    elif p_name == "local":
        return LocalLLMCodingAgent()
        
    logger.info(f"Unknown or unconfigured provider '{provider_name}'. Defaulting to Jules.")
    return JulesCodingAgent(api_key=api_key)
