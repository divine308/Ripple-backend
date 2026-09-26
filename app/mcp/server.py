from pathlib import Path
from time import perf_counter

from mcp.server import MCPServer

from app.api.routes import (
    graphs,
    repositories,
)
from app.analysis.agents import (
    DependencyAgent,
    ImpactAgent,
    RiskAgent,
    VerificationAgent,
)
from app.analysis.impact import ImpactEngine
from app.mcp.activity import record_mcp_activity
from app.analysis.capabilities import detect_capabilities

mcp = MCPServer(
    "Ripple Developer Intelligence",
)


# ============================================================
# REPOSITORY RESOLUTION
# ============================================================

def get_current_repository_id() -> str:
    """
    Return the most recently connected repository in Ripple.

    Ripple stores connected repositories and their graphs in
    shared in-memory dictionaries used by the API/frontend.

    The most recently connected repository is treated as the
    currently active repository for MCP/Bob.
    """

    if not repositories:
        raise ValueError(
            "No repository is currently connected in Ripple."
        )

    repository_id = next(reversed(repositories))

    if repository_id not in graphs:
        raise ValueError(
            f"Repository '{repository_id}' is connected "
            "but has no graph."
        )

    return repository_id


def resolve_repository_id(
    repository_id: str | None = None,
) -> str:
    """
    Resolve a repository ID.

    When no ID is supplied, automatically use the repository
    currently connected through the Ripple frontend.
    """

    if repository_id:
        return repository_id

    return get_current_repository_id()


def get_graph_or_error(
    repository_id: str | None = None,
):
    """
    Return the resolved repository ID and its graph.
    """

    repository_id = resolve_repository_id(repository_id)

    graph = graphs.get(repository_id)

    if not graph:
        raise ValueError(
            f"Repository '{repository_id}' was not found."
        )

    return repository_id, graph


# ============================================================
# ACTIVITY HELPERS
# ============================================================

def _record_success(
    tool: str,
    started: float,
    repository_id: str | None = None,
    message: str | None = None,
) -> None:
    """
    Record a successful MCP tool invocation.
    """

    duration_ms = round(
        (perf_counter() - started) * 1000
    )

    record_mcp_activity(
        tool=tool,
        status="success",
        repository_id=repository_id,
        message=message,
        duration_ms=duration_ms,
    )


def _record_error(
    tool: str,
    started: float,
    error: Exception,
    repository_id: str | None = None,
) -> None:
    """
    Record a failed MCP tool invocation.
    """

    duration_ms = round(
        (perf_counter() - started) * 1000
    )

    record_mcp_activity(
        tool=tool,
        status="error",
        repository_id=repository_id,
        message=str(error),
        duration_ms=duration_ms,
    )


# ============================================================
# CURRENT REPOSITORY
# ============================================================

@mcp.tool()
def ripple_current_repository() -> dict:
    """
    Get the repository currently connected in Ripple.

    This is the repository selected by the user through the
    Ripple frontend.
    """

    started = perf_counter()
    tool = "ripple_current_repository"

    try:
        repository_id = get_current_repository_id()

        root = repositories[repository_id]
        graph = graphs.get(repository_id)
        capabilities = detect_capabilities(
            root,
            graph,
        )

        files = []
        functions = []
        classes = []

        if graph:
            files = [
                node
                for node in graph.nodes
                if node.type == "file"
            ]

            functions = [
                node
                for node in graph.nodes
                if node.type == "function"
            ]

            classes = [
                node
                for node in graph.nodes
                if node.type == "class"
            ]

        result = {
            "repository_id": repository_id,
            "name": root.name,
            "path": str(root),
            "files": len(files),
            "functions": len(functions),
            "classes": len(classes),
            "capabilities": capabilities.model_dump(),
            "status": "connected",
        }

        _record_success(
            tool=tool,
            started=started,
            repository_id=repository_id,
            message=(
                f"Current repository: {root.name} "
                f"({len(files)} files)"
            ),
        )

        return result

    except Exception as exc:
        _record_error(
            tool=tool,
            started=started,
            error=exc,
        )
        raise


