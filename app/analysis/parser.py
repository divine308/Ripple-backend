import ast
import re
from pathlib import Path
from typing import Any

from app.analysis.languages import detect_language
from app.models.code import CodeEdge, CodeNode


# ============================================================
# GENERIC HELPERS
# ============================================================

def make_id(value: str) -> str:
    return (
        value
        .replace("\\", "/")
        .replace(" ", "_")
    )


def line_number(content: str, position: int) -> int:
    return content[:position].count("\n") + 1


def unique_relationships(
    relationships: list[tuple[str, str, str, float]],
) -> list[tuple[str, str, str, float]]:
    seen: set[tuple[str, str, str]] = set()
    result = []

    for source, target, edge_type, confidence in relationships:
        key = (source, target, edge_type)

        if key in seen:
            continue

        seen.add(key)
        result.append(
            (source, target, edge_type, confidence)
        )

    return result


# ============================================================
# IMPORT PATTERNS
# ============================================================

IMPORT_PATTERNS = {
    "JavaScript": [
        re.compile(
            r'import\s+(?:[\s\S]*?\s+from\s+)?["\']([^"\']+)["\']'
        ),
        re.compile(
            r'export\s+[\s\S]*?\s+from\s+["\']([^"\']+)["\']'
        ),
        re.compile(
            r'require\s*\(\s*["\']([^"\']+)["\']\s*\)'
        ),
    ],

    "JavaScript React": [
        re.compile(
            r'import\s+(?:[\s\S]*?\s+from\s+)?["\']([^"\']+)["\']'
        ),
        re.compile(
            r'export\s+[\s\S]*?\s+from\s+["\']([^"\']+)["\']'
        ),
        re.compile(
            r'require\s*\(\s*["\']([^"\']+)["\']\s*\)'
        ),
    ],

    "TypeScript": [
        re.compile(
            r'import\s+(?:[\s\S]*?\s+from\s+)?["\']([^"\']+)["\']'
        ),
        re.compile(
            r'export\s+[\s\S]*?\s+from\s+["\']([^"\']+)["\']'
        ),
        re.compile(
            r'require\s*\(\s*["\']([^"\']+)["\']\s*\)'
        ),
    ],

    "TypeScript React": [
        re.compile(
            r'import\s+(?:[\s\S]*?\s+from\s+)?["\']([^"\']+)["\']'
        ),
        re.compile(
            r'export\s+[\s\S]*?\s+from\s+["\']([^"\']+)["\']'
        ),
        re.compile(
            r'require\s*\(\s*["\']([^"\']+)["\']\s*\)'
        ),
    ],

    "Java": [
        re.compile(
            r'^\s*import\s+(?:static\s+)?([A-Za-z0-9_.*]+)\s*;',
            re.MULTILINE,
        ),
    ],

    "Go": [
        re.compile(
            r'"([^"]+)"'
        ),
    ],

    "Rust": [
        re.compile(
            r'^\s*use\s+([^;]+);',
            re.MULTILINE,
        ),
        re.compile(
            r'^\s*mod\s+([A-Za-z_][A-Za-z0-9_]*)\s*;',
            re.MULTILINE,
        ),
    ],

    "C#": [
        re.compile(
            r'^\s*using\s+(?:static\s+)?([A-Za-z0-9_.]+)\s*;',
            re.MULTILINE,
        ),
    ],

    "C++": [
        re.compile(
            r'^\s*#\s*include\s*[<"]([^>"]+)[>"]',
            re.MULTILINE,
        ),
    ],

    "C": [
        re.compile(
            r'^\s*#\s*include\s*[<"]([^>"]+)[>"]',
            re.MULTILINE,
        ),
    ],

    "C/C++ Header": [
        re.compile(
            r'^\s*#\s*include\s*[<"]([^>"]+)[>"]',
            re.MULTILINE,
        ),
    ],

    "C++ Header": [
        re.compile(
            r'^\s*#\s*include\s*[<"]([^>"]+)[>"]',
            re.MULTILINE,
        ),
    ],

    "PHP": [
        re.compile(
            r'^\s*(?:use|require|require_once|include|include_once)\s+["\']?([^;"\']+)',
            re.MULTILINE,
        ),
    ],

    "Ruby": [
        re.compile(
            r'^\s*(?:require|require_relative|load)\s+["\']([^"\']+)["\']',
            re.MULTILINE,
        ),
    ],

    "Swift": [
        re.compile(
            r'^\s*import\s+([A-Za-z0-9_.]+)',
            re.MULTILINE,
        ),
    ],

    "Kotlin": [
        re.compile(
            r'^\s*import\s+([A-Za-z0-9_.*]+)',
            re.MULTILINE,
        ),
    ],

    "Dart": [
        re.compile(
            r'^\s*import\s+["\']([^"\']+)["\']',
            re.MULTILINE,
        ),
        re.compile(
            r'^\s*export\s+["\']([^"\']+)["\']',
            re.MULTILINE,
        ),
    ],

    "Vue": [
        re.compile(
            r'import\s+(?:[\s\S]*?\s+from\s+)?["\']([^"\']+)["\']'
        ),
    ],

    "Svelte": [
        re.compile(
            r'import\s+(?:[\s\S]*?\s+from\s+)?["\']([^"\']+)["\']'
        ),
    ],
}


