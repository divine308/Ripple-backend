from collections import defaultdict

from app.analysis.impact import ImpactEngine
from app.models.agents import (
    AgentRelationship,
    DependencyAgentResult,
    ImpactAgentResult,
    RiskAgentResult,
    RiskFactor,
    VerificationAgentResult,
    VerificationCheck,
)
from app.models.code import CodeGraph, CodeNode


IMPACT_EDGE_TYPES = {
    "imports",
    "calls",
    "references",
    "tests",
    "exposes",
}


class DependencyAgent:
    def __init__(self, graph: CodeGraph):
        self.graph = graph

        self.nodes = {
            node.id: node
            for node in graph.nodes
        }

        self.outgoing = defaultdict(list)
        self.incoming = defaultdict(list)

        for edge in graph.edges:
            if edge.type not in IMPACT_EDGE_TYPES:
                continue

            self.outgoing[edge.source].append(edge)
            self.incoming[edge.target].append(edge)

    def run(self, node_id: str) -> DependencyAgentResult:
        target = self.nodes.get(node_id)

        if not target:
            raise ValueError("Target node not found.")

        dependencies = []

        for edge in self.outgoing.get(node_id, []):
            node = self.nodes.get(edge.target)

            if not node:
                continue

            dependencies.append(
                AgentRelationship(
                    node_id=node.id,
                    label=node.label,
                    path=node.path,
                    type=node.type,
                    relationship=edge.type,
                    confidence=edge.confidence,
                )
            )

        dependents = []

        for edge in self.incoming.get(node_id, []):
            node = self.nodes.get(edge.source)

            if not node:
                continue

            dependents.append(
                AgentRelationship(
                    node_id=node.id,
                    label=node.label,
                    path=node.path,
                    type=node.type,
                    relationship=edge.type,
                    confidence=edge.confidence,
                )
            )

        summary = self._summary(
            target,
            len(dependencies),
            len(dependents),
        )

        return DependencyAgentResult(
            target=target.id,
            target_label=target.label,
            dependencies=dependencies,
            dependents=dependents,
            dependency_count=len(dependencies),
            dependent_count=len(dependents),
            summary=summary,
        )

    def _summary(
        self,
        target: CodeNode,
        dependency_count: int,
        dependent_count: int,
    ) -> str:
        return (
            f"{target.label} has "
            f"{dependency_count} direct dependencies and "
            f"{dependent_count} direct dependents."
        )


class ImpactAgent:
    def __init__(self, graph: CodeGraph):
        self.engine = ImpactEngine(graph)

    def run(self, node_id: str) -> ImpactAgentResult:
        analysis = self.engine.analyze(node_id)

        return ImpactAgentResult(
            analysis=analysis,
        )


class RiskAgent:
    def __init__(self, graph: CodeGraph):
        self.graph = graph
        self.nodes = {
            node.id: node
            for node in graph.nodes
        }

        self.engine = ImpactEngine(graph)

    def run(self, node_id: str) -> RiskAgentResult:
        target = self.nodes.get(node_id)

        if not target:
            raise ValueError("Target node not found.")

        analysis = self.engine.analyze(node_id)

        factors = []

        score = 0

        direct = analysis.direct_count
        indirect = analysis.indirect_count
        total = analysis.total_affected

        # Direct blast radius
        if direct >= 10:
            score += 30

            factors.append(
                RiskFactor(
                    factor="High direct dependency count",
                    severity="critical",
                    explanation=(
                        f"{direct} directly dependent nodes "
                        "may be affected."
                    ),
                )
            )

        elif direct >= 5:
            score += 20

            factors.append(
                RiskFactor(
                    factor="Elevated direct dependency count",
                    severity="high",
                    explanation=(
                        f"{direct} directly dependent nodes "
                        "may be affected."
                    ),
                )
            )

        elif direct > 0:
            score += 10

            factors.append(
                RiskFactor(
                    factor="Direct dependencies detected",
                    severity="medium",
                    explanation=(
                        f"{direct} directly dependent nodes "
                        "may be affected."
                    ),
                )
            )

        # Indirect blast radius
        if indirect >= 15:
            score += 25

            factors.append(
                RiskFactor(
                    factor="Large indirect blast radius",
                    severity="critical",
                    explanation=(
                        f"{indirect} indirect connections "
                        "were discovered."
                    ),
                )
            )

        elif indirect >= 5:
            score += 15

            factors.append(
                RiskFactor(
                    factor="Indirect dependencies detected",
                    severity="high",
                    explanation=(
                        f"{indirect} indirect connections "
                        "were discovered."
                    ),
                )
            )

        elif indirect > 0:
            score += 5

            factors.append(
                RiskFactor(
                    factor="Indirect impact detected",
                    severity="medium",
                    explanation=(
                        f"{indirect} indirect connections "
                        "were discovered."
                    ),
                )
            )

        # Important node types
        if target.type == "api":
            score += 20

            factors.append(
                RiskFactor(
                    factor="API surface",
                    severity="high",
                    explanation=(
                        "The selected node represents an API "
                        "surface and may affect external consumers."
                    ),
                )
            )

        elif target.type == "class":
            score += 10

            factors.append(
                RiskFactor(
                    factor="Shared class",
                    severity="medium",
                    explanation=(
                        "The selected node is a class that may "
                        "be referenced by multiple parts of the codebase."
                    ),
                )
            )

        elif target.type == "function":
            score += 5

        # Large overall impact
        if total >= 25:
            score += 25

            factors.append(
                RiskFactor(
                    factor="Large overall blast radius",
                    severity="critical",
                    explanation=(
                        f"{total} potentially affected connections "
                        "were identified."
                    ),
                )
            )

        score = min(score, 100)

        risk = self._risk_level(score)

        if not factors:
            factors.append(
                RiskFactor(
                    factor="Limited dependency surface",
                    severity="low",
                    explanation=(
                        "No significant dependency risk factors "
                        "were detected."
                    ),
                )
            )

        return RiskAgentResult(
            target=target.id,
            target_label=target.label,
            risk=risk,
            score=score,
            factors=factors,
            affected_count=total,
            direct_count=direct,
            indirect_count=indirect,
            summary=(
                f"{target.label} has an estimated {risk} "
                f"change risk with {total} potentially affected "
                "connections."
            ),
        )

    def _risk_level(self, score: int):
        if score >= 75:
            return "critical"

        if score >= 50:
            return "high"

        if score >= 25:
            return "medium"

        return "low"


