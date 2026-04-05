import ast
import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class FunctionInfo:
    name: str
    file_path: str
    lineno: int
    source: str
    has_docstring: bool
    is_async: bool
    decorators: list[str]
    class_name: Optional[str] = None  # set if method inside a class

@dataclass
class ScanResult:
    missing_docstrings: list[FunctionInfo] = field(default_factory=list)
    missing_tests: list[FunctionInfo] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)

def has_docstring(node) -> bool:
    return (
        isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ) if node.body else False

def extract_source(file_source: str, node: ast.AST) -> str:
    lines = file_source.splitlines()
    return "\n".join(lines[node.lineno - 1 : node.end_lineno])

def scan_file(file_path: str, skip_private: bool = False, skip_dunder: bool = True) -> list[FunctionInfo]:
    results = []
    try:
        with open(file_path, "r") as f:
            source = f.read()
        tree = ast.parse(source)
    except SyntaxError:
        print(f"[SKIP] Syntax error in {file_path}")
        return []

    for node in ast.walk(tree):
        class_name = None
        functions = []

        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    functions.append((item, node.name))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # top-level only (not inside a class, handled above)
            functions.append((node, None))

        for func, cls_name in functions:
            name = func.name
            if skip_dunder and name.startswith("__") and name.endswith("__"):
                continue
            if skip_private and name.startswith("_") and not name.startswith("__"):
                continue

            decorators = [ast.unparse(d) for d in func.decorator_list]
            results.append(FunctionInfo(
                name=name,
                file_path=file_path,
                lineno=func.lineno,
                source=extract_source(source, func),
                has_docstring=has_docstring(func),
                is_async=isinstance(func, ast.AsyncFunctionDef),
                decorators=decorators,
                class_name=cls_name,
            ))

    return results

def scan_project(root: str, skip_private=False, skip_dunder=True) -> ScanResult:
    result = ScanResult()
    for dirpath, _, filenames in os.walk(root):
        for fname in filenames:
            # TODO ignore test files here, or handle them separately
            if fname.startswith("test_") and fname.endswith(".py"):
                continue
            if not fname.endswith(".py"):
                continue
            fpath = os.path.join(dirpath, fname)
            infos = scan_file(fpath, skip_private, skip_dunder)
            for info in infos:
                if not info.has_docstring:
                    result.missing_docstrings.append(info)
    return result

def find_untested_functions(scan_result: ScanResult, test_dir: str) -> list[FunctionInfo]:
    """Find functions that have no corresponding test in test_dir."""
    tested_names = set()
    for dirpath, _, filenames in os.walk(test_dir):
        for fname in filenames:
            if not fname.startswith("test_") or not fname.endswith(".py"):
                continue
            fpath = os.path.join(dirpath, fname)
            with open(fpath) as f:
                source = f.read()
            tree = ast.parse(source)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    # test_<name> convention
                    tested_names.add(node.name.replace("test_", ""))

    untested = []
    all_functions = scan_result.missing_docstrings  # reuse scan, or pass all functions
    for fn in all_functions:
        if fn.name not in tested_names:
            untested.append(fn)
    return untested
