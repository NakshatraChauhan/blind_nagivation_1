from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.routing_algorithm import AStarRouter, GraphNode

Coordinate = Tuple[float, float]


@dataclass
class RouteInstruction:
    text: str
    waypoint: Coordinate


class OfflineNavigationEngine:
    """Loads OSM XML and provides route + turn-by-turn hints."""

    def __init__(self, osm_file: Path):
        self.osm_file = osm_file
        self.nodes: Dict[int, GraphNode] = {}
        self.edges: Dict[int, List[int]] = {}
        self.router: Optional[AStarRouter] = None

    def load_map(self) -> None:
        tree = ET.parse(self.osm_file)
        root = tree.getroot()

        for node in root.findall("node"):
            node_id = int(node.attrib["id"])
            self.nodes[node_id] = GraphNode(
                node_id=node_id,
                lat=float(node.attrib["lat"]),
                lon=float(node.attrib["lon"]),
            )

        for way in root.findall("way"):
            tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
            if "highway" not in tags:
                continue
            refs = [int(nd.attrib["ref"]) for nd in way.findall("nd") if int(nd.attrib["ref"]) in self.nodes]
            for i in range(len(refs) - 1):
                a = refs[i]
                b = refs[i + 1]
                self.edges.setdefault(a, []).append(b)
                self.edges.setdefault(b, []).append(a)

        self.router = AStarRouter(self.nodes, self.edges)

    @staticmethod
    def _distance(a: Coordinate, b: Coordinate) -> float:
        return AStarRouter.haversine(a, b)

    def nearest_node(self, point: Coordinate) -> Optional[int]:
        if not self.nodes:
            return None
        return min(
            self.nodes.keys(),
            key=lambda n_id: self._distance(point, (self.nodes[n_id].lat, self.nodes[n_id].lon)),
        )

    def build_route(self, start: Coordinate, destination: Coordinate) -> List[GraphNode]:
        if not self.router:
            raise RuntimeError("Map not loaded. Call load_map first.")

        start_node = self.nearest_node(start)
        dest_node = self.nearest_node(destination)
        if start_node is None or dest_node is None:
            return []

        return self.router.shortest_path(start_node, dest_node)

    def build_turn_by_turn(self, path: List[GraphNode]) -> List[RouteInstruction]:
        if len(path) < 3:
            return [RouteInstruction("Proceed to destination", (n.lat, n.lon)) for n in path]

        instructions: List[RouteInstruction] = [
            RouteInstruction("Route started. Walk straight.", (path[0].lat, path[0].lon))
        ]

        for i in range(1, len(path) - 1):
            prev_n = path[i - 1]
            curr_n = path[i]
            next_n = path[i + 1]
            turn = self._turn_direction(prev_n, curr_n, next_n)
            if turn == "straight":
                text = "Continue straight"
            elif turn == "left":
                text = "Intersection ahead. Turn left"
            else:
                text = "Intersection ahead. Turn right"
            instructions.append(RouteInstruction(text, (curr_n.lat, curr_n.lon)))

        instructions.append(
            RouteInstruction("You have reached your destination.", (path[-1].lat, path[-1].lon))
        )
        return instructions

    @staticmethod
    def _turn_direction(a: GraphNode, b: GraphNode, c: GraphNode) -> str:
        ab = (b.lon - a.lon, b.lat - a.lat)
        bc = (c.lon - b.lon, c.lat - b.lat)
        cross = ab[0] * bc[1] - ab[1] * bc[0]
        angle = math.degrees(math.atan2(abs(cross), ab[0] * bc[0] + ab[1] * bc[1] + 1e-9))
        if angle < 20:
            return "straight"
        return "left" if cross > 0 else "right"