# ============================================================
# GENERIC SYMBOL PATTERNS
# ============================================================

FUNCTION_PATTERNS = {
    "JavaScript": [
        re.compile(
            r'\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\('
        ),
        re.compile(
            r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*'
            r'(?:async\s*)?\([^)]*\)\s*=>'
        ),
        re.compile(
            r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*'
            r'(?:async\s*)?[A-Za-z_$][\w$]*\s*=>'
        ),
    ],

    "JavaScript React": [
        re.compile(
            r'\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\('
        ),
        re.compile(
            r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*'
            r'(?:async\s*)?\([^)]*\)\s*=>'
        ),
    ],

    "TypeScript": [
        re.compile(
            r'\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\('
        ),
        re.compile(
            r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*'
            r'(?:async\s*)?\([^)]*\)\s*=>'
        ),
    ],

    "TypeScript React": [
        re.compile(
            r'\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\('
        ),
        re.compile(
            r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*'
            r'(?:async\s*)?\([^)]*\)\s*=>'
        ),
    ],

    "Java": [
        re.compile(
            r'\b(?:public|private|protected|static|final|synchronized|\s)+'
            r'[A-Za-z_$][\w$<>\[\], ?]*\s+'
            r'([A-Za-z_$][\w$]*)\s*\([^;{}]*\)\s*\{'
        ),
    ],

    "Go": [
        re.compile(
            r'\bfunc\s+(?:\([^)]*\)\s*)?'
            r'([A-Za-z_][\w]*)\s*\('
        ),
    ],

    "Rust": [
        re.compile(
            r'\bfn\s+([A-Za-z_][\w]*)\s*\('
        ),
    ],

    "C#": [
        re.compile(
            r'\b(?:public|private|protected|internal|static|async|virtual|override|sealed|\s)+'
            r'[A-Za-z_$][\w$<>\[\], ?]*\s+'
            r'([A-Za-z_$][\w$]*)\s*\([^;{}]*\)\s*\{'
        ),
    ],

    "C++": [
        re.compile(
            r'\b[A-Za-z_][\w:<>,*& ]*\s+'
            r'([A-Za-z_][\w]*)\s*\([^;{}]*\)\s*\{'
        ),
    ],

    "C": [
        re.compile(
            r'\b[A-Za-z_][\w *]*\s+'
            r'([A-Za-z_][\w]*)\s*\([^;{}]*\)\s*\{'
        ),
    ],

    "PHP": [
        re.compile(
            r'\bfunction\s+([A-Za-z_][\w]*)\s*\('
        ),
    ],

    "Ruby": [
        re.compile(
            r'^\s*def\s+([A-Za-z_][\w!?=]*)',
            re.MULTILINE,
        ),
    ],

    "Swift": [
        re.compile(
            r'\bfunc\s+([A-Za-z_][\w]*)\s*\('
        ),
    ],

    "Kotlin": [
        re.compile(
            r'\bfun\s+([A-Za-z_][\w]*)\s*\('
        ),
    ],

    "Dart": [
        re.compile(
            r'\b(?:Future<[^>]+>\s+|void\s+|[A-Za-z_][\w<>?]*\s+)?'
            r'([A-Za-z_][\w]*)\s*\([^;{}]*\)\s*\{'
        ),
    ],

    "Vue": [
        re.compile(
            r'\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\('
        ),
        re.compile(
            r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*'
            r'(?:async\s*)?\([^)]*\)\s*=>'
        ),
    ],

    "Svelte": [
        re.compile(
            r'\b(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\('
        ),
        re.compile(
            r'\b(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*'
            r'(?:async\s*)?\([^)]*\)\s*=>'
        ),
    ],
}


