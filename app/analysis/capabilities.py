from pathlib import Path

from app.models.code import (
    CodeGraph,
    RepositoryCapabilities,
)


FRAMEWORK_SIGNATURES = {
    # Python
    "FastAPI": {
        "files": ["requirements.txt", "pyproject.toml"],
        "imports": ["fastapi"],
    },
    "Django": {
        "files": ["manage.py"],
        "imports": ["django"],
    },
    "Flask": {
        "files": ["requirements.txt", "pyproject.toml"],
        "imports": ["flask"],
    },

    # JavaScript / TypeScript
    "React": {
        "files": ["package.json"],
        "imports": ["react"],
    },
    "Next.js": {
        "files": ["next.config.js", "next.config.mjs", "next.config.ts"],
        "imports": ["next"],
    },
    "Vue": {
        "files": ["vite.config.js", "vite.config.ts"],
        "imports": ["vue"],
    },
    "Svelte": {
        "files": ["svelte.config.js", "vite.config.js"],
        "imports": ["svelte"],
    },
    "Express": {
        "files": ["package.json"],
        "imports": ["express"],
    },
    "NestJS": {
        "files": ["nest-cli.json"],
        "imports": ["@nestjs"],
    },

    # Java
    "Spring": {
        "files": ["pom.xml", "build.gradle", "build.gradle.kts"],
        "imports": ["org.springframework"],
    },

    # PHP
    "Laravel": {
        "files": ["artisan"],
        "imports": ["illuminate"],
    },

    # Ruby
    "Rails": {
        "files": ["bin/rails", "config/routes.rb"],
        "imports": ["rails"],
    },
}


PACKAGE_MANAGERS = {
    "Python": [
        "requirements.txt",
        "requirements-dev.txt",
        "pyproject.toml",
        "poetry.lock",
        "Pipfile",
        "Pipfile.lock",
    ],
    "JavaScript": [
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "bun.lock",
        "bun.lockb",
    ],
    "Java": [
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
    ],
    "Go": [
        "go.mod",
        "go.sum",
    ],
    "Rust": [
        "Cargo.toml",
        "Cargo.lock",
    ],
    "PHP": [
        "composer.json",
        "composer.lock",
    ],
    "Ruby": [
        "Gemfile",
        "Gemfile.lock",
    ],
    "Swift": [
        "Package.swift",
    ],
    "Kotlin": [
        "build.gradle.kts",
    ],
    "Dart": [
        "pubspec.yaml",
        "pubspec.lock",
    ],
}


TEST_FILE_MARKERS = (
    "test_",
    "_test.",
    ".test.",
    ".spec.",
    "_spec.",
    "/tests/",
    "/test/",
    "\\tests\\",
    "\\test\\",
)


ENTRYPOINT_NAMES = {
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
    "Application.java",
}


def _is_test_path(path: str) -> bool:
    normalized = path.replace("\\", "/").lower()

    name = Path(normalized).name

    if any(
        marker in normalized
        for marker in TEST_FILE_MARKERS
    ):
        return True

    if name.startswith("test_"):
        return True

    return (
        ".test." in name
        or ".spec." in name
        or name.endswith("_test.go")
        or name.endswith("_test.rs")
    )


def _find_test_files(
    graph: CodeGraph,
) -> list[str]:
    results = []

    for node in graph.nodes:
        if node.type != "file":
            continue

        path = node.path or ""

        if _is_test_path(path):
            results.append(path)

    return sorted(
        set(results)
    )


def _find_entry_points(
    graph: CodeGraph,
) -> list[str]:
    results = []

    for node in graph.nodes:
        if node.type != "file":
            continue

        if node.metadata.get(
            "is_entrypoint",
            False,
        ):
            results.append(
                node.path or node.label
            )
            continue

        if (
            node.path
            and Path(node.path).name
            in ENTRYPOINT_NAMES
        ):
            results.append(
                node.path
            )

    return sorted(
        set(results)
    )