class VerificationAgent:
    def __init__(self, graph: CodeGraph):
        self.graph = graph

        self.nodes = {
            node.id: node
            for node in graph.nodes
        }

    def run(self, node_id: str) -> VerificationAgentResult:
        target = self.nodes.get(node_id)

        if not target:
            raise ValueError("Target node not found.")

        tests = self._find_tests(node_id)

        checks = []

        if tests:
            checks.append(
                VerificationCheck(
                    name="Test coverage candidates",
                    status="pass",
                    details=(
                        f"{len(tests)} test-related nodes were "
                        "identified around the selected code."
                    ),
                )
            )
        else:
            checks.append(
                VerificationCheck(
                    name="Test coverage candidates",
                    status="missing",
                    details=(
                        "No test relationship was discovered "
                        "for the selected node."
                    ),
                )
            )

        if target.type in {"api", "class", "function"}:
            checks.append(
                VerificationCheck(
                    name="Behavioral surface",
                    status="pass",
                    details=(
                        f"The selected node is a {target.type} "
                        "and should be verified after modification."
                    ),
                )
            )
        else:
            checks.append(
                VerificationCheck(
                    name="Behavioral surface",
                    status="warning",
                    details=(
                        "The selected node is not a primary "
                        "behavioral code element."
                    ),
                )
            )

        affected_tests = len(tests)

        if affected_tests == 0:
            verification_status = "blocked"
        elif affected_tests < 2:
            verification_status = "partial"
        else:
            verification_status = "ready"

        summary = self._summary(
            target,
            verification_status,
            affected_tests,
        )

        return VerificationAgentResult(
            target=target.id,
            target_label=target.label,
            verification_status=verification_status,
            checks=checks,
            tests_found=affected_tests,
            affected_tests=affected_tests,
            summary=summary,
        )

    def _find_tests(self, node_id: str):
        tests = []

        for edge in self.graph.edges:
            if edge.type == "tests":
                if edge.source == node_id:
                    test_node = self.nodes.get(edge.target)

                    if test_node:
                        tests.append(test_node)

                elif edge.target == node_id:
                    test_node = self.nodes.get(edge.source)

                    if test_node:
                        tests.append(test_node)

        # Also recognize test nodes by their model type.
        for node in self.graph.nodes:
            if node.type != "test":
                continue

            if node.id == node_id:
                continue

            label = node.label.lower()
            path = (node.path or "").lower()

            if self._looks_like_test(
                label,
                path,
            ):
                if node not in tests:
                    tests.append(node)

        return tests

    def _looks_like_test(
        self,
        label: str,
        path: str,
    ) -> bool:
        test_markers = (
            "test_",
            "_test.",
            ".test.",
            ".spec.",
            "spec_",
            "/tests/",
            "\\tests\\",
        )

        value = f"{label} {path}"

        return any(
            marker in value
            for marker in test_markers
        )

    def _summary(
        self,
        target: CodeNode,
        status: str,
        tests: int,
    ) -> str:
        if status == "ready":
            return (
                f"{target.label} has {tests} test-related "
                "verification candidates."
            )

        if status == "partial":
            return (
                f"{target.label} has limited test coverage "
                f"signals with {tests} candidate test node."
            )

        return (
            f"No test relationship was discovered for "
            f"{target.label}. Additional verification should "
            "be considered before shipping changes."
        )