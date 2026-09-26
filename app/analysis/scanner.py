from pathlib import Path

from app.analysis.languages import (
    detect_language,
    should_ignore,
)
from app.analysis.parser import (
    extract_imports,
    extract_relationships,
    parse_file,
)
from app.models.code import (
    CodeEdge,
    CodeGraph,
    CodeNode,
)


SUPPORTED_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".cs",
    ".cpp",
    ".cc",
    ".c",
    ".h",
    ".hpp",
    ".php",
    ".rb",
    ".swift",
    ".kt",
    ".kts",
    ".dart",
    ".vue",
    ".svelte",
}


SOURCE_EXTENSIONS = list(
    SUPPORTED_EXTENSIONS
)


class RepositoryScanner:

    def __init__(self, root: Path):
        self.root = root

        self.nodes: list[CodeNode] = []
        self.edges: list[CodeEdge] = []

        self.file_map: dict[str, Path] = {}

        self.nodes_by_id: dict[
            str,
            CodeNode,
        ] = {}

        self.symbols_by_name: dict[
            str,
            list[CodeNode],
        ] = {}

        self.symbols_by_file: dict[
            str,
            list[CodeNode],
        ] = {}

    # ========================================================
    # MAIN SCAN
    # ========================================================

    def scan(self) -> CodeGraph:

        self.nodes = []
        self.edges = []
        self.file_map = {}
        self.nodes_by_id = {}
        self.symbols_by_name = {}
        self.symbols_by_file = {}

        self._collect_files()
        self._add_repository_node()

        # Phase 1:
        # Build all structural nodes.
        self._parse_all_files()

        # Phase 2:
        # Index all symbols.
        self._build_symbol_indexes()

        # Phase 3:
        # Resolve cross-file relationships.
        self._resolve_all_relationships()

        return CodeGraph(
            nodes=self.nodes,
            edges=self.edges,
        )

    # ========================================================
    # FILE COLLECTION
    # ========================================================

    def _collect_files(self) -> None:

        for path in self.root.rglob("*"):

            if not path.is_file():
                continue

            if should_ignore(path):
                continue

            if (
                path.suffix.lower()
                not in SUPPORTED_EXTENSIONS
            ):
                continue

            relative = (
                path
                .relative_to(self.root)
                .as_posix()
            )

            self.file_map[relative] = path

    # ========================================================
    # REPOSITORY NODE
    # ========================================================

    def _add_repository_node(self) -> None:

        self._add_node(
            CodeNode(
                id="repository:root",
                label=(
                    self.root.name
                    or "Repository"
                ),
                type="repository",
                metadata={
                    "root": True,
                },
            )
        )

    # ========================================================
    # FILE PARSING
    # ========================================================

    def _parse_all_files(self) -> None:

        for relative, path in self.file_map.items():
            self._process_file(
                path,
                relative,
            )

    def _process_file(
        self,
        path: Path,
        relative: str,
    ) -> None:

        file_id = f"file:{relative}"
        language = detect_language(path)

        self._add_node(
            CodeNode(
                id=file_id,
                label=path.name,
                type="file",
                path=relative,
                language=language,
                metadata={
                    "extension": path.suffix.lower(),
                    "is_entrypoint": self._is_entrypoint(
                        relative
                    ),
                    "module": self._module_name(
                        relative
                    ),
                },
            )
        )

        self._add_edge(
            CodeEdge(
                source="repository:root",
                target=file_id,
                type="contains",
            )
        )

        try:
            content = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except OSError:
            return

        nodes, edges = parse_file(
            path,
            relative,
            content,
        )

        for node in nodes:
            self._add_node(node)

        for edge in edges:
            self._add_edge(edge)

    # ========================================================
    # SYMBOL INDEXES
    # ========================================================

    def _build_symbol_indexes(self) -> None:

        for node in self.nodes:

            if node.type not in {
                "function",
                "class",
            }:
                continue

            self.symbols_by_name.setdefault(
                node.label,
                [],
            ).append(node)

            if node.path:

                file_id = f"file:{node.path}"

                self.symbols_by_file.setdefault(
                    file_id,
                    [],
                ).append(node)

    # ========================================================
    # RELATIONSHIP RESOLUTION
    # ========================================================

    def _resolve_all_relationships(self) -> None:

        for relative, path in self.file_map.items():

            file_id = f"file:{relative}"

            try:
                content = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            except OSError:
                continue

            language = detect_language(path)

            # ------------------------------------------------
            # Imports
            # ------------------------------------------------

            imports = extract_imports(
                content,
                language,
            )

            for imported in imports:

                target = self._resolve_import(
                    relative,
                    imported,
                )

                if not target:
                    continue

                confidence = self._import_confidence(
                    language
                )

                self._add_edge(
                    CodeEdge(
                        source=file_id,
                        target=f"file:{target}",
                        type="imports",
                        confidence=confidence,
                    )
                )

            # ------------------------------------------------
            # Calls / references
            # ------------------------------------------------

            symbols = self.symbols_by_file.get(
                file_id,
                [],
            )

            relationships = extract_relationships(
                relative,
                content,
                language,
                symbols,
            )

            for (
                source_id,
                target_expression,
                edge_type,
                confidence,
            ) in relationships:

                target_node = (
                    self._resolve_symbol(
                        relative,
                        source_id,
                        target_expression,
                        language,
                    )
                )

                if not target_node:
                    continue

                if target_node.id == source_id:
                    continue

                self._add_edge(
                    CodeEdge(
                        source=source_id,
                        target=target_node.id,
                        type=edge_type,
                        confidence=confidence,
                    )
                )

    # ========================================================
    # IMPORT CONFIDENCE
    # ========================================================

    def _import_confidence(
        self,
        language: str | None,
    ) -> float:

        if language == "Python":
            return 0.95

        if language in {
            "JavaScript",
            "JavaScript React",
            "TypeScript",
            "TypeScript React",
            "Go",
            "Rust",
        }:
            return 0.90

        if language in {
            "Java",
            "C#",
            "Kotlin",
            "Swift",
            "Dart",
        }:
            return 0.88

        return 0.82

    # ========================================================
    # UNIVERSAL SYMBOL RESOLUTION
    # ========================================================

    def _resolve_symbol(
        self,
        source_path: str,
        source_id: str,
        expression: str,
        language: str | None,
    ) -> CodeNode | None:

        expression = expression.strip()

        if not expression:
            return None

        # ----------------------------------------------------
        # Python gets its stronger resolver.
        # ----------------------------------------------------

        if language == "Python":
            return self._resolve_python_symbol(
                source_path,
                source_id,
                expression,
            )

        # ----------------------------------------------------
        # Remove common invocation prefixes.
        # ----------------------------------------------------

        expression = expression.strip()

        if expression.startswith("this."):
            expression = expression[5:]

        if expression.startswith("self."):
            expression = expression[5:]

        parts = expression.split(".")

        root_name = parts[-1]

        # ----------------------------------------------------
        # Same-file symbol.
        # ----------------------------------------------------

        source_file_id = (
            f"file:{source_path}"
        )

        same_file = [
            node
            for node in self.symbols_by_file.get(
                source_file_id,
                [],
            )
            if node.label == root_name
        ]

        if same_file:
            return self._best_symbol(
                same_file,
                source_id,
            )

        # ----------------------------------------------------
        # Exact global symbol.
        # ----------------------------------------------------

        candidates = (
            self.symbols_by_name.get(
                root_name,
                [],
            )
        )

        if candidates:
            return self._best_symbol(
                candidates,
                source_id,
            )

        # ----------------------------------------------------
        # Try the root of a qualified expression.
        #
        # service.createOrder()
        # -> createOrder
        # ----------------------------------------------------

        if len(parts) > 1:

            for candidate_name in reversed(parts[:-1]):

                candidates = (
                    self.symbols_by_name.get(
                        candidate_name,
                        [],
                    )
                )

                if candidates:
                    return self._best_symbol(
                        candidates,
                        source_id,
                    )

        return None

    def _best_symbol(
        self,
        candidates: list[CodeNode],
        source_id: str,
    ) -> CodeNode | None:

        if not candidates:
            return None

        # Prefer same file.
        source = self.nodes_by_id.get(
            source_id
        )

        if source and source.path:

            same_file = [
                candidate
                for candidate in candidates
                if candidate.path == source.path
            ]

            if same_file:
                return same_file[0]

        # Prefer unique result.
        if len(candidates) == 1:
            return candidates[0]

        # Ambiguous global match.
        # Do not invent a relationship.
        return None

    # ========================================================
    # PYTHON SYMBOL RESOLUTION
    # ========================================================

    def _resolve_python_symbol(
        self,
        source_path: str,
        source_id: str,
        expression: str,
    ) -> CodeNode | None:

        expression = expression.strip()

        if not expression:
            return None

        source_file_id = (
            f"file:{source_path}"
        )

        source_node = self.nodes_by_id.get(
            source_id
        )

        # ----------------------------------------------------
        # self.method()
        # ----------------------------------------------------

        if expression.startswith("self."):

            method_name = (
                expression
                .split(".", 1)[1]
                .split(".")[0]
            )

            source_symbols = (
                self.symbols_by_file.get(
                    source_file_id,
                    [],
                )
            )

            parent_class = None

            if source_node:
                parent_class = (
                    source_node.metadata.get(
                        "parent_class"
                    )
                )

            candidates = [
                node
                for node in source_symbols
                if node.label == method_name
                and (
                    not parent_class
                    or node.metadata.get(
                        "parent_class"
                    ) == parent_class
                )
            ]

            if candidates:
                return candidates[0]

        # ----------------------------------------------------
        # Local Python symbol.
        # ----------------------------------------------------

        if "." not in expression:

            local_candidates = [
                node
                for node in self.symbols_by_file.get(
                    source_file_id,
                    [],
                )
                if node.label == expression
            ]

            if local_candidates:
                return local_candidates[0]

        # ----------------------------------------------------
        # Imported Python symbol.
        # ----------------------------------------------------

        binding = (
            self._get_python_import_binding(
                source_path,
                expression,
            )
        )

        if binding:

            module_name, symbol_name = binding

            target_file = (
                self._resolve_python_module(
                    source_path,
                    module_name,
                )
            )

            if target_file:

                target_file_id = (
                    f"file:{target_file}"
                )

                if symbol_name:

                    symbol_leaf = (
                        symbol_name.split(".")[-1]
                    )

                    candidates = [
                        node
                        for node in self.symbols_by_file.get(
                            target_file_id,
                            [],
                        )
                        if node.label == symbol_leaf
                    ]

                    if candidates:
                        return candidates[0]

                file_node = self.nodes_by_id.get(
                    target_file_id
                )

                if file_node:
                    return file_node

        # ----------------------------------------------------
        # Unique global symbol.
        # ----------------------------------------------------

        candidates = (
            self.symbols_by_name.get(
                expression,
                [],
            )
        )

        if len(candidates) == 1:
            return candidates[0]

        same_file = [
            node
            for node in candidates
            if node.path == source_path
        ]

        if same_file:
            return same_file[0]

        return None

    # ========================================================
    # PYTHON IMPORT BINDINGS
    # ========================================================

    def _get_python_import_binding(
        self,
        source_path: str,
        expression: str,
    ) -> tuple[
        str,
        str | None,
    ] | None:

        path = self.file_map.get(
            source_path
        )

        if not path:
            return None

        try:
            content = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        except OSError:
            return None

        try:
            import ast

            tree = ast.parse(content)
        except SyntaxError:
            return None

        parts = expression.split(".")
        first = parts[0]
        remaining = parts[1:]

        for node in ast.walk(tree):

            if isinstance(node, ast.Import):

                for alias in node.names:

                    bound_name = (
                        alias.asname
                        or alias.name.split(".")[0]
                    )

                    if bound_name != first:
                        continue

                    symbol_name = (
                        ".".join(remaining)
                        if remaining
                        else None
                    )

                    return (
                        alias.name,
                        symbol_name,
                    )

            elif isinstance(
                node,
                ast.ImportFrom,
            ):

                module = (
                    "." * node.level
                    + (node.module or "")
                )

                for alias in node.names:

                    bound_name = (
                        alias.asname
                        or alias.name
                    )

                    if bound_name != first:
                        continue

                    symbol_name = alias.name

                    if remaining:
                        symbol_name = ".".join(
                            [symbol_name]
                            + remaining
                        )

                    return (
                        module,
                        symbol_name,
                    )

        return None

    # ========================================================
    # PYTHON MODULE RESOLUTION
    # ========================================================

    def _resolve_python_module(
        self,
        source_path: str,
        module_name: str,
    ) -> str | None:

        module_name = module_name.strip()

        if not module_name:
            return None

        if module_name.startswith("."):
            return self._resolve_python_relative_module(
                source_path,
                module_name,
            )

        module_path = (
            module_name
            .replace(".", "/")
            .strip("/")
        )

        candidates = [
            f"{module_path}.py",
            f"{module_path}/__init__.py",
        ]

        for candidate in candidates:
            if candidate in self.file_map:
                return candidate

        suffixes = [
            f"/{module_path}.py",
            f"/{module_path}/__init__.py",
        ]

        for relative in self.file_map:

            normalized = relative.replace(
                "\\",
                "/",
            )

            if any(
                normalized.endswith(suffix)
                for suffix in suffixes
            ):
                return relative

        return None

    def _resolve_python_relative_module(
        self,
        source_path: str,
        module_name: str,
    ) -> str | None:

        dot_count = 0

        for char in module_name:
            if char != ".":
                break

            dot_count += 1

        module_part = (
            module_name[dot_count:]
            .strip(".")
        )

        source = Path(source_path)
        base = source.parent

        for _ in range(
            max(dot_count - 1, 0)
        ):
            base = base.parent

        if module_part:

            relative_module = (
                base
                / module_part.replace(
                    ".",
                    "/",
                )
            ).as_posix()

        else:
            relative_module = base.as_posix()

        candidates = [
            f"{relative_module}.py",
            f"{relative_module}/__init__.py",
        ]

        for candidate in candidates:
            if candidate in self.file_map:
                return candidate

        return None

    # ========================================================
    # GENERIC IMPORT RESOLUTION
    # ========================================================

    def _resolve_import(
        self,
        source: str,
        imported: str,
    ) -> str | None:

        imported = imported.strip()

        if not imported:
            return None

        # Python
        if source.lower().endswith(".py"):

            target = self._resolve_python_module(
                source,
                imported,
            )

            if target:
                return target

        normalized = (
            imported
            .replace("\\", "/")
            .strip()
        )

        # Remove query/hash artifacts.
        normalized = normalized.split("?")[0]
        normalized = normalized.split("#")[0]

        # External package.
        if not (
            normalized.startswith(".")
            or normalized.startswith("/")
        ):
            return None

        clean = normalized.lstrip("./")

        # Exact file.
        if clean in self.file_map:
            return clean

        # Extension resolution.
        for extension in SOURCE_EXTENSIONS:

            candidate = (
                f"{clean}{extension}"
            )

            if candidate in self.file_map:
                return candidate

        # Index/module resolution.
        for extension in SOURCE_EXTENSIONS:

            index_candidate = (
                f"{clean}/index{extension}"
            )

            if index_candidate in self.file_map:
                return index_candidate

        # Suffix fallback.
        for relative in self.file_map:

            normalized_relative = (
                relative.replace(
                    "\\",
                    "/",
                )
            )

            if normalized_relative.endswith(
                f"/{clean}"
            ):
                return relative

        return None

    # ========================================================
    # ENTRY POINTS
    # ========================================================

    def _is_entrypoint(
        self,
        relative: str,
    ) -> bool:

        name = Path(relative).name.lower()

        return name in {
            "main.py",
            "app.py",
            "run.py",
            "server.py",
            "index.js",
            "index.jsx",
            "index.ts",
            "index.tsx",
            "main.js",
            "main.ts",
            "main.tsx",
            "server.js",
            "server.ts",
            "main.go",
            "main.rs",
            "program.cs",
            "application.java",
            "main.kt",
            "main.dart",
        }

    # ========================================================
    # MODULE NAME
    # ========================================================

    def _module_name(
        self,
        relative: str,
    ) -> str | None:

        path = Path(relative)

        if path.suffix.lower() != ".py":
            return None

        parts = list(
            path.with_suffix("").parts
        )

        if parts and parts[-1] == "__init__":
            parts = parts[:-1]

        if not parts:
            return None

        return ".".join(parts)

    # ========================================================
    # GRAPH HELPERS
    # ========================================================

    def _add_node(
        self,
        node: CodeNode,
    ) -> None:

        if node.id in self.nodes_by_id:
            return

        self.nodes.append(node)
        self.nodes_by_id[node.id] = node

    def _add_edge(
        self,
        edge: CodeEdge,
    ) -> None:

        for existing in self.edges:

            if (
                existing.source == edge.source
                and existing.target == edge.target
                and existing.type == edge.type
            ):
                return

        self.edges.append(edge)