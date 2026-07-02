import os
import ast
import re
import logging
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger(__name__)

# Regular expressions for JS/TS/JSX parsing
JS_IMPORT_RE = re.compile(r'import\s+(?:[^"\'\n]+|{[^}\n]+})\s+from\s+[\'"]([^\'"]+)[\'"]')
JS_REQUIRE_RE = re.compile(r'(?:const|let|var)\s+(?:[a-zA-Z0-9_$]+|{[^}\n]+})\s*=\s*require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)')
JS_EXPORT_RE = re.compile(r'export\s+(?:default\s+)?(?:async\s+)?(?:function|class|interface)\s+([a-zA-Z0-9_$]+)')
JS_ARROW_FN_RE = re.compile(r'(?:const|let|var)\s+([a-zA-Z0-9_$]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>')
JS_EXPRESS_ROUTE_RE = re.compile(r'(?:app|router|route)\.(get|post|put|delete|patch|use)\s*\(\s*[\'"]([^\'"]+)[\'"]')
JS_CLASS_RE = re.compile(r'\bclass\s+([a-zA-Z0-9_$]+)')
JS_FUNC_RE = re.compile(r'\b(?:async\s+)?function\s+([a-zA-Z0-9_$]+)\s*\(')

# Regular expressions for Go
GO_IMPORT_RE = re.compile(r'import\s+(?:\(\s*(?:[\'"][^\'"]+[\'"]\s*)*\)|[\'"]([^\'"]+)[\'"])')
GO_FUNC_RE = re.compile(r'^func\s+(?:\([^)]+\)\s+)?([a-zA-Z0-9_]+)\s*\(')
GO_ROUTE_RE = re.compile(r'\.(?:HandleFunc|Handle|GET|POST|PUT|DELETE|PATCH)\s*\(\s*[\'"]([^\'"]+)[\'"]')

# Regular expressions for Java
JAVA_IMPORT_RE = re.compile(r'import\s+([a-zA-Z0-9_.]+);')
JAVA_CLASS_RE = re.compile(r'(?:public\s+)?(?:class|interface)\s+([a-zA-Z0-9_]+)')
JAVA_METHOD_RE = re.compile(r'(?:public|protected|private|static|\s)+[a-zA-Z0-9_<>]+\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{')
JAVA_ROUTE_RE = re.compile(r'@(?:GetMapping|PostMapping|PutMapping|DeleteMapping|RequestMapping)\s*\(\s*(?:value\s*=\s*)?[\'"]([^\'"]+)[\'"]')

# Caller-Callee regex resolver (supports Python, JS/TS, Java, Go)
CALL_RE = re.compile(r'\b(?!(?:if|for|while|switch|catch|return|function|class|interface|import|require|var|const|let|new|throw|default|package|func|public|private|protected|static|void)\b)([a-zA-Z0-9_$]+)\s*[(]')

def find_matching_brace_end_line(lines: List[str], start_line_idx: int) -> int:
    """
    Finds the line index where the brace block starting at or after start_line_idx balances out.
    Uses comment and literal stripping to ensure high accuracy.
    """
    brace_count = 0
    started = False
    for i in range(start_line_idx, len(lines)):
        line = lines[i]
        # Strip string literals
        line_clean = re.sub(r'"[^"\\]*(?:\\.[^"\\]*)*"', '', line)
        line_clean = re.sub(r"'[^'\\]*(?:\\.[^'\\]*)*'", '', line_clean)
        # Strip comments
        line_clean = re.sub(r'//.*', '', line_clean)
        line_clean = re.sub(r'/\*.*?\*/', '', line_clean)
        
        for char in line_clean:
            if char == '{':
                brace_count += 1
                started = True
            elif char == '}':
                brace_count -= 1
                if started and brace_count <= 0:
                    return i + 1  # 1-indexed
    return len(lines)