@mcp.tool()
def ripple_repository_capabilities() -> dict:
    """
    Analyze the capabilities of the repository currently connected
    through the Ripple frontend.

    Detects languages, frameworks, package managers, tests,
    entry points, graph relationships, and available analyses.
    """

    started = perf_counter()
    tool = "ripple_repository_capabilities"

    try:
        repository_id = get_current_repository_id()

        root = repositories[repository_id]
        graph = graphs[repository_id]

        capabilities = detect_capabilities(
            root,
            graph,
        )

        result = {
            "repository_id": repository_id,
            "name": root.name,
            "capabilities": capabilities.model_dump(),
        }

        _record_success(
            tool=tool,
            started=started,
            repository_id=repository_id,
            message=(
                f"Detected repository capabilities for "
                f"{root.name}."
            ),
        )

        return result

    except Exception as exc:
        _record_error(
            tool=tool,
            started=started,
            error=exc,
        )
        raise

# ============================================================
# REPOSITORY SUMMARY
# ============================================================

@mcp.tool()
def ripple_repository_summary(
    repository_id: str | None = None,
) -> dict:
    """
    Get a structural summary of a connected Ripple repository.

    If repository_id is omitted, Ripple automatically uses
    the repository currently connected through the frontend.

    Returns file, function, class, edge and language counts.
    """

    started = perf_counter()
    tool = "ripple_repository_summary"

    try:
        repository_id, graph = get_graph_or_error(
            repository_id
        )

        root = repositories[repository_id]

        capabilities = detect_capabilities(
            root,
            graph,
        )

        files = [
            node
            for node in graph.nodes
            if node.type == "file"
        ]

        functions = [
            node
            for node in graph.nodes
            if node.type == "function"
        ]

        classes = [
            node
            for node in graph.nodes
            if node.type == "class"
        ]

        languages: dict[str, int] = {}

        for node in files:
            if node.language:
                languages[node.language] = (
                    languages.get(node.language, 0) + 1
                )

        result = {
            "repository_id": repository_id,
            "files": len(files),
            "functions": len(functions),
            "classes": len(classes),
            "edges": len(graph.edges),
            "languages": languages,
            "capabilities": capabilities.model_dump(),
        }

        _record_success(
            tool=tool,
            started=started,
            repository_id=repository_id,
            message=(
                f"Generated repository summary: "
                f"{len(files)} files, "
                f"{len(functions)} functions, "
                f"{len(classes)} classes, "
                f"{len(graph.edges)} edges."
            ),
        )

        return result

    except Exception as exc:
        _record_error(
            tool=tool,
            started=started,
            error=exc,
            repository_id=repository_id,
        )
        raise


# ============================================================
# GRAPH
# ============================================================

@mcp.tool()
def ripple_get_graph(
    repository_id: str | None = None,
) -> dict:
    """
    Get the dependency graph of a connected Ripple repository.

    If repository_id is omitted, Ripple automatically uses
    the repository currently connected through the frontend.
    """

    started = perf_counter()
    tool = "ripple_get_graph"

    try:
        repository_id, graph = get_graph_or_error(
            repository_id
        )

        result = graph.model_dump()
        result["repository_id"] = repository_id

        _record_success(
            tool=tool,
            started=started,
            repository_id=repository_id,
            message=(
                f"Retrieved graph with "
                f"{len(graph.nodes)} nodes and "
                f"{len(graph.edges)} edges."
            ),
        )

        return result

    except Exception as exc:
        _record_error(
            tool=tool,
            started=started,
            error=exc,
            repository_id=repository_id,
        )
        raise


# ============================================================
# DEPENDENCY ANALYSIS
# ============================================================

