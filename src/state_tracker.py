import uuid
from dataclasses import dataclass, field
from typing import Optional, List, Tuple

from building_graph import load_graph


@dataclass
class NavigationSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    destination_node: str = ""
    current_node: Optional[str] = None
    last_node: Optional[str] = None
    inferred_direction: Optional[str] = None
    confidence_state: float = 1.0
    last_instruction_given: str = ""
    path_history: List[str] = field(default_factory=list)
    status: str = "active"
    movement_state: str = "starting"


class DirectionalStateTracker:
    def __init__(self, graph=None):
        self.graph = graph or load_graph()

    def create_session(self, destination_node: str) -> NavigationSession:
        return NavigationSession(destination_node=destination_node)

    def update_position(
        self,
        session: NavigationSession,
        detected_node: str,
        confidence: float = 1.0,
        expected_route: Optional[List[str]] = None,
    ) -> Tuple[NavigationSession, str]:
        session.confidence_state = confidence

        if detected_node == session.destination_node:
            session.last_node = session.current_node
            session.current_node = detected_node
            session.path_history.append(detected_node)
            session.status = "arrived"
            session.movement_state = "arrived"
            return session, "ARRIVED: Reached target destination!"

        if session.current_node is None:
            session.current_node = detected_node
            session.path_history.append(detected_node)
            session.movement_state = "starting"
            return session, f"INITIALIZED: Located at {detected_node}"

        if detected_node == session.current_node:
            return session, f"STATIONARY: Still at {detected_node}"

        last_pos = session.current_node
        new_pos = detected_node

        edge_data = self.graph.get_edge_data(last_pos, new_pos)

        if edge_data:
            move_dir = edge_data.get("direction")
            session.inferred_direction = move_dir
            session.last_node = last_pos
            session.current_node = new_pos
            session.path_history.append(new_pos)

            if len(session.path_history) >= 3 and new_pos == session.path_history[-3]:
                session.movement_state = "backtracking"
                return session, f"BACKTRACKING: Turned around to {new_pos} (heading {move_dir})"

            node_type = self.graph.nodes[new_pos].get("type")
            if node_type in ("lift", "steps", "gate"):
                session.movement_state = "reanchoring"
                return session, f"REANCHORING: Reached transition point {new_pos} ({node_type})"

            if expected_route and len(expected_route) > 1:
                expected_next = expected_route[1] if expected_route[0] == last_pos else None
                if expected_next and new_pos != expected_next:
                    session.movement_state = "wrong_way"
                    return session, f"WRONG_WAY: Moved to {new_pos} instead of expected {expected_next}"

            session.movement_state = "forward"
            return session, f"FORWARD: Moved from {last_pos} -> {new_pos} (heading {move_dir})"

        else:
            session.last_node = last_pos
            session.current_node = new_pos
            session.path_history.append(new_pos)
            session.movement_state = "reanchoring"
            return session, f"REANCHORING: Jumped location from {last_pos} -> {new_pos}"

    def should_emit_instruction(self, session: NavigationSession, new_instruction: str) -> bool:
        if not new_instruction:
            return False
        if new_instruction.strip() == session.last_instruction_given.strip():
            return False
        session.last_instruction_given = new_instruction.strip()
        return True