CLASS_PATTERNS = {
    "JavaScript": [
        re.compile(r'\bclass\s+([A-Za-z_$][\w$]*)')
    ],
    "JavaScript React": [
        re.compile(r'\bclass\s+([A-Za-z_$][\w$]*)')
    ],
    "TypeScript": [
        re.compile(r'\bclass\s+([A-Za-z_$][\w$]*)')
    ],
    "TypeScript React": [
        re.compile(r'\bclass\s+([A-Za-z_$][\w$]*)')
    ],
    "Java": [
        re.compile(r'\bclass\s+([A-Za-z_$][\w$]*)'),
        re.compile(r'\binterface\s+([A-Za-z_$][\w$]*)'),
        re.compile(r'\benum\s+([A-Za-z_$][\w$]*)'),
    ],
    "C#": [
        re.compile(r'\bclass\s+([A-Za-z_$][\w$]*)'),
        re.compile(r'\binterface\s+([A-Za-z_$][\w$]*)'),
        re.compile(r'\bstruct\s+([A-Za-z_$][\w$]*)'),
    ],
    "C++": [
        re.compile(r'\bclass\s+([A-Za-z_$][\w$]*)'),
        re.compile(r'\bstruct\s+([A-Za-z_$][\w$]*)'),
    ],
    "C": [
        re.compile(r'\bstruct\s+([A-Za-z_$][\w$]*)'),
    ],
    "PHP": [
        re.compile(r'\bclass\s+([A-Za-z_$][\w$]*)'),
        re.compile(r'\binterface\s+([A-Za-z_$][\w$]*)'),
        re.compile(r'\btrait\s+([A-Za-z_$][\w$]*)'),
    ],
    "Ruby": [
        re.compile(r'^\s*class\s+([A-Za-z_][\w:]*)', re.MULTILINE),
        re.compile(r'^\s*module\s+([A-Za-z_][\w:]*)', re.MULTILINE),
    ],
    "Swift": [
        re.compile(r'\bclass\s+([A-Za-z_][\w]*)'),
        re.compile(r'\bstruct\s+([A-Za-z_][\w]*)'),
        re.compile(r'\bprotocol\s+([A-Za-z_][\w]*)'),
    ],
    "Kotlin": [
        re.compile(r'\bclass\s+([A-Za-z_][\w]*)'),
        re.compile(r'\binterface\s+([A-Za-z_][\w]*)'),
        re.compile(r'\bobject\s+([A-Za-z_][\w]*)'),
    ],
    "Dart": [
        re.compile(r'\bclass\s+([A-Za-z_][\w]*)'),
        re.compile(r'\bmixin\s+([A-Za-z_][\w]*)'),
    ],
    "Go": [],
    "Rust": [
        re.compile(r'\bstruct\s+([A-Za-z_][\w]*)'),
        re.compile(r'\benum\s+([A-Za-z_][\w]*)'),
        re.compile(r'\btrait\s+([A-Za-z_][\w]*)'),
    ],
    "Vue": [],
    "Svelte": [],
}


# ============================================================
# PYTHON NODE PARSER
# ============================================================

def _qualified_name(
    relative_path: str,
    name: str,
    parent_class: str | None = None,
) -> str:
    symbol = (
        f"{parent_class}.{name}"
        if parent_class
        else name
    )

    return f"{relative_path}:{symbol}"


def _python_symbol_id(
    relative_path: str,
    line: int,
    name: str,
) -> str:
    return f"function:{relative_path}:{line}:{name}"


def _python_class_id(
    relative_path: str,
    line: int,
    name: str,
) -> str:
    return f"class:{relative_path}:{line}:{name}"