@mcp.tool()
def ripple_dependency_analysis(
    node_id: str,
    repository_id: str | None = None,
) -> dict:
    """
    Analyze the direct dependencies and dependents of a Ripple code node.

    If repository_id is omitted, Ripple automatically uses
    the repository currently connected through the frontend.
    """

    started = perf_counter()
    tool = "ripple_dependency_analysis"

    try:
        repository_id, graph = get_graph_or_error(
            repository_id
        )

        agent = DependencyAgent(graph)

        result = agent.run(node_id)

        response = result.model_dump()
        response["repository_id"] = repository_id

        _record_success(
            tool=tool,
            started=started,
            repository_id=repository_id,
            message=(
                f"Analyzed dependencies for node "
                f"{node_id}."
            ),
        )

        return response

    except Exception as exc:
        _record_error(
            tool=tool,
            started=started,
            error=exc,
            repository_id=repository_id,
        )
        raise


# ============================================================
# IMPACT ANALYSIS
# ============================================================

@mcp.tool()
def ripple_analyze_impact(
    node_id: str,
    repository_id: str | None = None,
) -> dict:
    """
    Analyze the downstream blast radius of changing a Ripple code node.

    If repository_id is omitted, Ripple automatically uses
    the repository currently connected through the frontend.

    Returns directly and indirectly affected nodes,
    relationships, confidence values, risk level and
    impact summary.
    """

    started = perf_counter()
    tool = "ripple_analyze_impact"

    try:
        repository_id, graph = get_graph_or_error(
            repository_id
        )

        engine = ImpactEngine(graph)

        result = engine.analyze(node_id)

        response = result.model_dump()
        response["repository_id"] = repository_id

        _record_success(
            tool=tool,
            started=started,
            repository_id=repository_id,
            message=(
                f"Analyzed downstream impact for node "
                f"{node_id}."
            ),
        )

        return response

    except Exception as exc:
        _record_error(
            tool=tool,
            started=started,
            error=exc,
            repository_id=repository_id,
        )
        raise


# ============================================================
# RISK ANALYSIS
# ============================================================

@mcp.tool()
def ripple_risk_analysis(
    node_id: str,
    repository_id: str | None = None,
) -> dict:
    """
    Calculate Ripple's change-risk assessment for a code node.

    If repository_id is omitted, Ripple automatically uses
    the repository currently connected through the frontend.

    Returns risk level, score, risk factors and affected counts.
    """

    started = perf_counter()
    tool = "ripple_risk_analysis"

    try:
        repository_id, graph = get_graph_or_error(
            repository_id
        )

        agent = RiskAgent(graph)

        result = agent.run(node_id)

        response = result.model_dump()
        response["repository_id"] = repository_id

        _record_success(
            tool=tool,
            started=started,
            repository_id=repository_id,
            message=(
                f"Calculated risk analysis for node "
                f"{node_id}."
            ),
        )

        return response

    except Exception as exc:
        _record_error(
            tool=tool,
            started=started,
            error=exc,
            repository_id=repository_id,
        )
        raise


# ============================================================
# VERIFICATION ANALYSIS
# ============================================================

@mcp.tool()
def ripple_verification_analysis(
    node_id: str,
    repository_id: str | None = None,
) -> dict:
    """
    Determine Ripple's verification readiness for a code node.

    If repository_id is omitted, Ripple automatically uses
    the repository currently connected through the frontend.

    Returns test candidates, verification checks and
    verification status.
    """

    started = perf_counter()
    tool = "ripple_verification_analysis"

    try:
        repository_id, graph = get_graph_or_error(
            repository_id
        )

        agent = VerificationAgent(graph)

        result = agent.run(node_id)

        response = result.model_dump()
        response["repository_id"] = repository_id

        _record_success(
            tool=tool,
            started=started,
            repository_id=repository_id,
            message=(
                f"Calculated verification readiness for node "
                f"{node_id}."
            ),
        )

        return response

    except Exception as exc:
        _record_error(
            tool=tool,
            started=started,
            error=exc,
            repository_id=repository_id,
        )
        raise


