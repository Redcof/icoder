import ast
import os
from dataclasses import dataclass, field
from typing import Optional

from icoder.utils import FileNavigator


@dataclass
class ItemInfo:
    name: str
    file_path: str
    lineno: int
    source: str
    indentation: str
    has_docstring: bool
    is_async: bool
    decorators: list[str]
    class_name: Optional[str] = None  # set if method inside a class


@dataclass
class ScanResult:
    missing_docstrings: list[ItemInfo] = field(default_factory=list)
    missing_tests: list[ItemInfo] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)


def has_docstring(node) -> bool:
    return (
        isinstance(node.body[0], ast.Expr)
        and isinstance(node.body[0].value, ast.Constant)
        and isinstance(node.body[0].value.value, str)
    ) if node.body else False


def extract_source(file_source: str, node: ast.AST) -> str:
    lines = file_source.splitlines()
    return "\n".join(lines[node.lineno - 1: node.end_lineno])


def calculate_indentation(source_code: str):
    # we can calculate the indentation from the first line
    first_line = source_code.split('\n')[1]
    # identify the indentation char
    is_using_tab = first_line[0] == '\t'
    search_char = ' '
    if is_using_tab:
        search_char = '\t'
    # Subtract the length of the string without leading spaces/tabs
    # from the original length
    leading_whitespace = len(first_line) - len(first_line.lstrip(search_char))
    return search_char * leading_whitespace


def scan_file(file_path: str, skip_private: bool = False, skip_dunder: bool = True) -> list[ItemInfo]:
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
        scanned_items = []  # (node, type, parent-class-name)
        print(type(node))
        if isinstance(node, ast.ClassDef):
            parent_class = node
            scanned_items.append((node, "CLASS", None))
            for child_item in node.body:
                if isinstance(child_item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    scanned_items.append((child_item, "FUNCTION", parent_class.name))
                if isinstance(child_item, ast.ClassDef):
                    scanned_items.append((child_item, "CLASS", parent_class.name))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # top-level only (not inside a class, handled above)
            scanned_items.append((node, "FUNCTION", None))
        
        for item, type_, parent_class_name in scanned_items:
            name = item.name
            if type_ == "FUNCTION":
                if skip_dunder and name.startswith("__") and name.endswith("__"):
                    continue
                if skip_private and name.startswith("_") and not name.startswith("__"):
                    continue
            elif type_ == "CLASS":
                continue  # TODO enable class handling
            source_code = extract_source(source, item)
            decorators = [ast.unparse(d) for d in item.decorator_list]
            results.append(ItemInfo(
                name=name,
                file_path=file_path,
                lineno=item.lineno,
                source=source_code,
                indentation=calculate_indentation(source_code),
                has_docstring=has_docstring(item),
                is_async=isinstance(item, ast.AsyncFunctionDef),
                decorators=decorators,
                class_name=parent_class_name,
            ))
    
    return results


def scan_project(root: str, test_dir_name: str, skip_private=False, skip_dunder=True) -> ScanResult:
    result = ScanResult()
    file_explorer = FileNavigator(root, skip_test_dir=test_dir_name).stream_files()
    for fpath in file_explorer:
        infos = scan_file(fpath, skip_private, skip_dunder)
        for info in infos:
            if not info.has_docstring:
                result.missing_docstrings.append(info)
    return result


def find_untested_functions(scan_result: ScanResult, test_dir: str) -> list[ItemInfo]:
    """Find functions that have no corresponding test in test_dir."""
    tested_names = set()
    file_explorer = FileNavigator(test_dir).stream_files()
    for fpath in file_explorer:
        fname = os.path.basename(fpath)
        if not fname.startswith("test_"):
            continue
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
