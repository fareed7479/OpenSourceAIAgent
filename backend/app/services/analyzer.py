import os
import json
import logging
import re
from typing import Dict, Any, List, Tuple

logger = logging.getLogger(__name__)

def get_directory_structure(clone_path: str, max_depth: int = 3) -> Dict[str, Any]:
    """Generates a nested tree representing the directory structure of the repository."""
    exclude_dirs = {".git", "node_modules", "venv", ".venv", "build", "target", "dist", "__pycache__", ".gemini"}
    
    def walk_tree(current_path: str, depth: int) -> Dict[str, Any]:
        node_name = os.path.basename(current_path) or "root"
        node = {"name": node_name, "type": "directory", "children": []}
        if depth > max_depth:
            return node
            
        try:
            for item in os.listdir(current_path):
                if item in exclude_dirs:
                    continue
                item_path = os.path.join(current_path, item)
                if os.path.isdir(item_path):
                    node["children"].append(walk_tree(item_path, depth + 1))
                else:
                    node["children"].append({"name": item, "type": "file"})
        except Exception:
            pass
        return node
        
    return walk_tree(clone_path, 1)

def detect_architecture(clone_path: str) -> Dict[str, Any]:
    """
    Scans directory hierarchy and filenames to infer repository architecture
    and maps file paths to components (controllers, services, models, etc.).
    """
    components = {
        "controllers": [],
        "services": [],
        "repositories": [],
        "models": [],
        "utilities": [],
        "middlewares": []
    }
    
    all_dirs = set()
    all_files = []
    
    exclude_dirs = {".git", "node_modules", "venv", ".venv", "build", "target", "dist", "__pycache__", ".gemini"}
    
    for root, dirs, files in os.walk(clone_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for d in dirs:
            all_dirs.add(d.lower())
        for f in files:
            rel_path = os.path.relpath(os.path.join(root, f), clone_path)
            all_files.append(rel_path)
            
            # Map file to components based on path & name keywords
            path_lower = rel_path.lower()
            if any(k in path_lower for k in ["controller", "router", "route", "api/"]):
                components["controllers"].append(rel_path)
            elif any(k in path_lower for k in ["service", "handler", "manager", "logic"]):
                components["services"].append(rel_path)
            elif any(k in path_lower for k in ["repository", "dao", "query"]):
                components["repositories"].append(rel_path)
            elif any(k in path_lower for k in ["model", "entity", "schema", "db/"]):
                components["models"].append(rel_path)
            elif any(k in path_lower for k in ["util", "helper", "common", "tool"]):
                components["utilities"].append(rel_path)
            elif any(k in path_lower for k in ["middleware", "auth", "guard", "intercept"]):
                components["middlewares"].append(rel_path)

    # Infer architecture pattern
    arch = "Monolithic Script / Simple Layout"
    
    if any(d in all_dirs for d in ["controllers", "views", "models"]):
        arch = "MVC (Model-View-Controller)"
    elif any(d in all_dirs for d in ["core", "infrastructure", "presentation", "domain"]):
        arch = "Clean / Hexagonal Architecture"
    elif any(d in all_dirs for d in ["adapters", "ports"]):
        arch = "Hexagonal Architecture (Ports & Adapters)"
    elif any(d in all_dirs for d in ["services", "apps"]) and len(components["controllers"]) > 10:
        arch = "Microservices / Monorepo Layout"
    elif len(components["services"]) > 0 and len(components["repositories"]) > 0:
        arch = "Layered Architecture"
    elif "frontend" in all_dirs and ("backend" in all_dirs or "api" in all_dirs):
        arch = "Client-Server Architecture"
        
    return {
        "pattern": arch,
        "components": components
    }

def analyze_repository(clone_path: str) -> Dict[str, Any]:
    """
    Analyze the files in a cloned repository and return details about
    the language, framework, build system, test commands, lint commands,
    and contribution guidelines.
    """
    result = {
        "language": "unknown",
        "framework": "unknown",
        "build_system": "unknown",
        "test_command": "",
        "lint_command": "",
        "contribution_rules": "",
        "meta_info": {}
    }

    if not clone_path or not os.path.exists(clone_path):
        logger.error(f"Clone path does not exist: {clone_path}")
        return result

    # 1. Detect Build System and Configuration Files
    files = os.listdir(clone_path)
    
    # Check package.json (Node/React/TS)
    if "package.json" in files:
        result["language"] = "TypeScript/JavaScript"
        result["build_system"] = "npm"
        try:
            with open(os.path.join(clone_path, "package.json"), "r", encoding="utf-8") as f:
                pkg_data = json.load(f)
                result["meta_info"]["package_name"] = pkg_data.get("name")
                result["meta_info"]["dependencies"] = list(pkg_data.get("dependencies", {}).keys())
                
                # Check scripts
                scripts = pkg_data.get("scripts", {})
                if "test" in scripts:
                    result["test_command"] = "npm test"
                else:
                    result["test_command"] = "npm run test"
                
                if "lint" in scripts:
                    result["lint_command"] = "npm run lint"
                
                # Detect framework (React, Next.js, Express, Vue, Angular, etc.)
                deps = pkg_data.get("dependencies", {})
                dev_deps = pkg_data.get("devDependencies", {})
                all_deps = {**deps, **dev_deps}
                if "next" in all_deps:
                    result["framework"] = "Next.js"
                elif "react" in all_deps:
                    result["framework"] = "React"
                elif "vue" in all_deps:
                    result["framework"] = "Vue"
                elif "@angular/core" in all_deps:
                    result["framework"] = "Angular"
                elif "express" in all_deps:
                    result["framework"] = "Express"
        except Exception as e:
            logger.error(f"Error parsing package.json: {e}")
            
    # Check Python configs
    elif "requirements.txt" in files or "pyproject.toml" in files or "setup.py" in files:
        result["language"] = "Python"
        result["build_system"] = "pip"
        result["test_command"] = "pytest"
        result["lint_command"] = "flake8"
        
        if "pyproject.toml" in files:
            result["build_system"] = "poetry"
            result["test_command"] = "poetry run pytest"
            result["lint_command"] = "poetry run black --check ."
            
        # Scan dependencies content to detect FastAPI, Django, Flask
        req_content = ""
        req_path = os.path.join(clone_path, "requirements.txt")
        pyproj_path = os.path.join(clone_path, "pyproject.toml")
        if os.path.exists(req_path):
            with open(req_path, "r", encoding="utf-8", errors="ignore") as f_req:
                req_content += f_req.read().lower()
        if os.path.exists(pyproj_path):
            with open(pyproj_path, "r", encoding="utf-8", errors="ignore") as f_py:
                req_content += f_py.read().lower()
                
        if "fastapi" in req_content:
            result["framework"] = "FastAPI"
        elif "django" in req_content:
            result["framework"] = "Django"
        elif "flask" in req_content:
            result["framework"] = "Flask"
            
    # Check Java Maven/Gradle
    elif "pom.xml" in files:
        result["language"] = "Java"
        result["build_system"] = "maven"
        result["test_command"] = "mvn test"
        result["lint_command"] = "mvn checkstyle:check"
        
        # Check Spring Boot dependency
        try:
            with open(os.path.join(clone_path, "pom.xml"), "r", encoding="utf-8", errors="ignore") as f_pom:
                pom_content = f_pom.read().lower()
                if "spring-boot" in pom_content or "springboot" in pom_content:
                    result["framework"] = "Spring Boot"
        except Exception:
            pass
        
    elif "build.gradle" in files or "build.gradle.kts" in files:
        result["language"] = "Java/Kotlin"
        result["build_system"] = "gradle"
        
        build_file = "build.gradle" if "build.gradle" in files else "build.gradle.kts"
        try:
            with open(os.path.join(clone_path, build_file), "r", encoding="utf-8", errors="ignore") as f_grad:
                grad_content = f_grad.read().lower()
                if "spring-boot" in grad_content or "springboot" in grad_content:
                    result["framework"] = "Spring Boot"
        except Exception:
            pass
            
        if os.path.exists(os.path.join(clone_path, "gradlew")):
            result["test_command"] = "./gradlew test"
            result["lint_command"] = "./gradlew check"
        else:
            result["test_command"] = "gradle test"
            result["lint_command"] = "gradle check"
            
    # Check Go
    elif "go.mod" in files:
        result["language"] = "Go"
        result["build_system"] = "go"
        result["test_command"] = "go test ./..."
        result["lint_command"] = "go vet ./..."

    # Check Rust
    elif "Cargo.toml" in files:
        result["language"] = "Rust"
        result["build_system"] = "cargo"
        result["test_command"] = "cargo test"
        result["lint_command"] = "cargo clippy"
        
    # Check PHP / Laravel
    elif "composer.json" in files:
        result["language"] = "PHP"
        result["build_system"] = "composer"
        try:
            with open(os.path.join(clone_path, "composer.json"), "r", encoding="utf-8") as f_comp:
                comp_data = json.load(f_comp)
                all_comp_deps = {**comp_data.get("require", {}), **comp_data.get("require-dev", {})}
                if "laravel/framework" in all_comp_deps or "laravel" in all_comp_deps:
                    result["framework"] = "Laravel"
        except Exception:
            pass
            
    # Check C# / ASP.NET
    else:
        csproj_files = [f for f in files if f.endswith(".csproj") or f.endswith(".sln")]
        if csproj_files:
            result["language"] = "C#"
            result["build_system"] = "dotnet"
            result["test_command"] = "dotnet test"
            result["lint_command"] = "dotnet format"
            try:
                with open(os.path.join(clone_path, csproj_files[0]), "r", encoding="utf-8", errors="ignore") as f_cs:
                    cs_content = f_cs.read().lower()
                    if "microsoft.aspnetcore" in cs_content or "aspnetcore" in cs_content:
                        result["framework"] = "ASP.NET"
            except Exception:
                pass

    # 2. Parse CONTRIBUTING.md or README.md for Contribution Rules
    contributing_file = None
    for name in files:
        if name.upper() in ["CONTRIBUTING.MD", "CONTRIBUTING", "CONTRIBUTING.TXT"]:
            contributing_file = name
            break
            
    if not contributing_file:
        for name in files:
            if name.upper() in ["README.MD", "README", "README.TXT"]:
                contributing_file = name
                break
                
    if contributing_file:
        try:
            filepath = os.path.join(clone_path, contributing_file)
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                # Store first 3000 characters of guidelines
                result["contribution_rules"] = content[:3000]
                result["meta_info"]["contribution_rules_source"] = contributing_file
        except Exception as e:
            logger.error(f"Error reading contribution guidelines: {e}")

    # 3. Detect workflows
    workflows_path = os.path.join(clone_path, ".github", "workflows")
    if os.path.exists(workflows_path) and os.path.isdir(workflows_path):
        try:
            result["meta_info"]["github_workflows"] = os.listdir(workflows_path)
            result["meta_info"]["cicd_configs"] = os.listdir(workflows_path)
        except Exception as e:
            logger.error(f"Error listing github workflows: {e}")

    # 4. Generate Directory Structure, Detect Architecture, Env/Lock files & Entry Points
    exclude_dirs = {".git", "node_modules", "venv", ".venv", "build", "target", "dist", "__pycache__", ".gemini"}
    
    # Lock files
    lock_files = []
    for lf in ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock", "go.sum", "composer.lock"]:
        if lf in files:
            lock_files.append(lf)
    result["meta_info"]["lock_files"] = lock_files
    
    # Env files
    env_files = []
    for ef in [".env", ".env.example", ".env.local", ".env.development", ".env.production"]:
        if ef in files:
            env_files.append(ef)
    result["meta_info"]["env_files"] = env_files

    # Entry points
    entry_points = []
    for root, dirs, fnames in os.walk(clone_path):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for fn in fnames:
            if fn in ["main.py", "app.py", "wsgi.py", "asgi.py", "index.js", "index.ts", "server.js", "server.ts", "app.js", "app.ts", "main.go", "Program.cs"]:
                entry_points.append(os.path.relpath(os.path.join(root, fn), clone_path))
    result["meta_info"]["entry_points"] = entry_points[:5]

    # Architecture components mapping
    arch_info = detect_architecture(clone_path)
    result["meta_info"]["architecture"] = arch_info["pattern"]
    result["meta_info"]["components"] = arch_info["components"]
    
    # Directory structure tree
    result["meta_info"]["directory_structure"] = get_directory_structure(clone_path)

    return result

