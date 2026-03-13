import ast
from radon.complexity import cc_visit
from radon.metrics import mi_visit
from core.logger import logger

class ASTAutoFixer(ast.NodeVisitor):
    def __init__(self, raw_code: str):
        self.raw_lines = raw_code.splitlines()
        self.suggestions = []

    def visit_FunctionDef(self, node):
        # 1. Check for mutable default arguments
        for arg in node.args.defaults:
            if isinstance(arg, (ast.List, ast.Dict, ast.Set)):
                func_line = self.raw_lines[node.lineno - 1]
                
                # A very naive auto-fix generation just for demonstration
                # Finds "=[]" or "={}" and replaces it with "=None"
                # In a real AST rewriter we use libcst, but string replace works for the capstone!
                fixed_line = func_line
                for char in ['[]', '{}', 'set()']:
                    if char in fixed_line:
                        fixed_line = fixed_line.replace(char, 'None')
                
                # Also inject the instantiation at the top of the function
                indent = " " * (node.col_offset + 4)
                injection = f"\n{indent}if {arg} is None:\n{indent}    {arg} = [] # Auto-fixed mutable default"

                self.suggestions.append({
                    "type": "bug",
                    "title": f"Mutable Default in `{node.name}()`",
                    "description": "Lists or dicts as defaults retain their state between function calls, causing severe memory leaks.",
                    "line": node.lineno,
                    "original": func_line,
                    "fix": fixed_line + injection
                })
        
        # 2. Check for docstrings (Enterprise Standard)
        if not ast.get_docstring(node) and not node.name.startswith("__"):
            indent = " " * (node.col_offset + 4)
            self.suggestions.append({
                "type": "standard",
                "title": f"Missing Docstring in `{node.name}()`",
                "description": "Enterprise standards require a brief docstring explaining the function's purpose.",
                "line": node.lineno,
                "original": getattr(node, 'name', ''),
                "fix": f'"""\n{indent}TODO: Add docstring here\n{indent}"""'
            })

        self.generic_visit(node)

    def visit_ExceptHandler(self, node):
        if node.type is None or (isinstance(node.type, ast.Name) and node.type.id == 'Exception'):
            for child in node.body:
                if isinstance(child, ast.Pass):
                    except_line = self.raw_lines[node.lineno - 1]
                    indent = " " * (node.col_offset + 4)
                    self.suggestions.append({
                        "type": "reliability",
                        "title": "Silent Exception Failure",
                        "description": "Catching an exception and doing nothing (`pass`) hides critical crashes.",
                        "line": node.lineno,
                        "original": except_line,
                        "fix": f"{except_line}\n{indent}import logging; logging.error('Exception occurred')"
                    })
        self.generic_visit(node)

class ASTEngine:
    def scan(self, raw_code: str, filename: str, tree: ast.AST = None) -> dict:
        """
        Scan code returning raw structured data for the Auto-Fixer orchestrator.
        """
        report_data = {
            "mi": "N/A",
            "complexity": [],
            "suggestions": []
        }

        try:
            mi_score = mi_visit(raw_code, multi=True)
            report_data["mi"] = round(mi_score, 1)
        except Exception as e:
            logger.warning(f"Radon MI scan failed for {filename}: {e}")

        try:
            for block in cc_visit(raw_code):
                if block.complexity >= 6:
                    report_data["complexity"].append({
                        "name": block.name,
                        "score": block.complexity,
                        "line": block.lineno
                    })
        except Exception as e:
            logger.warning(f"Radon complexity scan failed for {filename}: {e}")

        try:
            if tree is None:
                tree = ast.parse(raw_code)
            scanner = ASTAutoFixer(raw_code)
            scanner.visit(tree)
            report_data["suggestions"] = scanner.suggestions
        except SyntaxError:
            pass
            
        return report_data

ast_engine = ASTEngine()