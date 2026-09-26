from pathlib import Path

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Query,
    UploadFile,
)
from pydantic import BaseModel, Field

from app.analysis.capabilities import detect_capabilities

from app.analysis.agents import (
    DependencyAgent,
    ImpactAgent,
    RiskAgent,
    VerificationAgent,
)
from app.analysis.impact import ImpactEngine
from app.analysis.scanner import RepositoryScanner
from app.models.agents import AgentRunResult
from app.models.code import (
    CodeGraph,
    ImpactAnalysis,
)
from app.services.repository import RepositoryService

from app.analysis.simulation import SimulationEngine

from app.models.simulation import SimulationResult


router = APIRouter()

repository_service = RepositoryService()

repositories: dict[str, Path] = {}
graphs: dict[str, CodeGraph] = {}


class GitHubRepositoryRequest(BaseModel):
    url: str = Field(
        min_length=1,
        max_length=500,
    )

    branch: str | None = Field(
        default=None,
        max_length=250,
    )


def analyze_repository(
    root: Path,
    repository_id: str,
) -> dict:
    scanner = RepositoryScanner(root)

    graph = scanner.scan()

    capabilities = detect_capabilities(
        root,
        graph,
    )

    repositories[repository_id] = root
    graphs[repository_id] = graph

    languages = sorted(
        {
            node.language
            for node in graph.nodes
            if node.language
        }
    )

    files = [
        node
        for node in graph.nodes
        if node.type == "file"
    ]

    return {
        "repository_id": repository_id,
        "name": root.name,
        "files": len(files),
        "nodes": len(graph.nodes),
        "edges": len(graph.edges),
        "languages": languages,
        "capabilities": capabilities,
        "graph": graph,
    }


# ============================================================
# REPOSITORY
# ============================================================

@router.post("/repositories/upload")
async def upload_repository(
    file: UploadFile = File(...),
):
    try:
        root = await repository_service.save_upload(
            file
        )

        repository_id = root.parent.name

        return analyze_repository(
            root,
            repository_id,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


@router.post("/repositories/github")
async def connect_github_repository(
    payload: GitHubRepositoryRequest,
):
    try:
        root = (
            await repository_service
            .save_github_repository(
                repository_url=payload.url,
                branch=payload.branch,
            )
        )

        repository_id = root.parent.name

        result = analyze_repository(
            root,
            repository_id,
        )

        result["source"] = "github"
        result["repository_url"] = payload.url
        result["branch"] = (
            payload.branch or "default"
        )

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )


# ============================================================
# AGENTS
# ============================================================

@router.post(
    "/repositories/{repository_id}/agents/dependency",
)
async def run_dependency_agent(
    repository_id: str,
    node_id: str,
):
    graph = graphs.get(repository_id)

    if not graph:
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
        )

    try:
        agent = DependencyAgent(graph)

        return agent.run(node_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


@router.post(
    "/repositories/{repository_id}/agents/impact",
)
async def run_impact_agent(
    repository_id: str,
    node_id: str,
):
    graph = graphs.get(repository_id)

    if not graph:
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
        )

    try:
        agent = ImpactAgent(graph)

        return agent.run(node_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


@router.post(
    "/repositories/{repository_id}/agents/risk",
)
async def run_risk_agent(
    repository_id: str,
    node_id: str,
):
    graph = graphs.get(repository_id)

    if not graph:
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
        )

    try:
        agent = RiskAgent(graph)

        return agent.run(node_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


@router.post(
    "/repositories/{repository_id}/agents/verification",
)
async def run_verification_agent(
    repository_id: str,
    node_id: str,
):
    graph = graphs.get(repository_id)

    if not graph:
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
        )

    try:
        agent = VerificationAgent(graph)

        return agent.run(node_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


@router.post(
    "/repositories/{repository_id}/agents/run",
    response_model=AgentRunResult,
)
async def run_all_agents(
    repository_id: str,
    node_id: str,
):
    graph = graphs.get(repository_id)

    if not graph:
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
        )

    try:
        nodes = {
            node.id: node
            for node in graph.nodes
        }

        target = nodes.get(node_id)

        if not target:
            raise HTTPException(
                status_code=404,
                detail="Target node not found.",
            )

        dependency_agent = DependencyAgent(graph)
        impact_agent = ImpactAgent(graph)
        risk_agent = RiskAgent(graph)
        verification_agent = VerificationAgent(graph)

        dependency_result = dependency_agent.run(
            node_id
        )

        impact_result = impact_agent.run(
            node_id
        )

        risk_result = risk_agent.run(
            node_id
        )

        verification_result = (
            verification_agent.run(
                node_id
            )
        )

        return AgentRunResult(
            repository_id=repository_id,
            target=target.id,
            target_label=target.label,
            status="completed",
            dependency=dependency_result,
            impact=impact_result,
            risk=risk_result,
            verification=verification_result,
        )

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Agent execution failed.",
        )