class ASTParser:
    @staticmethod
    def parse_file(filepath: str, content: str) -> Dict[str, Any]:
        """
        Parses source code files, returning a dictionary containing:
        - symbols: List[Dict] (name, type, start_line, end_line)
        - imports: List[str] (imported dependencies)
        - routes: List[Dict] (method, path)
        - calls: List[Dict] (caller, callee)
        """
        ext = os.path.splitext(filepath)[1].lower()
        
        if ext == ".py":
            return ASTParser._parse_python(filepath, content)
        elif ext in [".js", ".ts", ".jsx", ".tsx"]:
            return ASTParser._parse_javascript_typescript(filepath, content)
        elif ext == ".go":
            return ASTParser._parse_go(filepath, content)
        elif ext == ".java":
            return ASTParser._parse_java(filepath, content)
        else:
            return ASTParser._parse_generic_regex(filepath, content)

    @staticmethod
    def _parse_python(filepath: str, content: str) -> Dict[str, Any]:
        result = {
            "symbols": [],
            "imports": [],
            "routes": [],
            "calls": []
        }
        lines = content.splitlines()
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                # Class extraction
                if isinstance(node, ast.ClassDef):
                    # Resolve inheritance
                    inheritance = [ast.unparse(b) for b in node.bases] if hasattr(ast, "unparse") else []
                    result["symbols"].append({
                        "name": node.name,
                        "type": "class",
                        "start_line": node.lineno,
                        "end_line": getattr(node, "end_lineno", len(lines)),
                        "inheritance": inheritance
                    })
                
                # Function/Method extraction
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    sym_type = "function"
                    
                    # Detect if route/API handler
                    is_route = False
                    route_path = None
                    route_method = "GET"
                    
                    for decorator in node.decorator_list:
                        dec_str = ast.unparse(decorator) if hasattr(ast, "unparse") else ""
                        route_match = re.search(r'\.(get|post|put|delete|route|patch)\s*\(\s*[\'"]([^\'"]+)[\'"]', dec_str)
                        if route_match:
                            is_route = True
                            route_method = route_match.group(1).upper()
                            route_path = route_match.group(2)
                            break
                    
                    if is_route and route_path:
                        result["routes"].append({
                            "method": route_method,
                            "path": route_path,
                            "symbol_name": node.name
                        })
                        sym_type = "api_handler"
                        
                    result["symbols"].append({
                        "name": node.name,
                        "type": sym_type,
                        "start_line": node.lineno,
                        "end_line": getattr(node, "end_lineno", len(lines))
                    })
                    
                    # Extract calls inside function Def
                    caller_name = node.name
                    for subnode in ast.walk(node):
                        if isinstance(subnode, ast.Call):
                            callee = None
                            if isinstance(subnode.func, ast.Name):
                                callee = subnode.func.id
                            elif isinstance(subnode.func, ast.Attribute):
                                callee = subnode.func.attr
                            if callee and callee != caller_name:
                                result["calls"].append({"caller": caller_name, "callee": callee})

                # Imports extraction
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        result["imports"].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        result["imports"].append(node.module)

            return result
        except SyntaxError:
            logger.warning(f"Syntax error parsing Python file AST: {filepath}. Falling back to regex.")
            return ASTParser._parse_generic_regex(filepath, content)

    @staticmethod
    def _parse_javascript_typescript(filepath: str, content: str) -> Dict[str, Any]:
        result = {
            "symbols": [],
            "imports": [],
            "routes": [],
            "calls": []
        }
        lines = content.splitlines()
        
        # Parse imports
        for line in lines:
            line_strip = line.strip()
            if not line_strip:
                continue
                
            imp_match = JS_IMPORT_RE.search(line_strip)
            if imp_match:
                result["imports"].append(imp_match.group(1))
                continue
            req_match = JS_REQUIRE_RE.search(line_strip)
            if req_match:
                result["imports"].append(req_match.group(1))
                continue
                
            route_match = JS_EXPRESS_ROUTE_RE.search(line_strip)
            if route_match:
                result["routes"].append({
                    "method": route_match.group(1).upper(),
                    "path": route_match.group(2)
                })

        # Parse Symbols (Classes, Functions, Interfaces)
        for idx, line in enumerate(lines, 1):
            line_strip = line.strip()
            if not line_strip:
                continue
                
            # Exported classes/functions
            exp_match = JS_EXPORT_RE.search(line_strip)
            if exp_match:
                sym_type = "function"
                if "class" in line_strip:
                    sym_type = "class"
                elif "interface" in line_strip:
                    sym_type = "interface"
                    
                end_line = find_matching_brace_end_line(lines, idx - 1)
                result["symbols"].append({
                    "name": exp_match.group(1),
                    "type": sym_type,
                    "start_line": idx,
                    "end_line": end_line
                })
                continue
                
            # Class match
            class_match = JS_CLASS_RE.search(line_strip)
            if class_match:
                end_line = find_matching_brace_end_line(lines, idx - 1)
                result["symbols"].append({
                    "name": class_match.group(1),
                    "type": "class",
                    "start_line": idx,
                    "end_line": end_line
                })
                continue
                
            # Function match
            func_match = JS_FUNC_RE.search(line_strip)
            if func_match:
                end_line = find_matching_brace_end_line(lines, idx - 1)
                result["symbols"].append({
                    "name": func_match.group(1),
                    "type": "function",
                    "start_line": idx,
                    "end_line": end_line
                })
                continue
                
            # Arrow functions / constants
            arr_match = JS_ARROW_FN_RE.search(line_strip)
            if arr_match:
                end_line = find_matching_brace_end_line(lines, idx - 1)
                result["symbols"].append({
                    "name": arr_match.group(1),
                    "type": "function",
                    "start_line": idx,
                    "end_line": end_line
                })

        # Trace caller-callee inside each function body
        for sym in result["symbols"]:
            if sym["type"] in ["function", "method", "api_handler"]:
                body_lines = lines[sym["start_line"] - 1 : sym["end_line"]]
                body_text = "\n".join(body_lines)
                for callee in CALL_RE.findall(body_text):
                    if callee != sym["name"]:
                        result["calls"].append({"caller": sym["name"], "callee": callee})

        return result

    @staticmethod
    def _parse_go(filepath: str, content: str) -> Dict[str, Any]:
        result = {
            "symbols": [],
            "imports": [],
            "routes": [],
            "calls": []
        }
        lines = content.splitlines()
        
        in_import_block = False
        for line in lines:
            line_strip = line.strip()
            if line_strip == "import (":
                in_import_block = True
                continue
            elif in_import_block and line_strip == ")":
                in_import_block = False
                continue
                
            if in_import_block:
                m = re.search(r'[\'"]([^\'"]+)[\'"]', line_strip)
                if m:
                    result["imports"].append(m.group(1))
            else:
                m = GO_IMPORT_RE.search(line_strip)
                if m and m.group(1):
                    result["imports"].append(m.group(1))
                    
            route_match = GO_ROUTE_RE.search(line_strip)
            if route_match:
                result["routes"].append({
                    "method": "ANY",
                    "path": route_match.group(1)
                })

        # Parse functions with brace matching
        for idx, line in enumerate(lines, 1):
            line_strip = line.strip()
            go_match = GO_FUNC_RE.search(line_strip)
            if go_match:
                end_line = find_matching_brace_end_line(lines, idx - 1)
                result["symbols"].append({
                    "name": go_match.group(1),
                    "type": "function",
                    "start_line": idx,
                    "end_line": end_line
                })

        # Trace caller-callee inside each function body
        for sym in result["symbols"]:
            body_lines = lines[sym["start_line"] - 1 : sym["end_line"]]
            body_text = "\n".join(body_lines)
            for callee in CALL_RE.findall(body_text):
                if callee != sym["name"]:
                    result["calls"].append({"caller": sym["name"], "callee": callee})

        return result

    @staticmethod
    def _parse_java(filepath: str, content: str) -> Dict[str, Any]:
        result = {
            "symbols": [],
            "imports": [],
            "routes": [],
            "calls": []
        }
        lines = content.splitlines()
        
        for idx, line in enumerate(lines, 1):
            line_strip = line.strip()
            if not line_strip:
                continue
                
            # Imports
            imp_match = JAVA_IMPORT_RE.search(line_strip)
            if imp_match:
                result["imports"].append(imp_match.group(1))
                continue
                
            # Routes
            route_match = JAVA_ROUTE_RE.search(line_strip)
            if route_match:
                result["routes"].append({
                    "method": "ANY",
                    "path": route_match.group(1)
                })
                
            # Classes
            class_match = JAVA_CLASS_RE.search(line_strip)
            if class_match:
                sym_type = "class"
                if "interface" in line_strip:
                    sym_type = "interface"
                end_line = find_matching_brace_end_line(lines, idx - 1)
                result["symbols"].append({
                    "name": class_match.group(1),
                    "type": sym_type,
                    "start_line": idx,
                    "end_line": end_line
                })
                continue
                
            # Methods
            m_match = JAVA_METHOD_RE.search(line_strip)
            if m_match:
                end_line = find_matching_brace_end_line(lines, idx - 1)
                result["symbols"].append({
                    "name": m_match.group(1),
                    "type": "method",
                    "start_line": idx,
                    "end_line": end_line
                })

        # Trace caller-callee inside each function body
        for sym in result["symbols"]:
            if sym["type"] in ["function", "method", "api_handler"]:
                body_lines = lines[sym["start_line"] - 1 : sym["end_line"]]
                body_text = "\n".join(body_lines)
                for callee in CALL_RE.findall(body_text):
                    if callee != sym["name"]:
                        result["calls"].append({"caller": sym["name"], "callee": callee})

        return result

    @staticmethod
    def _parse_generic_regex(filepath: str, content: str) -> Dict[str, Any]:
        """Simple generic regex parser for other code languages."""
        result = {
            "symbols": [],
            "imports": [],
            "routes": [],
            "calls": []
        }
        lines = content.splitlines()
        for idx, line in enumerate(lines, 1):
            line_strip = line.strip()
            # Look for function keywords
            fn_match = re.search(r'(?:def|fn|function|func)\s+([a-zA-Z0-9_]+)\s*[(]', line_strip)
            if fn_match:
                end_line = find_matching_brace_end_line(lines, idx - 1)
                result["symbols"].append({
                    "name": fn_match.group(1),
                    "type": "function",
                    "start_line": idx,
                    "end_line": end_line
                })
            # Look for classes
            class_match = re.search(r'class\s+([a-zA-Z0-9_]+)', line_strip)
            if class_match:
                end_line = find_matching_brace_end_line(lines, idx - 1)
                result["symbols"].append({
                    "name": class_match.group(1),
                    "type": "class",
                    "start_line": idx,
                    "end_line": end_line
                })
        return result