class _PythonNodeVisitor(ast.NodeVisitor):

    def __init__(self, relative_path: str):
        self.relative_path = relative_path
        self.nodes: list[CodeNode] = []
        self.edges: list[CodeEdge] = []
        self.scope_stack: list[tuple[str, str, str]] = []

    @property
    def file_id(self) -> str:
        return f"file:{self.relative_path}"

    @property
    def current_class(self) -> str | None:
        for kind, _, name in reversed(self.scope_stack):
            if kind == "class":
                return name

        return None

    @property
    def current_scope_id(self) -> str:
        if self.scope_stack:
            return self.scope_stack[-1][1]

        return self.file_id

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        node_id = _python_class_id(
            self.relative_path,
            node.lineno,
            node.name,
        )

        parent_class = self.current_class

        self.nodes.append(
            CodeNode(
                id=node_id,
                label=node.name,
                type="class",
                path=self.relative_path,
                line=node.lineno,
                language="Python",
                metadata={
                    "qualified_name": _qualified_name(
                        self.relative_path,
                        node.name,
                        parent_class,
                    ),
                    "parent_class": parent_class,
                    "scope": "class",
                    "is_public": not node.name.startswith("_"),
                },
            )
        )

        self.edges.append(
            CodeEdge(
                source=self.current_scope_id,
                target=node_id,
                type="contains",
            )
        )

        self.scope_stack.append(
            ("class", node_id, node.name)
        )

        for child in node.body:
            self.visit(child)

        self.scope_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._visit_function(node)

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> Any:
        self._visit_function(node)

    def _visit_function(self, node: ast.AST) -> None:
        name = getattr(node, "name")
        lineno = getattr(node, "lineno")

        node_id = _python_symbol_id(
            self.relative_path,
            lineno,
            name,
        )

        parent_class = self.current_class

        self.nodes.append(
            CodeNode(
                id=node_id,
                label=name,
                type="function",
                path=self.relative_path,
                line=lineno,
                language="Python",
                metadata={
                    "qualified_name": _qualified_name(
                        self.relative_path,
                        name,
                        parent_class,
                    ),
                    "parent_class": parent_class,
                    "scope": (
                        "method"
                        if parent_class
                        else "function"
                    ),
                    "is_public": not name.startswith("_"),
                },
            )
        )

        self.edges.append(
            CodeEdge(
                source=self.current_scope_id,
                target=node_id,
                type="contains",
            )
        )

        self.scope_stack.append(
            ("function", node_id, name)
        )

        for child in ast.iter_child_nodes(node):
            self.visit(child)

        self.scope_stack.pop()


def parse_python(
    path: Path,
    relative_path: str,
    content: str,
) -> tuple[list[CodeNode], list[CodeEdge]]:

    try:
        tree = ast.parse(
            content,
            filename=relative_path,
        )
    except SyntaxError:
        return [], []

    visitor = _PythonNodeVisitor(relative_path)

    for node in tree.body:
        visitor.visit(node)

    return visitor.nodes, visitor.edges


# ============================================================
# GENERIC NODE PARSER
# ============================================================

def parse_generic(
    path: Path,
    relative_path: str,
    content: str,
) -> tuple[list[CodeNode], list[CodeEdge]]:

    nodes: list[CodeNode] = []
    edges: list[CodeEdge] = []

    file_id = f"file:{relative_path}"
    language = detect_language(path)

    if not language:
        return nodes, edges

    seen: set[tuple[str, int, str]] = set()

    for pattern in FUNCTION_PATTERNS.get(language, []):
        for match in pattern.finditer(content):
            name = match.group(1)

            if not name:
                continue

            line = line_number(
                content,
                match.start(),
            )

            key = (
                "function",
                line,
                name,
            )

            if key in seen:
                continue

            seen.add(key)

            node_id = (
                f"function:{relative_path}:"
                f"{line}:{make_id(name)}"
            )

            nodes.append(
                CodeNode(
                    id=node_id,
                    label=name,
                    type="function",
                    path=relative_path,
                    line=line,
                    language=language,
                    metadata={
                        "qualified_name": (
                            f"{relative_path}:{name}"
                        ),
                        "scope": "function",
                        "is_public": not name.startswith("_"),
                    },
                )
            )

            edges.append(
                CodeEdge(
                    source=file_id,
                    target=node_id,
                    type="contains",
                )
            )

    for pattern in CLASS_PATTERNS.get(language, []):
        for match in pattern.finditer(content):
            name = match.group(1)

            if not name:
                continue

            line = line_number(
                content,
                match.start(),
            )

            key = (
                "class",
                line,
                name,
            )

            if key in seen:
                continue

            seen.add(key)

            node_id = (
                f"class:{relative_path}:"
                f"{line}:{make_id(name)}"
            )

            nodes.append(
                CodeNode(
                    id=node_id,
                    label=name,
                    type="class",
                    path=relative_path,
                    line=line,
                    language=language,
                    metadata={
                        "qualified_name": (
                            f"{relative_path}:{name}"
                        ),
                        "scope": "class",
                        "is_public": not name.startswith("_"),
                    },
                )
            )

            edges.append(
                CodeEdge(
                    source=file_id,
                    target=node_id,
                    type="contains",
                )
            )

    return nodes, edges