# ============================================================
# COMPLETE AGENT PIPELINE
# ============================================================

@mcp.tool()
def ripple_run_all_agents(
    node_id: str,
    repository_id: str | None = None,
) -> dict:
    """
    Run Ripple's complete analysis pipeline for a code node.

    If repository_id is omitted, Ripple automatically uses
    the repository currently connected through the frontend.

    Runs dependency, impact, risk and verification analysis together.
    """

    started = perf_counter()
    tool = "ripple_run_all_agents"

    try:
        repository_id, graph = get_graph_or_error(
            repository_id
        )

        nodes = {
            node.id: node
            for node in graph.nodes
        }

        target = nodes.get(node_id)

        if not target:
            raise ValueError(
                "Target node not found."
            )

        dependency_agent = DependencyAgent(graph)
        impact_agent = ImpactAgent(graph)
        risk_agent = RiskAgent(graph)
        verification_agent = VerificationAgent(graph)

        dependency_result = dependency_agent.run(node_id)
        impact_result = impact_agent.run(node_id)
        risk_result = risk_agent.run(node_id)
        verification_result = verification_agent.run(node_id)

        result = {
            "repository_id": repository_id,
            "target": target.id,
            "target_label": target.label,
            "status": "completed",
            "dependency": dependency_result.model_dump(),
            "impact": impact_result.model_dump(),
            "risk": risk_result.model_dump(),
            "verification": verification_result.model_dump(),
        }

        _record_success(
            tool=tool,
            started=started,
            repository_id=repository_id,
            message=(
                f"Completed dependency, impact, risk and "
                f"verification analysis for {target.label}."
            ),
        )

        return result

    except Exception as exc:
        _record_error(
            tool=tool,
            started=started,
            error=exc,
            repository_id=repository_id,
        )
        raise


# ============================================================
# FILE ACCESS
# ============================================================

@mcp.tool()
def ripple_get_file(
    path: str,
    repository_id: str | None = None,
) -> dict:
    """
    Read a file from a connected Ripple repository.

    If repository_id is omitted, Ripple automatically uses
    the repository currently connected through the frontend.

    The path must be relative to the repository root.
    """

    started = perf_counter()
    tool = "ripple_get_file"

    try:
        repository_id = resolve_repository_id(
            repository_id
        )

        root = repositories.get(repository_id)

        if not root:
            raise ValueError(
                f"Repository '{repository_id}' was not found."
            )

        requested_path = root / path

        file_path = requested_path.resolve()
        root_resolved = root.resolve()

        try:
            file_path.relative_to(root_resolved)
        except ValueError:
            raise ValueError(
                "Invalid file path."
            )

        if not file_path.exists():
            raise ValueError(
                "File not found."
            )

        if not file_path.is_file():
            raise ValueError(
                "The selected path is not a file."
            )

        max_file_size = 2 * 1024 * 1024

        if file_path.stat().st_size > max_file_size:
            raise ValueError(
                "This file is too large to display."
            )

        content = file_path.read_text(
            encoding="utf-8",
            errors="replace",
        )

        result = {
            "repository_id": repository_id,
            "path": file_path.relative_to(
                root_resolved
            ).as_posix(),
            "name": file_path.name,
            "size": file_path.stat().st_size,
            "content": content,
        }

        _record_success(
            tool=tool,
            started=started,
            repository_id=repository_id,
            message=(
                f"Read file {result['path']} "
                f"({result['size']} bytes)."
            ),
        )

        return result

    except Exception as exc:
        _record_error(
            tool=tool,
            started=started,
            error=exc,
            repository_id=repository_id,
        )
        raise


# ============================================================
# MCP APP
# ============================================================

def get_mcp_app():
    return mcp.streamable_http_app()

