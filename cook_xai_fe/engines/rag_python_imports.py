import ast

class RAGEngine:
    def extract_dependencies(self, raw_code: str, tree: ast.AST = None) -> list:
        """
        Parses Python code to find imported modules.
        Accepts an optional pre-parsed AST tree to avoid double-parsing.
        """
        dependencies = []
        try:
            if tree is None:
                tree = ast.parse(raw_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependencies.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        dependencies.append(node.module)
        except SyntaxError:
            pass
        return dependencies

rag_engine = RAGEngine()