# ============================================================
# FILE PARSER
# ============================================================

def parse_file(
    path: Path,
    relative_path: str,
    content: str,
) -> tuple[list[CodeNode], list[CodeEdge]]:

    language = detect_language(path)

    if language == "Python":
        return parse_python(
            path,
            relative_path,
            content,
        )

    return parse_generic(
        path,
        relative_path,
        content,
    )


# ============================================================
# PYTHON IMPORTS
# ============================================================

def extract_python_imports(
    content: str,
) -> list[str]:

    imports: list[str] = []

    try:
        tree = ast.parse(content)
    except SyntaxError:
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name:
                    imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            dots = "." * node.level
            module = node.module or ""

            value = (
                f"{dots}{module}"
                if module
                else dots
            )

            if value:
                imports.append(value)

    return list(dict.fromkeys(imports))


# ============================================================
# GENERIC IMPORT EXTRACTION
# ============================================================

def extract_imports(
    content: str,
    language: str | None = None,
) -> list[str]:

    if language == "Python" or language is None:
        python_imports = extract_python_imports(content)

        if python_imports:
            return python_imports

    imports: list[str] = []

    patterns = IMPORT_PATTERNS.get(
        language or "",
        [],
    )

    for pattern in patterns:
        for match in pattern.finditer(content):
            value = match.group(1).strip()

            if not value:
                continue

            # Go import blocks can contain several strings.
            if language == "Go":
                imports.append(value)
                continue

            imports.append(value)

    return list(
        dict.fromkeys(imports)
    )


# ============================================================
# GENERIC CALL EXTRACTION
# ============================================================

CALL_PATTERN = re.compile(
    r'(?<![\w.$])'
    r'([A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*)'
    r'\s*\('
)


KEYWORD_CALLS = {
    "if",
    "for",
    "while",
    "switch",
    "catch",
    "return",
    "sizeof",
    "typeof",
    "class",
    "function",
    "fn",
    "func",
    "def",
    "new",
    "throw",
    "require",
}


def _find_source_scope(
    content: str,
    position: int,
    symbols: list[CodeNode],
) -> str | None:

    candidates = [
        node
        for node in symbols
        if node.line is not None
        and line_number(content, position) >= node.line
    ]

    if not candidates:
        return None

    candidates.sort(
        key=lambda node: node.line or 0,
        reverse=True,
    )

    return candidates[0].id


def extract_generic_relationships(
    relative_path: str,
    content: str,
    language: str,
    symbols: list[CodeNode],
) -> list[tuple[str, str, str, float]]:

    file_id = f"file:{relative_path}"

    relationships: list[
        tuple[str, str, str, float]
    ] = []

    # --------------------------------------------------------
    # Calls
    # --------------------------------------------------------

    for match in CALL_PATTERN.finditer(content):
        expression = match.group(1)

        root = expression.split(".")[0]

        if root in KEYWORD_CALLS:
            continue

        source_id = _find_source_scope(
            content,
            match.start(),
            symbols,
        ) or file_id

        confidence = 0.82

        if "." in expression:
            confidence = 0.78

        relationships.append(
            (
                source_id,
                expression,
                "calls",
                confidence,
            )
        )

    # --------------------------------------------------------
    # References to known symbols
    # --------------------------------------------------------

    symbol_names = {
        node.label
        for node in symbols
        if node.type in {"function", "class"}
    }

    for name in symbol_names:
        if len(name) < 2:
            continue

        pattern = re.compile(
            rf'(?<![\w$]){re.escape(name)}(?![\w$])'
        )

        for match in pattern.finditer(content):
            # Calls are already represented as calls.
            after = content[match.end():]

            if re.match(r'\s*\(', after):
                continue

            source_id = _find_source_scope(
                content,
                match.start(),
                symbols,
            ) or file_id

            relationships.append(
                (
                    source_id,
                    name,
                    "references",
                    0.68,
                )
            )

    # --------------------------------------------------------
    # Test relationships
    # --------------------------------------------------------

    normalized = relative_path.lower()

    is_test_file = (
        "/test/" in normalized
        or "/tests/" in normalized
        or "test_" in Path(normalized).name
        or ".test." in normalized
        or ".spec." in normalized
        or normalized.endswith("_test.go")
        or normalized.endswith("_test.rs")
    )

    if is_test_file:
        for symbol in symbols:
            if symbol.type not in {
                "function",
                "class",
            }:
                continue

            if symbol.path != relative_path:
                continue

            # Test functions/classes themselves are retained;
            # scanner can connect them to referenced symbols.
            continue

    return unique_relationships(
        relationships
    )


