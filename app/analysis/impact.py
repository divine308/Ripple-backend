# from collections import defaultdict, deque

# from app.models.code import (
#     CodeGraph,
#     CodeNode,
#     ImpactAnalysis,
#     ImpactItem,
# )


# class ImpactEngine:
#     def __init__(self, graph: CodeGraph):
#         self.graph = graph

#         self.reverse_edges: dict[str, list[tuple[str, str]]] = defaultdict(list)

#         for edge in graph.edges:
#             self.reverse_edges[edge.target].append(
#                 (edge.source, edge.type)
#             )

#         self.nodes = {
#             node.id: node
#             for node in graph.nodes
#         }

#     def analyze(self, target_id: str) -> ImpactAnalysis:
#         target = self.nodes.get(target_id)

#         if not target:
#             raise ValueError("Target node not found.")

#         direct: list[ImpactItem] = []
#         indirect: list[ImpactItem] = []

#         visited = {target_id}

#         queue = deque(
#             [
#                 (target_id, 0)
#             ]
#         )

#         while queue:
#             current, depth = queue.popleft()

#             for dependent_id, edge_type in self.reverse_edges.get(
#                 current,
#                 [],
#             ):
#                 if dependent_id in visited:
#                     continue

#                 visited.add(dependent_id)

#                 dependent = self.nodes.get(dependent_id)

#                 if not dependent:
#                     continue

#                 impact = "direct" if depth == 0 else "indirect"

#                 reason = self._reason(
#                     dependent,
#                     target,
#                     edge_type,
#                     impact,
#                 )

#                 item = ImpactItem(
#                     node_id=dependent.id,
#                     label=dependent.label,
#                     path=dependent.path,
#                     type=dependent.type,
#                     impact=impact,
#                     reason=reason,
#                     confidence=0.9 if impact == "direct" else 0.75,
#                 )

#                 if impact == "direct":
#                     direct.append(item)
#                 else:
#                     indirect.append(item)

#                 queue.append(
#                     (dependent_id, depth + 1)
#                 )

#         affected = direct + indirect

#         risk = self._calculate_risk(
#             target,
#             len(direct),
#             len(indirect),
#         )

#         summary = self._summary(
#             target,
#             len(affected),
#             len(direct),
#             len(indirect),
#             risk,
#         )

#         return ImpactAnalysis(
#             target=target,
#             total_affected=len(affected),
#             direct_count=len(direct),
#             indirect_count=len(indirect),
#             potential_count=0,
#             risk=risk,
#             summary=summary,
#             affected=affected,
#         )

#     def _reason(
#         self,
#         dependent: CodeNode,
#         target: CodeNode,
#         edge_type: str,
#         impact: str,
#     ) -> str:
#         if edge_type == "imports":
#             return (
#                 f"{dependent.label} imports the file containing "
#                 f"{target.label}."
#             )

#         if edge_type == "contains":
#             return (
#                 f"{dependent.label} is structurally connected "
#                 f"to the changed code."
#             )

#         if edge_type == "tests":
#             return (
#                 f"{dependent.label} tests behavior associated "
#                 f"with {target.label}."
#             )

#         return (
#             f"{dependent.label} has a {edge_type} relationship "
#             f"with {target.label}."
#         )

#     def _calculate_risk(
#         self,
#         target: CodeNode,
#         direct: int,
#         indirect: int,
#     ):
#         score = 0

#         score += min(direct * 2, 10)
#         score += min(indirect, 10)

#         if target.type in {"api", "class"}:
#             score += 3

#         if score >= 18:
#             return "critical"

#         if score >= 12:
#             return "high"

#         if score >= 6:
#             return "medium"

#         return "low"

#     def _summary(
#         self,
#         target: CodeNode,
#         total: int,
#         direct: int,
#         indirect: int,
#         risk: str,
#     ) -> str:
#         if total == 0:
#             return (
#                 f"No downstream dependencies were discovered for "
#                 f"{target.label}."
#             )

#         return (
#             f"{target.label} has {total} potentially affected "
#             f"connections: {direct} direct and {indirect} indirect. "
#             f"Current estimated impact level is {risk}."
#         )


from collections import defaultdict, deque

