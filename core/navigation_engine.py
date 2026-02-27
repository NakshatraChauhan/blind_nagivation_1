from __future__ import annotations

import math
import threading
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from core.routing_algorithm import AStarRouter, GraphNode

Coordinate = Tuple[float, float]


@dataclass(frozen=True)
class RouteInstruction:
    text: str
    waypoint: Coordinate


class OfflineNavigationEngine:
    """Offline OSM navigation manager with pause/resume-aware instruction flow."""

    def __init__(self, osm_file: Path):
        self.osm_file = osm_file
        self.nodes: Dict[int, GraphNode] = {}
        self.edges: Dict[int, List[int]] = {}
        self.router: Optional[AStarRouter] = None

        self._instructions: List[RouteInstruction] = []
        self._instruction_index = 0
        self._paused = False
        self._state_lock = threading.Lock()

    def load_map(self) -> None:
        tree = ET.parse(self.osm_file)
        root = tree.getroot()

        for node in root.findall("node"):
            node_id = int(node.attrib["id"])
            self.nodes[node_id] = GraphNode(node_id=node_id, lat=float(node.attrib["lat"]), lon=float(node.attrib["lon"]))

        for way in root.findall("way"):
            tags = {tag.attrib["k"]: tag.attrib["v"] for tag in way.findall("tag")}
            if "highway" not in tags:
                continue

            refs = [int(nd.attrib["ref"]) for nd in way.findall("nd") if int(nd.attrib["ref"]) in self.nodes]
            for i in range(len(refs) - 1):
                a, b = refs[i], refs[i + 1]
                self.edges.setdefault(a, []).append(b)
                self.edges.setdefault(b, []).append(a)

        self.router = AStarRouter(self.nodes, self.edges)

    @staticmethod
    def distance_m(a: Coordinate, b: Coordinate) -> float:
        return AStarRouter.haversine(a, b)

    def nearest_node(self, point: Coordinate) -> Optional[int]:
        if not self.nodes:
            return None
        return min(self.nodes, key=lambda n_id: self.distance_m(point, (self.nodes[n_id].lat, self.nodes[n_id].lon)))

    def build_route(self, start: Coordinate, destination: Coordinate) -> List[GraphNode]:
        if not self.router:
            raise RuntimeError("Map not loaded. Call load_map() first.")

        start_node = self.nearest_node(start)
        destination_node = self.nearest_node(destination)
        if start_node is None or destination_node is None:
            return []
        return self.router.shortest_path(start_node, destination_node)

    def start_guidance(self, path: List[GraphNode]) -> None:
        with self._state_lock:
            self._instructions = self.build_turn_by_turn(path)
            self._instruction_index = 0

    def pause(self) -> None:
        with self._state_lock:
            self._paused = True

    def resume(self) -> None:
        with self._state_lock:
            self._paused = False

    def next_instruction(self, current_location: Coordinate, trigger_distance_m: float = 8.0) -> Optional[str]:
        with self._state_lock:
            if self._paused or self._instruction_index >= len(self._instructions):
                return None

            current = self._instructions[self._instruction_index]
            if self.distance_m(current_location, current.waypoint) > trigger_distance_m:
                return None

            self._instruction_index += 1
            return current.text

    def build_turn_by_turn(self, path: List[GraphNode]) -> List[RouteInstruction]:
        if not path:
            return []
        if len(path) < 3:
            return [RouteInstruction("Proceed to destination", (n.lat, n.lon)) for n in path]

        instructions: List[RouteInstruction] = [RouteInstruction("Route started. Walk straight.", (path[0].lat, path[0].lon))]
        for i in range(1, len(path) - 1):
            prev_n, cur_n, next_n = path[i - 1], path[i], path[i + 1]
            turn = self._turn_direction(prev_n, cur_n, next_n)
            if turn == "left":
                text = "Intersection ahead. Turn left"
            elif turn == "right":
                text = "Intersection ahead. Turn right"
            else:
                text = "Continue straight"
            instructions.append(RouteInstruction(text, (cur_n.lat, cur_n.lon)))

        instructions.append(RouteInstruction("You have reached your destination.", (path[-1].lat, path[-1].lon)))
        return instructions

    @staticmethod
    def _turn_direction(a: GraphNode, b: GraphNode, c: GraphNode) -> str:
        ab = (b.lon - a.lon, b.lat - a.lat)
        bc = (c.lon - b.lon, c.lat - b.lat)
        cross = (ab[0] * bc[1]) - (ab[1] * bc[0])
        angle = math.degrees(math.atan2(abs(cross), (ab[0] * bc[0]) + (ab[1] * bc[1]) + 1e-9))
        if angle < 20:
            return "straight"
        return "left" if cross > 0 else "right"
