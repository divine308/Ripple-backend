from typing import Literal

from pydantic import BaseModel, Field


AgentStatus = Literal[
    "completed",
    "failed",
]

RiskLevel = Literal[
    "low",
    "medium",
    "high",
    "critical",
]

VerificationStatus = Literal[
    "ready",
    "partial",
    "blocked",
]


class AgentRelationship(BaseModel):
    node_id: str
    label: str
    path: str | None = None
    type: str
    relationship: str
    confidence: float = 0.0


class DependencyAgentResult(BaseModel):
    agent: Literal["dependency"] = "dependency"
    status: AgentStatus = "completed"

    target: str
    target_label: str

    dependencies: list[AgentRelationship] = Field(
        default_factory=list
    )

    dependents: list[AgentRelationship] = Field(
        default_factory=list
    )

    dependency_count: int
    dependent_count: int

    summary: str


class ImpactAgentResult(BaseModel):
    agent: Literal["impact"] = "impact"
    status: AgentStatus = "completed"

    analysis: object


class RiskFactor(BaseModel):
    factor: str
    severity: Literal[
        "low",
        "medium",
        "high",
        "critical",
    ]
    explanation: str


class RiskAgentResult(BaseModel):
    agent: Literal["risk"] = "risk"
    status: AgentStatus = "completed"

    target: str
    target_label: str

    risk: RiskLevel
    score: int = Field(ge=0, le=100)

    factors: list[RiskFactor] = Field(
        default_factory=list
    )

    affected_count: int
    direct_count: int
    indirect_count: int

    summary: str


class VerificationCheck(BaseModel):
    name: str
    status: Literal[
        "pass",
        "warning",
        "missing",
    ]
    details: str


class VerificationAgentResult(BaseModel):
    agent: Literal["verification"] = "verification"
    status: AgentStatus = "completed"

    target: str
    target_label: str

    verification_status: VerificationStatus

    checks: list[VerificationCheck] = Field(
        default_factory=list
    )

    tests_found: int
    affected_tests: int

    summary: str


class AgentRunResult(BaseModel):
    repository_id: str
    target: str
    target_label: str

    status: AgentStatus

    dependency: DependencyAgentResult
    impact: ImpactAgentResult
    risk: RiskAgentResult
    verification: VerificationAgentResult