# ============================================================
# GRAPH
# ============================================================

@router.get(
    "/repositories/{repository_id}/graph",
    response_model=CodeGraph,
)
async def get_graph(
    repository_id: str,
):
    graph = graphs.get(repository_id)

    if not graph:
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
        )

    return graph


# ============================================================
# FILE VIEWER
# ============================================================

@router.get(
    "/repositories/{repository_id}/file",
)
async def get_repository_file(
    repository_id: str,
    path: str = Query(
        ...,
        min_length=1,
        max_length=1000,
    ),
):
    root = repositories.get(repository_id)

    if not root:
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
        )

    try:
        requested_path = Path(path)

        if requested_path.is_absolute():
            raise HTTPException(
                status_code=400,
                detail="Invalid file path.",
            )

        file_path = (
            root / requested_path
        ).resolve()

        root_resolved = root.resolve()

        try:
            file_path.relative_to(
                root_resolved
            )
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid file path.",
            )

        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail="File not found.",
            )

        if not file_path.is_file():
            raise HTTPException(
                status_code=400,
                detail="The selected path is not a file.",
            )

        max_file_size = 2 * 1024 * 1024

        if file_path.stat().st_size > max_file_size:
            raise HTTPException(
                status_code=413,
                detail=(
                    "This file is too large to display "
                    "in the Ripple code viewer."
                ),
            )

        try:
            content = file_path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except OSError:
            raise HTTPException(
                status_code=500,
                detail="Unable to read the selected file.",
            )

        relative_path = file_path.relative_to(
            root_resolved
        ).as_posix()

        suffix = file_path.suffix.lower()

        language_map = {
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".py": "python",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".c": "c",
            ".h": "c",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".cs": "csharp",
            ".php": "php",
            ".rb": "ruby",
            ".swift": "swift",
            ".kt": "kotlin",
            ".kts": "kotlin",
            ".html": "html",
            ".css": "css",
            ".scss": "scss",
            ".sass": "scss",
            ".json": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".md": "markdown",
            ".sql": "sql",
            ".sh": "shell",
            ".bash": "shell",
            ".xml": "xml",
            ".vue": "vue",
            ".svelte": "svelte",
        }

        language = language_map.get(
            suffix,
            "text",
        )

        return {
            "path": relative_path,
            "name": file_path.name,
            "language": language,
            "size": file_path.stat().st_size,
            "content": content,
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Unable to load the selected file.",
        )


# ============================================================
# IMPACT
# ============================================================

@router.post(
    "/repositories/{repository_id}/impact",
    response_model=ImpactAnalysis,
)
async def analyze_impact(
    repository_id: str,
    node_id: str,
):
    graph = graphs.get(repository_id)

    if not graph:
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
        )

    try:
        engine = ImpactEngine(graph)

        return engine.analyze(node_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

# ============================================================
# SIMULATION
# ============================================================

class SimulationRequest(BaseModel):
    change_type: str = Field(
        min_length=1,
        max_length=50,
    )

    description: str = Field(
        default="",
        max_length=2000,
    )


@router.post(
    "/repositories/{repository_id}/simulate",
    response_model=SimulationResult,
)
async def simulate_change(
    repository_id: str,
    node_id: str,
    payload: SimulationRequest,
):
    graph = graphs.get(repository_id)

    if not graph:
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
        )

    try:
        engine = SimulationEngine(
            graph
        )

        return engine.simulate(
            target_id=node_id,
            change_type=payload.change_type,
            description=payload.description,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Simulation failed.",
        )

# ============================================================
# SUMMARY
# ============================================================

@router.get(
    "/repositories/{repository_id}/summary"
)
async def repository_summary(
    repository_id: str,
):
    graph = graphs.get(repository_id)

    if not graph:
        raise HTTPException(
            status_code=404,
            detail="Repository not found.",
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
                languages.get(node.language, 0)
                + 1
            )

    return {
        "files": len(files),
        "functions": len(functions),
        "classes": len(classes),
        "edges": len(graph.edges),
        "languages": languages,
    }

   