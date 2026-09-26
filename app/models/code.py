from typing import Literal

from pydantic import BaseModel, Field


NodeType = Literal[
    "repository",
    "directory",
    "file",
    "function",
    "class",
    "module",
    "api",
    "test",
]


EdgeType = Literal[
    "contains",
    "imports",
    "calls",
    "references",
    "tests",
    "exposes",
]


class CodeNode(BaseModel):
    id: str
    label: str
    type: NodeType
    path: str | None = None
    line: int | None = None
    language: str | None = None
    metadata: dict = Field(default_factory=dict)


class CodeEdge(BaseModel):
    source: str
    target: str
    type: EdgeType
    confidence: float = 1.0

class AnalysisCapability(BaseModel):
    status: Literal[
        "available",
        "limited",
        "unavailable",
    ]

    reason: str


class RepositoryCapabilities(BaseModel):
    languages: dict[str, int] = Field(
        default_factory=dict
    )

    frameworks: list[str] = Field(
        default_factory=list
    )

    package_managers: list[str] = Field(
        default_factory=list
    )

    test_files: list[str] = Field(
        default_factory=list
    )

    test_count: int = 0

    entry_points: list[str] = Field(
        default_factory=list
    )

    edge_counts: dict[str, int] = Field(
        default_factory=dict
    )

    analyses: dict[
        str,
        AnalysisCapability,
    ] = Field(
        default_factory=dict
    )

class CodeGraph(BaseModel):
    nodes: list[CodeNode]
    edges: list[CodeEdge]


class ImpactItem(BaseModel):
    node_id: str
    label: str
    path: str | None = None
    type: str
    impact: Literal["direct", "indirect", "potential"]
    reason: str
    confidence: float = 0.0


class ImpactAnalysis(BaseModel):
    target: CodeNode
    total_affected: int
    direct_count: int
    indirect_count: int
    potential_count: int
    risk: Literal["low", "medium", "high", "critical"]
    summary: str
    affected: list[ImpactItem]