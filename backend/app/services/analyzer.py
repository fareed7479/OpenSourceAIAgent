import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

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
                # Store first 2000 characters of guidelines
                result["contribution_rules"] = content[:3000]
                result["meta_info"]["contribution_rules_source"] = contributing_file
        except Exception as e:
            logger.error(f"Error reading contribution guidelines: {e}")

    # 3. Detect workflows
    workflows_path = os.path.join(clone_path, ".github", "workflows")
    if os.path.exists(workflows_path) and os.path.isdir(workflows_path):
        try:
            result["meta_info"]["github_workflows"] = os.listdir(workflows_path)
        except Exception as e:
            logger.error(f"Error listing github workflows: {e}")

    return result
