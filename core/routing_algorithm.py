from __future__ import annotations

import heapq
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

NodeId = int
Coordinate = Tuple[float, float]


@dataclass(frozen=True)
class GraphNode:
    node_id: NodeId
    lat: float
    lon: float


class AStarRouter:
    """A* routing on an in-memory graph built from OSM data."""

    def __init__(self, nodes: Dict[NodeId, GraphNode], edges: Dict[NodeId, List[NodeId]]):
        self.nodes = nodes
        self.edges = edges

    @staticmethod
    def haversine(a: Coordinate, b: Coordinate) -> float:
        """Distance in meters."""
        lat1, lon1 = map(math.radians, a)
        lat2, lon2 = map(math.radians, b)
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        h = (
            math.sin(dlat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
        )
        return 2 * 6371000 * math.asin(math.sqrt(h))

    def shortest_path(self, start_id: NodeId, goal_id: NodeId) -> List[GraphNode]:
        if start_id not in self.nodes or goal_id not in self.nodes:
            return []

        open_heap: List[Tuple[float, NodeId]] = []
        heapq.heappush(open_heap, (0.0, start_id))

        came_from: Dict[NodeId, Optional[NodeId]] = {start_id: None}
        g_score: Dict[NodeId, float] = {start_id: 0.0}

        goal = self.nodes[goal_id]

        while open_heap:
            _, current = heapq.heappop(open_heap)
            if current == goal_id:
                break

            current_node = self.nodes[current]
            for neighbor in self.edges.get(current, []):
                neighbor_node = self.nodes[neighbor]
                tentative = g_score[current] + self.haversine(
                    (current_node.lat, current_node.lon),
                    (neighbor_node.lat, neighbor_node.lon),
                )
                if tentative < g_score.get(neighbor, float("inf")):
                    came_from[neighbor] = current
                    g_score[neighbor] = tentative
                    heuristic = self.haversine(
                        (neighbor_node.lat, neighbor_node.lon),
                        (goal.lat, goal.lon),
                    )
                    heapq.heappush(open_heap, (tentative + heuristic, neighbor))

        if goal_id not in came_from:
            return []

        path = []
        cursor: Optional[NodeId] = goal_id
        while cursor is not None:
            path.append(self.nodes[cursor])
            cursor = came_from.get(cursor)
        path.reverse()
        return path
