import libcst as cst
import os

class DocstringInserter(cst.CSTTransformer):
    def __init__(self, insertions: dict):
        # insertions = {func_name: docstring_text}
        self.insertions = insertions

    def leave_FunctionDef(self, original_node, updated_node):
        name = updated_node.name.value
        if name not in self.insertions:
            return updated_node
        # Check it truly has no docstring already
        body = updated_node.body
        if isinstance(body, cst.IndentedBlock):
            first = body.body[0]
            if isinstance(first, cst.SimpleStatementLine):
                if isinstance(first.body[0], cst.Expr):
                    if isinstance(first.body[0].value, (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString)):
                        return updated_node  # already has docstring, skip

        docstring_text = self.insertions[name]
        # TODO: calculate correct indentation for multi-line docstrings
        # indent = body.indent  # Default indentation, adjust as needed
        # docstring_text = docstring_text.replace("\n", "\n" + indent)
        docstring_node = cst.IndentedBlock(body=[cst.Expr(value=cst.SimpleString(f'"""{docstring_text}"""\n'))])
        new_body = body.with_changes(body=[docstring_node, *body.body])
        return updated_node.with_changes(body=new_body)

def write_docstrings(file_path: str, insertions: dict):
    with open(file_path, "r") as f:
        source = f.read()
    tree = cst.parse_module(source)
    new_tree = tree.visit(DocstringInserter(insertions))
    with open(file_path, "w") as f:
        f.write(new_tree.code)

def write_tests(source_file: str, test_codes: list, test_root: str):
    """Creates or appends to a test file mirroring the source path."""
    rel_path = os.path.relpath(source_file)
    test_file = os.path.join(test_root, "test_" + rel_path.replace(os.sep, "_"))
    
    mode = "a" if os.path.exists(test_file) else "w"
    with open(test_file, mode) as f:
        if mode == "w":
            f.write("import pytest\n\n")
        for code in test_codes:
            f.write("\n\n" + code.strip())
