from pathlib import Path

LANGUAGE_MAP = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript React",
    ".ts": "TypeScript",
    ".tsx": "TypeScript React",
    ".java": "Java",
    ".go": "Go",
    ".rs": "Rust",
    ".cs": "C#",
    ".cpp": "C++",
    ".cc": "C++",
    ".c": "C",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".php": "PHP",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".kts": "Kotlin",
    ".dart": "Dart",
    ".vue": "Vue",
    ".svelte": "Svelte",
}


IGNORED_DIRECTORIES = {
    "node_modules",
    ".git",
    ".next",
    "dist",
    "build",
    "coverage",
    ".venv",
    "venv",
    "__pycache__",
    ".idea",
    ".vscode",
}


def detect_language(path: Path) -> str | None:
    return LANGUAGE_MAP.get(path.suffix.lower())


def should_ignore(path: Path) -> bool:
    return any(part in IGNORED_DIRECTORIES for part in path.parts)