from app.models.code import (
    CodeGraph,
    CodeNode,
    ImpactAnalysis,
    ImpactItem,
)


class ImpactEngine:
    IMPACT_EDGE_TYPES = {
        "imports",
        "calls",
        "references",
        "tests",
        "exposes",
    }

    def __init__(self, graph: CodeGraph):
        self.graph = graph

        self.reverse_edges: dict[
            str,
            list[tuple[str, str]],
        ] = defaultdict(list)

        for edge in graph.edges:
            if edge.type not in self.IMPACT_EDGE_TYPES:
                continue

            self.reverse_edges[edge.target].append(
                (edge.source, edge.type)
            )

        self.nodes = {
            node.id: node
            for node in graph.nodes
        }

    def analyze(self, target_id: str) -> ImpactAnalysis:
        target = self.nodes.get(target_id)

        if not target:
            raise ValueError("Target node not found.")

        direct: list[ImpactItem] = []
        indirect: list[ImpactItem] = []

        visited = {target_id}

        queue = deque(
            [
                (target_id, 0)
            ]
        )

        while queue:
            current, depth = queue.popleft()

            for dependent_id, edge_type in self.reverse_edges.get(
                current,
                [],
            ):
                if dependent_id in visited:
                    continue

                visited.add(dependent_id)

                dependent = self.nodes.get(dependent_id)

                if not dependent:
                    continue

                impact = (
                    "direct"
                    if depth == 0
                    else "indirect"
                )

                reason = self._reason(
                    dependent,
                    target,
                    edge_type,
                    impact,
                )

                item = ImpactItem(
                    node_id=dependent.id,
                    label=dependent.label,
                    path=dependent.path,
                    type=dependent.type,
                    impact=impact,
                    reason=reason,
                    confidence=(
                        0.9
                        if impact == "direct"
                        else 0.75
                    ),
                )

                if impact == "direct":
                    direct.append(item)
                else:
                    indirect.append(item)

                queue.append(
                    (
                        dependent_id,
                        depth + 1,
                    )
                )

        affected = direct + indirect

        risk = self._calculate_risk(
            target,
            len(direct),
            len(indirect),
        )

        summary = self._summary(
            target,
            len(affected),
            len(direct),
            len(indirect),
            risk,
        )

        return ImpactAnalysis(
            target=target,
            total_affected=len(affected),
            direct_count=len(direct),
            indirect_count=len(indirect),
            potential_count=0,
            risk=risk,
            summary=summary,
            affected=affected,
        )

    def _reason(
        self,
        dependent: CodeNode,
        target: CodeNode,
        edge_type: str,
        impact: str,
    ) -> str:
        if edge_type == "imports":
            return (
                f"{dependent.label} imports the file containing "
                f"{target.label}."
            )

        if edge_type == "calls":
            return (
                f"{dependent.label} calls or depends on "
                f"{target.label}."
            )

        if edge_type == "references":
            return (
                f"{dependent.label} references "
                f"{target.label}."
            )

        if edge_type == "tests":
            return (
                f"{dependent.label} tests behavior associated "
                f"with {target.label}."
            )

        if edge_type == "exposes":
            return (
                f"{dependent.label} exposes or depends on "
                f"{target.label}."
            )

        if edge_type == "contains":
            return (
                f"{dependent.label} is structurally connected "
                f"to the changed code."
            )

        return (
            f"{dependent.label} has a {edge_type} relationship "
            f"with {target.label}."
        )

    def _calculate_risk(
        self,
        target: CodeNode,
        direct: int,
        indirect: int,
    ):
        score = 0

        score += min(direct * 2, 10)
        score += min(indirect, 10)

        if target.type in {"api", "class"}:
            score += 3

        if score >= 18:
            return "critical"

        if score >= 12:
            return "high"

        if score >= 6:
            return "medium"

        return "low"

    def _summary(
        self,
        target: CodeNode,
        total: int,
        direct: int,
        indirect: int,
        risk: str,
    ) -> str:
        if total == 0:
            return (
                f"No downstream dependencies were discovered for "
                f"{target.label}."
            )

        return (
            f"{target.label} has {total} potentially affected "
            f"connections: {direct} direct and {indirect} indirect. "
            f"Current estimated impact level is {risk}."
        )