def _detect_languages(
    graph: CodeGraph,
) -> dict[str, int]:
    counts: dict[str, int] = {}

    for node in graph.nodes:
        if node.type != "file":
            continue

        language = node.language

        if not language:
            continue

        counts[language] = (
            counts.get(language, 0)
            + 1
        )

    return dict(
        sorted(
            counts.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )


def _detect_package_managers(
    root: Path,
    languages: dict[str, int],
) -> list[str]:
    names = set()

    for language in languages:
        for filename in PACKAGE_MANAGERS.get(
            language,
            [],
        ):
            if (root / filename).exists():
                names.add(filename)

    # Check common package files even when
    # language detection is incomplete.
    for filename in {
        "package.json",
        "package-lock.json",
        "yarn.lock",
        "pnpm-lock.yaml",
        "bun.lock",
        "pyproject.toml",
        "requirements.txt",
        "poetry.lock",
        "Pipfile",
        "go.mod",
        "Cargo.toml",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "composer.json",
        "Gemfile",
        "Package.swift",
        "pubspec.yaml",
    }:
        if (root / filename).exists():
            names.add(filename)

    return sorted(names)


def _detect_frameworks(
    root: Path,
) -> list[str]:
    detected = set()

    # Collect a bounded amount of source text.
    # This avoids trying to inspect enormous files.
    text_chunks = []

    for path in root.rglob("*"):
        if not path.is_file():
            continue

        relative = path.relative_to(root).as_posix()

        # Skip obvious generated/vendor folders.
        parts = set(
            part.lower()
            for part in Path(relative).parts
        )

        if parts.intersection({
            "node_modules",
            ".git",
            "dist",
            "build",
            ".next",
            "target",
            "__pycache__",
            ".venv",
            "venv",
        }):
            continue

        if path.suffix.lower() not in {
            ".py",
            ".js",
            ".jsx",
            ".ts",
            ".tsx",
            ".java",
            ".kt",
            ".kts",
            ".php",
            ".rb",
            ".go",
            ".rs",
            ".vue",
            ".svelte",
        }:
            continue

        try:
            text = path.read_text(
                encoding="utf-8",
                errors="ignore",
            )

            text_chunks.append(
                text[:100_000]
            )

        except OSError:
            continue

        if len(text_chunks) >= 200:
            break

    source_text = "\n".join(
        text_chunks
    ).lower()

    for framework, signature in FRAMEWORK_SIGNATURES.items():
        for filename in signature["files"]:
            if (root / filename).exists():
                detected.add(framework)
                break
        else:
            for import_name in signature["imports"]:
                if import_name.lower() in source_text:
                    detected.add(framework)
                    break

    return sorted(detected)


def _edge_counts(
    graph: CodeGraph,
) -> dict[str, int]:
    counts: dict[str, int] = {}

    for edge in graph.edges:
        counts[edge.type] = (
            counts.get(edge.type, 0)
            + 1
        )

    return dict(
        sorted(counts.items())
    )


def _analysis_capabilities(
    graph: CodeGraph,
    test_files: list[str],
) -> dict[str, dict]:
    edge_counts = _edge_counts(graph)

    import_edges = edge_counts.get(
        "imports",
        0,
    )

    call_edges = edge_counts.get(
        "calls",
        0,
    )

    reference_edges = edge_counts.get(
        "references",
        0,
    )

    test_edges = edge_counts.get(
        "tests",
        0,
    )

    relationship_edges = (
        import_edges
        + call_edges
        + reference_edges
        + test_edges
    )

    # Dependency intelligence needs at least
    # some structural relationship evidence.
    dependency_available = (
        relationship_edges > 0
    )

    # Impact needs a graph with actual
    # cross-node relationships.
    impact_available = (
        import_edges
        + call_edges
        + reference_edges
        + test_edges
        > 0
    )

    # Risk can always provide structural
    # signals, but its confidence is limited
    # when the graph is shallow.
    risk_status = (
        "available"
        if relationship_edges > 0
        else "limited"
    )

    # Verification is strongest when tests
    # or test relationships exist.
    if test_files or test_edges:
        verification_status = "available"
        verification_reason = (
            "Test files or test relationships "
            "were detected."
        )
    else:
        verification_status = "limited"
        verification_reason = (
            "No test files or test relationships "
            "were detected."
        )

    return {
        "dependency": {
            "status": (
                "available"
                if dependency_available
                else "limited"
            ),
            "reason": (
                "Repository relationships were detected."
                if dependency_available
                else
                "No cross-node relationships were detected."
            ),
        },
        "impact": {
            "status": (
                "available"
                if impact_available
                else "limited"
            ),
            "reason": (
                "The graph contains relationships that "
                "can be traversed for change impact."
                if impact_available
                else
                "Impact confidence is limited because "
                "the graph has insufficient relationships."
            ),
        },
        "risk": {
            "status": risk_status,
            "reason": (
                "Structural risk signals can be calculated "
                "from the repository graph."
                if risk_status == "available"
                else
                "Only limited structural evidence is available."
            ),
        },
        "verification": {
            "status": verification_status,
            "reason": verification_reason,
        },
    }


def detect_capabilities(
    root: Path,
    graph: CodeGraph,
) -> RepositoryCapabilities:
    languages = _detect_languages(
        graph
    )

    test_files = _find_test_files(
        graph
    )

    entry_points = _find_entry_points(
        graph
    )

    package_managers = (
        _detect_package_managers(
            root,
            languages,
        )
    )

    frameworks = _detect_frameworks(
        root
    )

    edge_counts = _edge_counts(
        graph
    )

    return RepositoryCapabilities(
        languages=languages,
        frameworks=frameworks,
        package_managers=package_managers,
        test_files=test_files,
        test_count=len(test_files),
        entry_points=entry_points,
        edge_counts=edge_counts,
        analyses=_analysis_capabilities(
            graph,
            test_files,
        ),
    )