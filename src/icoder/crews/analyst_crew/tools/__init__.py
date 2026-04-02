import os

from crewai.tools import BaseTool
import ast
import glob
import pathlib


class FileNavigator:
    def __init__(self, root_directory):
        self.root_directory = root_directory
        self.files = []
        self.current_file_idx = -1
        self.file_count = -1
        
    def get_next_file(self):
        # Scan only on the first call for this specific instance
        if self.file_count == -1:
            self.files = glob.glob(f"{self.root_directory}/**/*.py", recursive=True)
            self.file_count = len(self.files)
            
        self.current_file_idx += 1
        
        if self.current_file_idx < self.file_count:
            return self.files[self.current_file_idx]
        return None  # Return None if no more files are left

class TestCaseExplorerTool(BaseTool):
    name: str = "test_case_explorer"
    description: str = ("Given a source file path, return the corresponding test file path. "
                        "Assume all test files are located in a /tests directory and mirror the source file structure. "
                        "For example, if the source file is src/module/file.py, the corresponding test file would be tests/module/test_file.py.")
    
    def _run(self, source_file_path: str) -> str:
        try:
            if not source_file_path.endswith(".py"):
                raise ValueError("Input must be a Python file path ending with .py")
            test_file_path = source_file_path.replace("src/", "tests/").replace(".py", "_test.py")
            if not os.path.exists(test_file_path):
                file_path = pathlib.Path(test_file_path)
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.touch()
            return test_file_path
        except Exception as e:
            raise e

class FileExplorerTool(BaseTool):
    name: str = "file_explorer_tool"
    description: str = ("Scans a root-directory for python source code files and" 
                        "returns one full filepath at a time. When the function"
                        "returns an empty string, consider that as end files and "
                        "do not call this tool anymore")        

    def _run(self, root_directory: str) -> str:
        try:
            file_explorer = getattr(self, "file_explorer")
            if file_explorer is None:
                file_explorer = FileNavigator(root_directory)
                setattr(self, "file_explorer", file_explorer)
            return file_explorer.get_next_file()
        except Exception as e:
            raise e

class CodeAnalyzerTool(BaseTool):
    name: str = "code_analyzer_tool"
    description: str = "Scans a Python file to identify functions and classes missing docstrings."

    def _run(self, file_path: str) -> str:
        try:
            with open(file_path, "r") as f:
                tree = ast.parse(f.read())
            
            missing_info = []
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        line_no = getattr(node, 'lineno', 'Unknown')
                        missing_info.append(f"{type(node).__name__}: '{node.name}' at line {line_no}")
            
            if not missing_info:
                return "No missing documentation found."
            return "Missing docstrings in:\n" + "\n".join(missing_info)
        except Exception as e:
            return f"Error parsing file: {str(e)}"
