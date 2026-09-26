from collections import defaultdict, deque

from app.models.code import (
    CodeGraph,
    CodeNode,
)

from app.models.simulation import (
    SimulationChange,
    SimulationImpactItem,
    SimulationResult,
    SimulationRisk,
    SimulationTest,
    SimulationVerification,
)


class SimulationEngine:
    """
    Simulates the likely repository consequences of a proposed
    change using Ripple's existing code graph.

    This engine is intentionally repository-agnostic.

    It does not contain knowledge of TradePilot, MivaVerse,
    or any specific repository.
    """

    IMPACT_EDGE_TYPES = {
        "imports",
        "calls",
        "references",
        "tests",
        "exposes",
    }

    BREAKING_EDGE_TYPES = {
        "calls",
        "references",
        "exposes",
        "imports",
    }

    def __init__(
        self,
        graph: CodeGraph,
    ):
        self.graph = graph

        self.nodes = {
            node.id: node
            for node in graph.nodes
        }

        self.reverse_edges: dict[
            str,
            list[tuple[str, str, float]],
        ] = defaultdict(list)

        self.forward_edges: dict[
            str,
            list[tuple[str, str, float]],
        ] = defaultdict(list)

        for edge in graph.edges:
            if edge.type not in self.IMPACT_EDGE_TYPES:
                continue

            self.reverse_edges[
                edge.target
            ].append(
                (
                    edge.source,
                    edge.type,
                    edge.confidence,
                )
            )

            self.forward_edges[
                edge.source
            ].append(
                (
                    edge.target,
                    edge.type,
                    edge.confidence,
                )
            )

    # =========================================================
    # MAIN SIMULATION
    # =========================================================

    def simulate(
        self,
        target_id: str,
        change_type: str,
        description: str = "",
    ) -> SimulationResult:

        target = self.nodes.get(target_id)

        if not target:
            raise ValueError(
                "Target node not found."
            )

        if change_type not in {
            "modify",
            "delete",
            "rename",
            "add",
        }:
            raise ValueError(
                "Unsupported change type."
            )

        change = SimulationChange(
            type=change_type,
            target_id=target.id,
            target_label=target.label,
            target_path=target.path,
            description=description,
        )

        affected = self._discover_impact(
            target,
            change_type,
        )

        tests = self._discover_tests(
            target.id,
            affected,
        )

        verification = self._build_verification(
            target,
            change_type,
            affected,
            tests,
        )

        direct_count = sum(
            1
            for item in affected
            if item.impact == "direct"
        )

        indirect_count = sum(
            1
            for item in affected
            if item.impact == "indirect"
        )

        potentially_broken_count = sum(
            1
            for item in affected
            if item.impact == "potentially_broken"
        )

        risk = self._calculate_risk(
            target=target,
            change_type=change_type,
            affected=affected,
            tests=tests,
        )

        summary = self._build_summary(
            target=target,
            change_type=change_type,
            affected=affected,
            tests=tests,
            risk=risk,
        )

        status = (
            "completed"
            if affected or tests
            else "no_impact"
        )

        return SimulationResult(
            status=status,
            change=change,
            risk=risk,
            total_affected=len(affected),
            direct_count=direct_count,
            indirect_count=indirect_count,
            potentially_broken_count=(
                potentially_broken_count
            ),
            affected=affected,
            tests=tests,
            verification=verification,
            summary=summary,
        )

    # =========================================================
    # IMPACT DISCOVERY
    # =========================================================

    def _discover_impact(
        self,
        target: CodeNode,
        change_type: str,
    ) -> list[SimulationImpactItem]:

        results: list[SimulationImpactItem] = []

        visited = {
            target.id
        }

        queue = deque(
            [
                (
                    target.id,
                    0,
                )
            ]
        )

        while queue:

            current_id, depth = queue.popleft()

            relationships = (
                self.reverse_edges.get(
                    current_id,
                    [],
                )
            )

            for (
                dependent_id,
                edge_type,
                edge_confidence,
            ) in relationships:

                if dependent_id in visited:
                    continue

                visited.add(
                    dependent_id
                )

                dependent = self.nodes.get(
                    dependent_id
                )

                if not dependent:
                    continue

                if depth == 0:
                    impact = "direct"
                elif self._could_break(
                    change_type,
                    edge_type,
                ):
                    impact = "potentially_broken"
                else:
                    impact = "indirect"

                confidence = self._impact_confidence(
                    edge_confidence=edge_confidence,
                    depth=depth,
                    change_type=change_type,
                )

                reason = self._build_reason(
                    dependent=dependent,
                    target=target,
                    edge_type=edge_type,
                    impact=impact,
                    change_type=change_type,
                )

                results.append(
                    SimulationImpactItem(
                        node_id=dependent.id,
                        label=dependent.label,
                        path=dependent.path,
                        type=dependent.type,
                        impact=impact,
                        relationship=edge_type,
                        reason=reason,
                        confidence=confidence,
                    )
                )

                queue.append(
                    (
                        dependent_id,
                        depth + 1,
                    )
                )

        return results

    # =========================================================
    # BREAKAGE LOGIC
    # =========================================================

    def _could_break(
        self,
        change_type: str,
        edge_type: str,
    ) -> bool:

        if change_type == "delete":
            return edge_type in {
                "calls",
                "references",
                "imports",
                "exposes",
            }

        if change_type == "rename":
            return edge_type in {
                "calls",
                "references",
                "imports",
                "exposes",
            }

        if change_type == "modify":
            return edge_type in {
                "calls",
                "references",
                "exposes",
            }

        if change_type == "add":
            return False

        return False

    # =========================================================
    # CONFIDENCE
    # =========================================================

    def _impact_confidence(
        self,
        edge_confidence: float,
        depth: int,
        change_type: str,
    ) -> float:

        confidence = edge_confidence

        # Confidence decreases as the relationship becomes
        # further removed from the proposed change.
        confidence -= min(
            depth * 0.08,
            0.32,
        )

        if change_type in {
            "delete",
            "rename",
        }:
            confidence += 0.05

        return round(
            max(
                0.1,
                min(
                    confidence,
                    0.99,
                ),
            ),
            2,
        )

    # =========================================================
    # REASONS
    # =========================================================

    def _build_reason(
        self,
        dependent: CodeNode,
        target: CodeNode,
        edge_type: str,
        impact: str,
        change_type: str,
    ) -> str:

        action = {
            "modify": "modified",
            "delete": "deleted",
            "rename": "renamed",
            "add": "added",
        }.get(
            change_type,
            "changed",
        )

        if edge_type == "imports":
            return (
                f"{dependent.label} imports "
                f"the code that would be {action}. "
                f"The import relationship may need "
                f"to be updated or revalidated."
            )

        if edge_type == "calls":
            return (
                f"{dependent.label} calls "
                f"{target.label}. A {action} change "
                f"could alter the behavior expected "
                f"by this caller."
            )

        if edge_type == "references":
            return (
                f"{dependent.label} references "
                f"{target.label}. The reference should "
                f"be checked after the proposed change."
            )

        if edge_type == "tests":
            return (
                f"{dependent.label} tests behavior "
                f"associated with {target.label}. "
                f"This test should be considered during "
                f"verification."
            )

        if edge_type == "exposes":
            return (
                f"{dependent.label} exposes or depends "
                f"on {target.label}. The exposed contract "
                f"should be revalidated."
            )

        return (
            f"{dependent.label} has a "
            f"{edge_type} relationship with "
            f"{target.label}."
        )

    # =========================================================
    # TEST DISCOVERY
    # =========================================================

    def _discover_tests(
        self,
        target_id: str,
        affected: list[SimulationImpactItem],
    ) -> list[SimulationTest]:

        test_ids: set[str] = set()

        # Direct test relationships.
        for (
            dependent_id,
            edge_type,
            _,
        ) in self.reverse_edges.get(
            target_id,
            [],
        ):

            if edge_type != "tests":
                continue

            test_ids.add(
                dependent_id
            )

        # Tests discovered somewhere in the affected graph.
        for item in affected:

            if item.type == "test":
                test_ids.add(
                    item.node_id
                )

            for (
                dependent_id,
                edge_type,
                _,
            ) in self.reverse_edges.get(
                item.node_id,
                [],
            ):

                if edge_type == "tests":
                    test_ids.add(
                        dependent_id
                    )

        results: list[SimulationTest] = []

        for test_id in test_ids:

            test = self.nodes.get(
                test_id
            )

            if not test:
                continue

            results.append(
                SimulationTest(
                    node_id=test.id,
                    label=test.label,
                    path=test.path,
                    reason=(
                        f"{test.label} is connected to "
                        f"the affected code and should "
                        f"be rerun during verification."
                    ),
                    confidence=0.9,
                )
            )

        return results

    # =========================================================
    # RISK
    # =========================================================

    def _calculate_risk(
        self,
        target: CodeNode,
        change_type: str,
        affected: list[SimulationImpactItem],
        tests: list[SimulationTest],
    ) -> SimulationRisk:

        score = 0.0

        direct = sum(
            1
            for item in affected
            if item.impact == "direct"
        )

        indirect = sum(
            1
            for item in affected
            if item.impact == "indirect"
        )

        potentially_broken = sum(
            1
            for item in affected
            if item.impact
            == "potentially_broken"
        )

        score += min(
            direct * 7,
            28,
        )

        score += min(
            indirect * 2,
            16,
        )

        score += min(
            potentially_broken * 10,
            35,
        )

        score += min(
            len(tests) * 3,
            12,
        )

        if target.type in {
            "api",
            "class",
        }:
            score += 8

        if target.type == "function":
            score += 3

        if change_type == "delete":
            score += 12

        elif change_type == "rename":
            score += 8

        elif change_type == "modify":
            score += 3

        score = int(
            max(
                0,
                min(
                    score,
                    100,
                ),
            )
        )

        if score >= 75:
            level = "critical"

        elif score >= 50:
            level = "high"

        elif score >= 25:
            level = "medium"

        else:
            level = "low"

        if affected:
            average_confidence = (
                sum(
                    item.confidence
                    for item in affected
                )
                / len(affected)
            )
        else:
            average_confidence = 0.8

        return SimulationRisk(
            level=level,
            score=score,
            confidence=round(
                average_confidence,
                2,
            ),
        )

    # =========================================================
    # VERIFICATION
    # =========================================================

    def _build_verification(
        self,
        target: CodeNode,
        change_type: str,
        affected: list[SimulationImpactItem],
        tests: list[SimulationTest],
    ) -> list[SimulationVerification]:

        verification: list[
            SimulationVerification
        ] = []

        if tests:
            verification.append(
                SimulationVerification(
                    title="Run affected tests",
                    description=(
                        f"Run the {len(tests)} "
                        f"test relationship(s) identified "
                        f"by Ripple."
                    ),
                    priority="high",
                )
            )

        if any(
            item.impact
            == "potentially_broken"
            for item in affected
        ):
            verification.append(
                SimulationVerification(
                    title="Validate dependent behavior",
                    description=(
                        "Check callers, references, "
                        "imports, and exposed contracts "
                        "that may depend on the changed code."
                    ),
                    priority="high",
                )
            )

        if change_type == "rename":
            verification.append(
                SimulationVerification(
                    title="Search for stale references",
                    description=(
                        "Verify that no unresolved references "
                        "to the previous name remain."
                    ),
                    priority="high",
                )
            )

        if change_type == "delete":
            verification.append(
                SimulationVerification(
                    title="Confirm safe removal",
                    description=(
                        "Verify that the deleted code is not "
                        "still required by callers, imports, "
                        "references, or exposed interfaces."
                    ),
                    priority="high",
                )
            )

        if change_type == "modify":
            verification.append(
                SimulationVerification(
                    title="Validate changed behavior",
                    description=(
                        f"Verify that behavior associated "
                        f"with {target.label} still satisfies "
                        f"its affected callers and tests."
                    ),
                    priority="medium",
                )
            )

        if not affected and not tests:
            verification.append(
                SimulationVerification(
                    title="Perform targeted validation",
                    description=(
                        "No graph relationships were discovered. "
                        "Perform a focused review of the proposed "
                        "change and run relevant repository tests "
                        "if available."
                    ),
                    priority="low",
                )
            )

        return verification

    # =========================================================
    # SUMMARY
    # =========================================================

    def _build_summary(
        self,
        target: CodeNode,
        change_type: str,
        affected: list[SimulationImpactItem],
        tests: list[SimulationTest],
        risk: SimulationRisk,
    ) -> str:

        direct = sum(
            1
            for item in affected
            if item.impact == "direct"
        )

        indirect = sum(
            1
            for item in affected
            if item.impact == "indirect"
        )

        broken = sum(
            1
            for item in affected
            if item.impact
            == "potentially_broken"
        )

        action = {
            "modify": "modify",
            "delete": "delete",
            "rename": "rename",
            "add": "add",
        }.get(
            change_type,
            "change",
        )

        if not affected and not tests:
            return (
                f"Ripple found no graph-connected impact "
                f"for the proposed {action} of "
                f"{target.label}. "
                f"Confidence is based on the relationships "
                f"currently discovered in the repository."
            )

        return (
            f"A proposed {action} of {target.label} "
            f"could affect {len(affected)} connected "
            f"nodes: {direct} direct, "
            f"{indirect} indirect, and "
            f"{broken} potentially broken. "
            f"Ripple identified {len(tests)} test "
            f"relationship(s) for verification. "
            f"Estimated risk is {risk.level} "
            f"({risk.score}/100) with "
            f"{int(risk.confidence * 100)}% "
            f"relationship confidence."
        )