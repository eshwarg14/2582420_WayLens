from dataclasses import dataclass
from typing import List, Dict, Optional

import networkx as nx

from building_graph import load_graph


TURN_MAPPING = {
    "north": {"north": "straight ahead", "east": "turn right", "west": "turn left", "south": "turn around"},
    "south": {"south": "straight ahead", "west": "turn right", "east": "turn left", "north": "turn around"},
    "east":  {"east":  "straight ahead", "south": "turn right", "north": "turn left", "west":  "turn around"},
    "west":  {"west":  "straight ahead", "north": "turn right", "south": "turn left", "east":  "turn around"},
}


@dataclass
class RouteStep:
    step_index: int
    from_node: str
    to_node: str
    from_label: str
    to_label: str
    absolute_direction: str
    relative_direction: str
    corridor_segment: str
    distance: int
    is_floor_change: bool
    floor_from_name: str
    floor_to_name: str
    nearby_landmark: Optional[str] = None


class Router:
    def __init__(self, graph=None):
        self.graph = graph or load_graph()
        self.undirected_graph = self.graph.to_undirected()

    def get_route(self, from_node: str, to_node: str) -> List[str]:
        if from_node not in self.graph:
            raise ValueError(f"Source node '{from_node}' not in building graph.")
        if to_node not in self.graph:
            raise ValueError(f"Destination node '{to_node}' not in building graph.")

        try:
            return nx.shortest_path(self.undirected_graph, from_node, to_node, weight="distance")
        except nx.NetworkXNoPath:
            raise RuntimeError(f"No valid route found between '{from_node}' and '{to_node}'.")

    def compute_relative_direction(
        self,
        abs_dir: str,
        user_heading: Optional[str] = None,
    ) -> str:
        if abs_dir in ("up", "down"):
            return f"go {abs_dir}"

        if not user_heading or user_heading not in TURN_MAPPING:
            return abs_dir

        return TURN_MAPPING.get(user_heading, {}).get(abs_dir, abs_dir)

    def generate_route_steps(
        self,
        route_nodes: List[str],
        user_heading: Optional[str] = None,
    ) -> List[RouteStep]:
        if len(route_nodes) < 2:
            return []

        steps = []
        for i in range(len(route_nodes) - 1):
            u = route_nodes[i]
            v = route_nodes[i + 1]

            edge_data = self.graph.get_edge_data(u, v) or {}
            abs_dir = edge_data.get("direction", "forward")
            segment = edge_data.get("corridor_segment", "corridor")
            dist = edge_data.get("distance", 1)

            u_info = self.graph.nodes[u]
            v_info = self.graph.nodes[v]

            floor_u_name = u_info.get("floor_name", f"Floor {u_info.get('floor')}")
            floor_v_name = v_info.get("floor_name", f"Floor {v_info.get('floor')}")
            is_floor_change = (u_info.get("floor") != v_info.get("floor"))

            rel_dir = self.compute_relative_direction(abs_dir, user_heading)

            if is_floor_change:
                node_type = u_info.get("type")
                if node_type == "lift":
                    rel_dir = f"take the lift {abs_dir} to {floor_v_name}"
                else:
                    rel_dir = f"take the stairs {abs_dir} to {floor_v_name}"

            nearby = None
            for neighbor in self.graph.neighbors(u):
                if self.graph.nodes[neighbor].get("type") == "landmark" and neighbor != v:
                    nearby = self.graph.nodes[neighbor].get("label", neighbor)
                    break

            step = RouteStep(
                step_index=i + 1,
                from_node=u,
                to_node=v,
                from_label=u_info.get("label", u),
                to_label=v_info.get("label", v),
                absolute_direction=abs_dir,
                relative_direction=rel_dir,
                corridor_segment=segment,
                distance=dist,
                is_floor_change=is_floor_change,
                floor_from_name=floor_u_name,
                floor_to_name=floor_v_name,
                nearby_landmark=nearby,
            )
            steps.append(step)

            if abs_dir in ("north", "south", "east", "west"):
                user_heading = abs_dir

        return steps

    def get_instruction_context(
        self,
        current_node: str,
        destination_node: str,
        user_heading: Optional[str] = None,
    ) -> Dict:
        path = self.get_route(current_node, destination_node)
        steps = self.generate_route_steps(path, user_heading=user_heading)

        if not steps:
            curr_info = self.graph.nodes[current_node]
            return {
                "current_node": current_node,
                "current_label": curr_info.get("label", current_node),
                "destination_node": destination_node,
                "next_node": destination_node,
                "next_label": curr_info.get("label", current_node),
                "relative_direction": "arrived",
                "remaining_steps": 0,
                "floor_name": curr_info.get("floor_name", ""),
                "nearby_landmark": None,
                "note": "You have arrived at your destination.",
            }

        first_step = steps[0]
        remaining = len(steps)

        return {
            "current_node": current_node,
            "current_label": first_step.from_label,
            "destination_node": destination_node,
            "next_node": first_step.to_node,
            "next_label": first_step.to_label,
            "relative_direction": first_step.relative_direction,
            "absolute_direction": first_step.absolute_direction,
            "remaining_steps": remaining,
            "floor_name": first_step.floor_from_name,
            "nearby_landmark": first_step.nearby_landmark,
            "is_floor_change": first_step.is_floor_change,
            "note": f"Heading to {first_step.to_label}" if not first_step.is_floor_change else f"Change floor to {first_step.floor_to_name}",
        }