# ============================================================
# PYTHON RELATIONSHIPS
# ============================================================

def _expression_to_name(
    node: ast.AST,
) -> str | None:

    if isinstance(node, ast.Name):
        return node.id

    if isinstance(node, ast.Attribute):
        parts: list[str] = []
        current: ast.AST | None = node

        while isinstance(
            current,
            ast.Attribute,
        ):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

            return ".".join(
                reversed(parts)
            )

    return None


class _PythonRelationshipVisitor(ast.NodeVisitor):

    def __init__(self, relative_path: str):
        self.relative_path = relative_path

        self.relationships: list[
            tuple[str, str, str, float]
        ] = []

        self.scope_stack: list[str] = []
        self.import_bound_names: set[str] = set()

    @property
    def file_id(self) -> str:
        return f"file:{self.relative_path}"

    @property
    def source_id(self) -> str:
        if self.scope_stack:
            return self.scope_stack[-1]

        return self.file_id

    def visit_Import(
        self,
        node: ast.Import,
    ) -> Any:

        for alias in node.names:
            self.import_bound_names.add(
                alias.asname
                or alias.name.split(".")[0]
            )

    def visit_ImportFrom(
        self,
        node: ast.ImportFrom,
    ) -> Any:

        for alias in node.names:
            self.import_bound_names.add(
                alias.asname
                or alias.name
            )

    def visit_ClassDef(
        self,
        node: ast.ClassDef,
    ) -> Any:

        node_id = _python_class_id(
            self.relative_path,
            node.lineno,
            node.name,
        )

        self.scope_stack.append(node_id)

        for child in node.body:
            self.visit(child)

        self.scope_stack.pop()

    def visit_FunctionDef(
        self,
        node: ast.FunctionDef,
    ) -> Any:

        self._visit_function(node)

    def visit_AsyncFunctionDef(
        self,
        node: ast.AsyncFunctionDef,
    ) -> Any:

        self._visit_function(node)

    def _visit_function(
        self,
        node: ast.AST,
    ) -> None:

        name = getattr(node, "name")
        lineno = getattr(node, "lineno")

        node_id = _python_symbol_id(
            self.relative_path,
            lineno,
            name,
        )

        self.scope_stack.append(node_id)

        for child in ast.iter_child_nodes(node):
            self.visit(child)

        self.scope_stack.pop()

    def visit_Call(
        self,
        node: ast.Call,
    ) -> Any:

        target_name = _expression_to_name(
            node.func
        )

        if target_name:
            self.relationships.append(
                (
                    self.source_id,
                    target_name,
                    "calls",
                    0.90,
                )
            )

        self.generic_visit(node)

    def visit_Name(
        self,
        node: ast.Name,
    ) -> Any:

        if not isinstance(
            node.ctx,
            ast.Load,
        ):
            return

        if node.id in self.import_bound_names:
            self.relationships.append(
                (
                    self.source_id,
                    node.id,
                    "references",
                    0.80,
                )
            )

        self.generic_visit(node)

    def visit_Attribute(
        self,
        node: ast.Attribute,
    ) -> Any:

        value = _expression_to_name(node)

        if value:
            root = value.split(".")[0]

            if root in self.import_bound_names:
                self.relationships.append(
                    (
                        self.source_id,
                        value,
                        "references",
                        0.80,
                    )
                )

        self.generic_visit(node)


def extract_python_relationships(
    relative_path: str,
    content: str,
) -> list[tuple[str, str, str, float]]:

    try:
        tree = ast.parse(
            content,
            filename=relative_path,
        )
    except SyntaxError:
        return []

    visitor = _PythonRelationshipVisitor(
        relative_path
    )

    for node in tree.body:
        visitor.visit(node)

    return unique_relationships(
        visitor.relationships
    )


# ============================================================
# UNIFIED RELATIONSHIP API
# ============================================================

def extract_relationships(
    relative_path: str,
    content: str,
    language: str | None,
    symbols: list[CodeNode],
) -> list[tuple[str, str, str, float]]:

    if not language:
        return []

    if language == "Python":
        return extract_python_relationships(
            relative_path,
            content,
        )

    return extract_generic_relationships(
        relative_path,
        content,
        language,
        symbols,
    )