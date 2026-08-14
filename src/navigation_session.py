from typing import Dict, Tuple, Optional, Union
from PIL import Image

from building_graph import load_graph, get_all_room_ids, get_node_info
from intent_parser import parse_destination
from localization import localize
from state_tracker import DirectionalStateTracker, NavigationSession
from routing import Router
from llm_instructor import generate_instruction


class NavigationOrchestrator:
    def __init__(self, graph=None):
        self.graph = graph or load_graph()
        self.valid_rooms = get_all_room_ids(self.graph)
        self.tracker = DirectionalStateTracker(self.graph)
        self.router = Router(self.graph)

    def start_session(self, destination_text: str) -> Tuple[Optional[NavigationSession], Dict]:
        node_id, conf, parse_msg = parse_destination(destination_text, self.valid_rooms, self.graph)

        if not node_id:
            return None, {
                "status": "error",
                "message": parse_msg,
                "instruction": parse_msg,
                "session_id": None,
            }

        session = self.tracker.create_session(node_id)
        node_info = get_node_info(self.graph, node_id) or {}
        dest_label = node_info.get("label", node_id)
        floor_name = node_info.get("floor_name", "")

        welcome_msg = f"Destination set to {dest_label} on {floor_name}. Please point your camera and scan your surroundings."

        return session, {
            "status": "active",
            "destination_node": node_id,
            "destination_label": dest_label,
            "floor_name": floor_name,
            "message": welcome_msg,
            "instruction": welcome_msg,
            "session_id": session.session_id,
        }

    def process_scan(
        self,
        session: NavigationSession,
        image_input: Union[str, Image.Image],
    ) -> Dict:
        if session.status == "arrived":
            return {
                "status": "arrived",
                "current_node": session.current_node,
                "instruction": "You have already arrived at your destination.",
                "session_id": session.session_id,
            }

        curr_node, loc_conf, loc_method, loc_msg = localize(image_input, self.valid_rooms, self.graph)

        if curr_node == "rescan":
            return {
                "status": "rescan_needed",
                "current_node": None,
                "instruction": loc_msg,
                "method": loc_method,
                "session_id": session.session_id,
            }

        expected_route = None
        if session.current_node:
            try:
                expected_route = self.router.get_route(session.current_node, session.destination_node)
            except Exception:
                pass

        session, state_msg = self.tracker.update_position(
            session,
            curr_node,
            confidence=loc_conf,
            expected_route=expected_route,
        )

        if session.status == "arrived":
            dest_info = get_node_info(self.graph, session.destination_node) or {}
            dest_label = dest_info.get("label", session.destination_node)
            arrival_text = f"You have arrived at {dest_label}! Destination reached."
            session.last_instruction_given = arrival_text

            return {
                "status": "arrived",
                "current_node": curr_node,
                "current_label": dest_label,
                "instruction": arrival_text,
                "session_id": session.session_id,
            }

        context = self.router.get_instruction_context(
            current_node=curr_node,
            destination_node=session.destination_node,
            user_heading=session.inferred_direction,
        )

        try:
            route_path = [str(n) for n in self.router.get_route(curr_node, session.destination_node)]
        except Exception:
            route_path = []

        instruction_text, gen_method = generate_instruction(context)
        is_new = self.tracker.should_emit_instruction(session, instruction_text)

        return {
            "status": "active",
            "current_node": curr_node,
            "current_label": context.get("current_label"),
            "destination_node": session.destination_node,
            "next_node": context.get("next_node"),
            "instruction": instruction_text,
            "is_new_instruction": is_new,
            "movement_state": session.movement_state,
            "remaining_steps": context.get("remaining_steps"),
            "localization_method": loc_method,
            "instruction_method": gen_method,
            "session_id": session.session_id,
            "route_path": route_path,
        }
