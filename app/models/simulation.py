from typing import Literal

from pydantic import BaseModel, Field


SimulationChangeType = Literal[
    "modify",
    "delete",
    "rename",
    "add",
]


SimulationImpactType = Literal[
    "direct",
    "indirect",
    "potentially_broken",
]


class SimulationChange(BaseModel):
    type: SimulationChangeType
    target_id: str
    target_label: str
    target_path: str | None = None
    description: str = ""


class SimulationImpactItem(BaseModel):
    node_id: str
    label: str
    path: str | None = None
    type: str
    impact: SimulationImpactType
    relationship: str
    reason: str
    confidence: float = 0.0


class SimulationRisk(BaseModel):
    level: Literal[
        "low",
        "medium",
        "high",
        "critical",
    ]
    score: int = Field(
        ge=0,
        le=100,
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
    )


class SimulationTest(BaseModel):
    node_id: str
    label: str
    path: str | None = None
    reason: str
    confidence: float = 0.0


class SimulationVerification(BaseModel):
    title: str
    description: str
    priority: Literal[
        "high",
        "medium",
        "low",
    ]


class SimulationResult(BaseModel):
    status: Literal[
        "completed",
        "no_impact",
    ]

    change: SimulationChange

    risk: SimulationRisk

    total_affected: int
    direct_count: int
    indirect_count: int
    potentially_broken_count: int

    affected: list[SimulationImpactItem] = Field(
        default_factory=list
    )

    tests: list[SimulationTest] = Field(
        default_factory=list
    )

    verification: list[SimulationVerification] = Field(
        default_factory=list
    )

    summary: str