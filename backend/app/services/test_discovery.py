import os
import re
import logging
from typing import List, Set

logger = logging.getLogger(__name__)

class TestDiscoveryManager:
    @staticmethod
    def get_all_test_files(repo_path: str) -> List[str]:
        """Scans the repository and returns a list of all identified test files."""
        test_files = []
        exclude_dirs = {".git", "node_modules", "venv", ".venv", "build", "target", "dist", "__pycache__"}
        
        # Test file patterns
        test_patterns = [
            r'test_.*\.py$', r'.*_test\.py$',
            r'.*\.test\.(?:js|ts|jsx|tsx)$', r'.*\.spec\.(?:js|ts|jsx|tsx)$',
            r'.*Test\.java$', r'.*Tests\.java$',
            r'.*_test\.go$',
            r'test_.*'
        ]
        regexes = [re.compile(p, re.IGNORECASE) for p in test_patterns]
        
        for root, dirs, files in os.walk(repo_path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            
            # Check if directory itself is a test folder
            is_test_dir = "test" in os.path.basename(root).lower() or "tests" in os.path.basename(root).lower() or "__tests__" in os.path.basename(root)
            
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), repo_path)
                
                # If inside test directory, it's likely a test file
                if is_test_dir:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in [".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".java", ".rs"]:
                        test_files.append(rel_path)
                        continue
                
                # Check regex matching
                for reg in regexes:
                    if reg.match(file):
                        test_files.append(rel_path)
                        break
                        
        return test_files

    @staticmethod
    def discover_related_tests(repo_path: str, source_files: List[str]) -> List[str]:
        """
        Maps a list of source files to their most relevant test files based on
        name similarities, paths, and patterns.
        """
        if not source_files:
            return []
            
        all_tests = TestDiscoveryManager.get_all_test_files(repo_path)
        if not all_tests:
            return []
            
        matched_tests = set()
        
        for src in source_files:
            src_base = os.path.splitext(os.path.basename(src))[0]
            # Strip prefixes/suffixes like _service, _controller, etc.
            src_clean = re.sub(r'(_service|_controller|_model|_helper|_util|_view)$', '', src_base)
            
            for test in all_tests:
                test_base = os.path.splitext(os.path.basename(test))[0]
                # Check direct matching
                if src_base.lower() in test_base.lower() or src_clean.lower() in test_base.lower():
                    matched_tests.add(test)
                # Check if test file is in same directory hierarchy
                elif os.path.dirname(src) and os.path.dirname(src) in os.path.dirname(test):
                    # Only add if it's general test for directory
                    if "index" in test_base or "main" in test_base or "test" == test_base:
                        matched_tests.add(test)
                        
        # If no specific matches, return default entry-point tests
        if not matched_tests and all_tests:
            for test in all_tests:
                test_base = os.path.splitext(os.path.basename(test))[0]
                if any(x in test_base.lower() for x in ["main", "app", "index", "test"]):
                    matched_tests.add(test)
                    
        return list(matched_tests)[:5]  # Limit to top 5 related tests
