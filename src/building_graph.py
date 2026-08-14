"""
WayLens : Building Knowledge Graph
Step 1: Digitize floor plans into a directional room-adjacency graph.

Built from MAP.pdf analysis:
  - Page 1: Ground Floor  (5xx rooms: 501-527 + landmarks)
  - Page 2: Second Floor   (6xx rooms: 601-627 + landmarks)
  - Page 3: Third Floor    (7xx rooms: 701-755 + landmarks, inferred from dataset)

The graph is a networkx DiGraph where:
  - Nodes represent rooms, landmarks, lifts, steps, gates, toilets
  - Edges carry direction metadata per corridor segment
  - Cross-floor edges connect via lifts and steps
"""

import json
import sys
from pathlib import Path
from typing import Optional

import networkx as nx


# ─── Direction helpers ──────────────────────────────────────────────

OPPOSITE_DIR = {
    "north": "south",
    "south": "north",
    "east": "west",
    "west": "east",
    "up": "down",
    "down": "up",
}

FLOOR_NAMES = {
    5: "Ground Floor",
    6: "First Floor",
    7: "Second Floor",
}


def _add_bidir_edge(edges_list, a, b, direction, corridor_segment, distance=1):
    """Add a pair of directed edges (A→B and B→A) with opposite directions."""
    edges_list.append({
        "from": a, "to": b,
        "direction": direction,
        "corridor_segment": corridor_segment,
        "distance": distance,
    })
    edges_list.append({
        "from": b, "to": a,
        "direction": OPPOSITE_DIR[direction],
        "corridor_segment": corridor_segment,
        "distance": distance,
    })


#  FLOOR 5  :  from MAP.pdf Page 1
FLOOR_5_NODES = [
    # ── South corridor rooms ──
    {"id": "501", "type": "room", "floor": 5, "label": "Room 501",
     "aliases": ["501", "five oh one", "five zero one"], "corridor": "5_south"},
    {"id": "502", "type": "room", "floor": 5, "label": "Room 502",
     "aliases": ["502", "five oh two", "five zero two"], "corridor": "5_south"},
    {"id": "503", "type": "room", "floor": 5, "label": "Room 503",
     "aliases": ["503", "five oh three", "five zero three"], "corridor": "5_south"},
    {"id": "504", "type": "room", "floor": 5, "label": "Room 504",
     "aliases": ["504", "five oh four", "five zero four"], "corridor": "5_south"},

    # ── East wing rooms (north→south on map = top→bottom) ──
    {"id": "505", "type": "room", "floor": 5, "label": "Room 505",
     "aliases": ["505", "five oh five", "five zero five"], "corridor": "5_east"},
    {"id": "506", "type": "room", "floor": 5, "label": "Room 506",
     "aliases": ["506", "five oh six", "five zero six"], "corridor": "5_east"},
    {"id": "507", "type": "room", "floor": 5, "label": "Room 507",
     "aliases": ["507", "five oh seven", "five zero seven"], "corridor": "5_east"},
    {"id": "507A", "type": "room", "floor": 5, "label": "Room 507A",
     "aliases": ["507A", "five oh seven A", "five zero seven A"], "corridor": "5_east"},

    # ── West wing rooms (south→north on map = bottom→top) ──
    {"id": "513", "type": "room", "floor": 5, "label": "Room 513",
     "aliases": ["513", "five thirteen"], "corridor": "5_west"},
    {"id": "514", "type": "room", "floor": 5, "label": "Room 514",
     "aliases": ["514", "five fourteen"], "corridor": "5_west"},
    {"id": "515", "type": "room", "floor": 5, "label": "Room 515",
     "aliases": ["515", "five fifteen"], "corridor": "5_west"},
    {"id": "516", "type": "room", "floor": 5, "label": "Room 516",
     "aliases": ["516", "five sixteen"], "corridor": "5_west"},
    {"id": "517", "type": "room", "floor": 5, "label": "Room 517",
     "aliases": ["517", "five seventeen"], "corridor": "5_west"},
    {"id": "518", "type": "room", "floor": 5, "label": "Room 518",
     "aliases": ["518", "five eighteen"], "corridor": "5_west"},
    {"id": "521", "type": "room", "floor": 5, "label": "Room 521",
     "aliases": ["521", "five twenty one"], "corridor": "5_west"},
    {"id": "522", "type": "room", "floor": 5, "label": "Room 522",
     "aliases": ["522", "five twenty two"], "corridor": "5_west"},

    # ── North corridor rooms ──
    {"id": "523", "type": "room", "floor": 5, "label": "Room 523",
     "aliases": ["523", "five twenty three"], "corridor": "5_inner_north"},
    {"id": "524", "type": "room", "floor": 5, "label": "Room 524",
     "aliases": ["524", "five twenty four"], "corridor": "5_inner_north"},
    {"id": "526", "type": "room", "floor": 5, "label": "Room 526",
     "aliases": ["526", "five twenty six"], "corridor": "5_north"},
    {"id": "527", "type": "room", "floor": 5, "label": "Room 527",
     "aliases": ["527", "five twenty seven"], "corridor": "5_north"},

    # ── Landmarks ──
    {"id": "Hall_5", "type": "landmark", "floor": 5, "label": "Hall",
     "aliases": ["hall", "main hall"], "corridor": "5_north"},
    {"id": "Seminar_Hall", "type": "landmark", "floor": 5, "label": "Seminar Hall",
     "aliases": ["seminar hall", "seminar"], "corridor": "5_north"},
    {"id": "Dept_of_Commerce", "type": "landmark", "floor": 5,
     "label": "Department of Commerce",
     "aliases": ["department of commerce", "dept of commerce",
                 "commerce department", "dean school of commerce",
                 "Dean_School_of_Commerce"],
     "corridor": "5_north"},
    {"id": "Physics_Lab", "type": "landmark", "floor": 5, "label": "Physics Lab",
     "aliases": ["physics lab", "physics laboratory"], "corridor": "5_south_west"},
    {"id": "Xerox_5", "type": "landmark", "floor": 5, "label": "Xerox",
     "aliases": ["xerox", "photocopy", "copy center"], "corridor": "5_south_west"},
    {"id": "Panel_Room", "type": "landmark", "floor": 5, "label": "Panel Room",
     "aliases": ["panel room", "panel"], "corridor": "5_north"},
    {"id": "Water_5", "type": "landmark", "floor": 5, "label": "Water Cooler (F5)",
     "aliases": ["water", "water cooler", "drinking water"], "corridor": "5_north"},

    # ── Infrastructure ──
    {"id": "Lift_5NE", "type": "lift", "floor": 5, "label": "Lift (NE, Floor 5)",
     "aliases": ["lift", "elevator"], "corridor": "5_north"},
    {"id": "Lift_5C", "type": "lift", "floor": 5, "label": "Lift (Center, Floor 5)",
     "aliases": ["lift", "elevator", "center lift"], "corridor": "5_south"},
    {"id": "Steps_5SW", "type": "steps", "floor": 5,
     "label": "Steps (SW, Floor 5)",
     "aliases": ["steps", "stairs", "staircase"], "corridor": "5_south_west"},
    {"id": "Steps_5NE", "type": "steps", "floor": 5,
     "label": "Steps (NE, Floor 5)",
     "aliases": ["steps", "stairs", "staircase"], "corridor": "5_inner_north"},
    {"id": "Steps_5SE", "type": "steps", "floor": 5,
     "label": "Steps (SE, Floor 5)",
     "aliases": ["steps", "stairs", "staircase"], "corridor": "5_south"},
    {"id": "Gate_5E", "type": "gate", "floor": 5, "label": "Gate (East, Floor 5)",
     "aliases": ["gate", "east gate", "main gate"], "corridor": "5_south"},
    {"id": "Gate_5NE", "type": "gate", "floor": 5,
     "label": "Gate (NE, Floor 5)",
     "aliases": ["gate", "north east gate"], "corridor": "5_inner_north"},
    {"id": "Small_Gate_5", "type": "gate", "floor": 5,
     "label": "Small Gate (Floor 5)",
     "aliases": ["small gate", "back gate"], "corridor": "5_south_west"},
    {"id": "Gents_Toilet_5E", "type": "toilet", "floor": 5,
     "label": "Gents Toilet (East Wing, F5)",
     "aliases": ["gents toilet", "mens toilet", "mens restroom"],
     "corridor": "5_east"},
    {"id": "Ladies_Toilet_5E", "type": "toilet", "floor": 5,
     "label": "Ladies Toilet (East Wing, F5)",
     "aliases": ["ladies toilet", "womens toilet", "womens restroom"],
     "corridor": "5_east"},
    {"id": "Gents_Toilet_5W", "type": "toilet", "floor": 5,
     "label": "Gents Toilet (West Wing, F5)",
     "aliases": ["gents toilet", "mens toilet"], "corridor": "5_west"},
    {"id": "Ladies_Toilet_5W", "type": "toilet", "floor": 5,
     "label": "Ladies Toilet (West Wing, F5)",
     "aliases": ["ladies toilet", "womens toilet"], "corridor": "5_west"},
]


def _build_floor5_edges():
    """Build all edges for Floor 5 from the floor plan."""
    edges = []

    # ── South corridor (west → east) ──
    _add_bidir_edge(edges, "Lift_5C", "501", "east", "5_south")
    _add_bidir_edge(edges, "501", "502", "east", "5_south")
    _add_bidir_edge(edges, "502", "503", "east", "5_south")
    _add_bidir_edge(edges, "503", "504", "east", "5_south")
    _add_bidir_edge(edges, "504", "Steps_5SE", "east", "5_south")
    _add_bidir_edge(edges, "Steps_5SE", "Gate_5E", "east", "5_south")

    # ── SW area (below west wing) ──
    _add_bidir_edge(edges, "513", "Steps_5SW", "south", "5_south_west")
    _add_bidir_edge(edges, "Steps_5SW", "Lift_5C", "east", "5_south")
    _add_bidir_edge(edges, "Steps_5SW", "Xerox_5", "south", "5_south_west")
    _add_bidir_edge(edges, "Xerox_5", "Physics_Lab", "south", "5_south_west")
    _add_bidir_edge(edges, "Physics_Lab", "Small_Gate_5", "south", "5_south_west")

    # ── SE corner (east wing bottom meets south corridor) ──
    _add_bidir_edge(edges, "505", "Steps_5SE", "south", "5_east_south_junc")

    # ── East wing (north → south, i.e. top → bottom on map) ──
    # Walking south along east wing: toilets → 507A → 507 → 506 → 505
    _add_bidir_edge(edges, "Gents_Toilet_5E", "Ladies_Toilet_5E", "south", "5_east")
    _add_bidir_edge(edges, "Ladies_Toilet_5E", "507A", "south", "5_east")
    _add_bidir_edge(edges, "507A", "507", "south", "5_east")
    _add_bidir_edge(edges, "507", "506", "south", "5_east")
    _add_bidir_edge(edges, "506", "505", "south", "5_east")

    # ── West wing (south → north, i.e. bottom → top on map) ──
    # Walking north along west wing: 513 → 514 → ... → 522
    _add_bidir_edge(edges, "513", "514", "north", "5_west")
    _add_bidir_edge(edges, "514", "515", "north", "5_west")
    _add_bidir_edge(edges, "515", "516", "north", "5_west")
    _add_bidir_edge(edges, "516", "517", "north", "5_west")
    _add_bidir_edge(edges, "517", "518", "north", "5_west")
    _add_bidir_edge(edges, "518", "Ladies_Toilet_5W", "north", "5_west")
    _add_bidir_edge(edges, "Ladies_Toilet_5W", "Gents_Toilet_5W", "north", "5_west")
    _add_bidir_edge(edges, "Gents_Toilet_5W", "521", "north", "5_west")
    _add_bidir_edge(edges, "521", "522", "north", "5_west")

    # ── NW corner (west wing top → north corridor) ──
    _add_bidir_edge(edges, "522", "Hall_5", "east", "5_nw_junc")

    # ── North corridor (west → east) ──
    _add_bidir_edge(edges, "Water_5", "Hall_5", "east", "5_north")
    _add_bidir_edge(edges, "Hall_5", "Seminar_Hall", "east", "5_north")
    _add_bidir_edge(edges, "Seminar_Hall", "526", "east", "5_north")
    _add_bidir_edge(edges, "526", "527", "east", "5_north")
    _add_bidir_edge(edges, "527", "Dept_of_Commerce", "east", "5_north")
    _add_bidir_edge(edges, "Dept_of_Commerce", "Lift_5NE", "east", "5_north")

    # Panel Room : near Seminar Hall (best guess, not on map)
    _add_bidir_edge(edges, "Seminar_Hall", "Panel_Room", "south", "5_north")

    # ── Inner north area (523, 524 below north corridor) ──
    _add_bidir_edge(edges, "526", "523", "south", "5_inner_north")
    _add_bidir_edge(edges, "523", "524", "east", "5_inner_north")
    _add_bidir_edge(edges, "524", "Steps_5NE", "east", "5_inner_north")
    _add_bidir_edge(edges, "Steps_5NE", "Gate_5NE", "east", "5_inner_north")

    # ── NE corner (north corridor end → east wing top) ──
    _add_bidir_edge(edges, "Lift_5NE", "Steps_5NE", "south", "5_ne_junc")
    _add_bidir_edge(edges, "Steps_5NE", "Gents_Toilet_5E", "south", "5_ne_junc")

    return edges


#  FLOOR 6  :  from MAP.pdf Page 2
FLOOR_6_NODES = [
    # ── South corridor rooms ──
    {"id": "601", "type": "room", "floor": 6, "label": "Room 601",
     "aliases": ["601", "six oh one", "six zero one"], "corridor": "6_south"},
    {"id": "602", "type": "room", "floor": 6, "label": "Room 602",
     "aliases": ["602", "six oh two", "six zero two"], "corridor": "6_south"},
    {"id": "603", "type": "room", "floor": 6, "label": "Room 603",
     "aliases": ["603", "six oh three", "six zero three"], "corridor": "6_south"},

    # ── East wing rooms ──
    {"id": "604", "type": "room", "floor": 6, "label": "Room 604",
     "aliases": ["604", "six oh four", "six zero four"], "corridor": "6_east"},
    {"id": "605", "type": "room", "floor": 6, "label": "Room 605",
     "aliases": ["605", "six oh five", "six zero five"], "corridor": "6_east"},
    {"id": "606", "type": "room", "floor": 6, "label": "Room 606",
     "aliases": ["606", "six oh six", "six zero six"], "corridor": "6_east"},
    {"id": "607", "type": "room", "floor": 6, "label": "Room 607",
     "aliases": ["607", "six oh seven", "six zero seven"], "corridor": "6_east"},
    {"id": "607A", "type": "room", "floor": 6, "label": "Room 607A",
     "aliases": ["607A", "six oh seven A", "six zero seven A"],
     "corridor": "6_east"},

    # ── West wing rooms ──
    {"id": "613", "type": "room", "floor": 6, "label": "Room 613",
     "aliases": ["613", "six thirteen"], "corridor": "6_west"},
    {"id": "615", "type": "room", "floor": 6, "label": "Room 615",
     "aliases": ["615", "six fifteen"], "corridor": "6_west"},
    {"id": "616", "type": "room", "floor": 6, "label": "Room 616",
     "aliases": ["616", "six sixteen"], "corridor": "6_west"},
    {"id": "617", "type": "room", "floor": 6, "label": "Room 617",
     "aliases": ["617", "six seventeen"], "corridor": "6_west"},
    {"id": "621", "type": "room", "floor": 6, "label": "Room 621",
     "aliases": ["621", "six twenty one"], "corridor": "6_west"},

    # ── North corridor rooms ──
    {"id": "623", "type": "room", "floor": 6, "label": "Room 623",
     "aliases": ["623", "six twenty three"], "corridor": "6_inner_north"},
    {"id": "624", "type": "room", "floor": 6, "label": "Room 624",
     "aliases": ["624", "six twenty four"], "corridor": "6_inner_north"},
    {"id": "625", "type": "room", "floor": 6, "label": "Room 625",
     "aliases": ["625", "six twenty five"], "corridor": "6_north"},
    {"id": "626", "type": "room", "floor": 6, "label": "Room 626",
     "aliases": ["626", "six twenty six"], "corridor": "6_north"},
    {"id": "627", "type": "room", "floor": 6, "label": "Room 627",
     "aliases": ["627", "six twenty seven"], "corridor": "6_north"},

    # ── Landmarks ──
    {"id": "Quantum_Computing", "type": "landmark", "floor": 6,
     "label": "Quantum Computing Lab",
     "aliases": ["quantum computing", "quantum computing lab", "quantum lab"],
     "corridor": "6_south"},
    {"id": "Dept_of_Math", "type": "landmark", "floor": 6,
     "label": "Department of Mathematics",
     "aliases": ["department of mathematics", "dept of math", "dept of mathematics",
                 "math department", "Dept_of_Mathematics", "mathematics"],
     "corridor": "6_west"},
    {"id": "Dept_of_CS_W", "type": "landmark", "floor": 6,
     "label": "Department of Computer Science (West)",
     "aliases": ["department of computer science", "dept of cs", "cs department",
                 "computer science"],
     "corridor": "6_west"},
    {"id": "Dept_of_CS_N", "type": "landmark", "floor": 6,
     "label": "Department of Computer Science (North)",
     "aliases": ["department of computer science", "dept of cs", "cs department"],
     "corridor": "6_north"},
    {"id": "Energy_Science_Lab", "type": "landmark", "floor": 6,
     "label": "Energy Science Lab",
     "aliases": ["energy science lab", "energy science", "energy lab"],
     "corridor": "6_west"},
    {"id": "Water_6", "type": "landmark", "floor": 6,
     "label": "Water Cooler (F6)",
     "aliases": ["water", "water cooler", "drinking water"], "corridor": "6_north"},

    # ── Infrastructure ──
    {"id": "Lift_6NE", "type": "lift", "floor": 6, "label": "Lift (NE, Floor 6)",
     "aliases": ["lift", "elevator"], "corridor": "6_north"},
    {"id": "Lift_6C", "type": "lift", "floor": 6, "label": "Lift (Center, Floor 6)",
     "aliases": ["lift", "elevator", "center lift"], "corridor": "6_south"},
    {"id": "Steps_6NE", "type": "steps", "floor": 6,
     "label": "Steps (NE, Floor 6)",
     "aliases": ["steps", "stairs"], "corridor": "6_inner_north"},
    {"id": "Steps_6E", "type": "steps", "floor": 6,
     "label": "Steps (East, Floor 6)",
     "aliases": ["steps", "stairs"], "corridor": "6_south"},
    {"id": "Gents_Toilet_6E", "type": "toilet", "floor": 6,
     "label": "Gents Toilet (East Wing, F6)",
     "aliases": ["gents toilet", "mens toilet"], "corridor": "6_east"},
    {"id": "Ladies_Toilet_6E", "type": "toilet", "floor": 6,
     "label": "Ladies Toilet (East Wing, F6)",
     "aliases": ["ladies toilet", "womens toilet"], "corridor": "6_east"},
    {"id": "Gents_Toilet_6W", "type": "toilet", "floor": 6,
     "label": "Gents Toilet (West Wing, F6)",
     "aliases": ["gents toilet", "mens toilet"], "corridor": "6_west"},
    {"id": "Ladies_Toilet_6W", "type": "toilet", "floor": 6,
     "label": "Ladies Toilet (West Wing, F6)",
     "aliases": ["ladies toilet", "womens toilet"], "corridor": "6_west"},
]


def _build_floor6_edges():
    """Build all edges for Floor 6 from the floor plan."""
    edges = []

    # ── South corridor (west → east) ──
    _add_bidir_edge(edges, "Lift_6C", "601", "east", "6_south")
    _add_bidir_edge(edges, "601", "Quantum_Computing", "east", "6_south")
    _add_bidir_edge(edges, "Quantum_Computing", "602", "east", "6_south")
    _add_bidir_edge(edges, "602", "603", "east", "6_south")
    _add_bidir_edge(edges, "603", "Steps_6E", "east", "6_south")

    # ── SW corner (west wing bottom → south corridor) ──
    _add_bidir_edge(edges, "613", "Lift_6C", "east", "6_sw_junc")

    # ── SE corner (east wing bottom → south corridor) ──
    _add_bidir_edge(edges, "604", "Steps_6E", "south", "6_se_junc")

    # ── East wing (north → south) ──
    _add_bidir_edge(edges, "Gents_Toilet_6E", "Ladies_Toilet_6E", "south", "6_east")
    _add_bidir_edge(edges, "Ladies_Toilet_6E", "607A", "south", "6_east")
    _add_bidir_edge(edges, "607A", "607", "south", "6_east")
    _add_bidir_edge(edges, "607", "606", "south", "6_east")
    _add_bidir_edge(edges, "606", "605", "south", "6_east")
    _add_bidir_edge(edges, "605", "604", "south", "6_east")

    # ── West wing (south → north) ──
    _add_bidir_edge(edges, "613", "Dept_of_Math", "north", "6_west")
    _add_bidir_edge(edges, "Dept_of_Math", "615", "north", "6_west")
    _add_bidir_edge(edges, "615", "616", "north", "6_west")
    _add_bidir_edge(edges, "616", "617", "north", "6_west")
    _add_bidir_edge(edges, "617", "Energy_Science_Lab", "north", "6_west")
    _add_bidir_edge(edges, "Energy_Science_Lab", "Ladies_Toilet_6W", "north", "6_west")
    _add_bidir_edge(edges, "Ladies_Toilet_6W", "Gents_Toilet_6W", "north", "6_west")
    _add_bidir_edge(edges, "Gents_Toilet_6W", "621", "north", "6_west")
    _add_bidir_edge(edges, "621", "Dept_of_CS_W", "north", "6_west")

    # ── NW corner (west wing top → north corridor) ──
    _add_bidir_edge(edges, "Dept_of_CS_W", "Water_6", "east", "6_nw_junc")

    # ── North corridor (west → east) ──
    _add_bidir_edge(edges, "Water_6", "625", "east", "6_north")
    _add_bidir_edge(edges, "625", "626", "east", "6_north")
    _add_bidir_edge(edges, "626", "627", "east", "6_north")
    _add_bidir_edge(edges, "627", "Dept_of_CS_N", "east", "6_north")
    _add_bidir_edge(edges, "Dept_of_CS_N", "Lift_6NE", "east", "6_north")

    # ── Inner north area ──
    _add_bidir_edge(edges, "625", "623", "south", "6_inner_north")
    _add_bidir_edge(edges, "623", "624", "east", "6_inner_north")
    _add_bidir_edge(edges, "624", "Steps_6NE", "east", "6_inner_north")

    # ── NE corner ──
    _add_bidir_edge(edges, "Lift_6NE", "Steps_6NE", "south", "6_ne_junc")
    _add_bidir_edge(edges, "Steps_6NE", "Gents_Toilet_6E", "south", "6_ne_junc")

    return edges


#  FLOOR 7  :  Inferred from dataset images (no floor plan)
#  NOTE: This floor follows the same building pattern as floors 5-6.
#  Room adjacencies are best-guess and may need manual correction.
FLOOR_7_NODES = [
    # ── South corridor rooms ──
    {"id": "701", "type": "room", "floor": 7, "label": "Room 701",
     "aliases": ["701", "seven oh one", "seven zero one"], "corridor": "7_south"},
    {"id": "702", "type": "room", "floor": 7, "label": "Room 702",
     "aliases": ["702", "seven oh two", "seven zero two"], "corridor": "7_south"},
    {"id": "703", "type": "room", "floor": 7, "label": "Room 703",
     "aliases": ["703", "seven oh three", "seven zero three"], "corridor": "7_south"},
    {"id": "704", "type": "room", "floor": 7, "label": "Room 704",
     "aliases": ["704", "seven oh four", "seven zero four"], "corridor": "7_south"},

    # ── East wing rooms ──
    {"id": "705", "type": "room", "floor": 7, "label": "Room 705",
     "aliases": ["705", "seven oh five", "seven zero five"], "corridor": "7_east"},
    {"id": "707", "type": "room", "floor": 7, "label": "Room 707",
     "aliases": ["707", "seven oh seven", "seven zero seven"], "corridor": "7_east"},
    {"id": "708", "type": "room", "floor": 7, "label": "Room 708",
     "aliases": ["708", "seven oh eight", "seven zero eight"], "corridor": "7_east"},
    {"id": "709C", "type": "room", "floor": 7, "label": "Room 709C",
     "aliases": ["709C", "seven oh nine C", "seven zero nine C"],
     "corridor": "7_east"},

    # ── West wing rooms ──
    {"id": "710", "type": "room", "floor": 7, "label": "Room 710",
     "aliases": ["710", "seven ten"], "corridor": "7_west"},
    {"id": "711", "type": "room", "floor": 7, "label": "Room 711",
     "aliases": ["711", "seven eleven"], "corridor": "7_west"},
    {"id": "713", "type": "room", "floor": 7, "label": "Room 713",
     "aliases": ["713", "seven thirteen"], "corridor": "7_west"},
    {"id": "714", "type": "room", "floor": 7, "label": "Room 714",
     "aliases": ["714", "seven fourteen"], "corridor": "7_west"},
    {"id": "715", "type": "room", "floor": 7, "label": "Room 715",
     "aliases": ["715", "seven fifteen"], "corridor": "7_west"},
    {"id": "716", "type": "room", "floor": 7, "label": "Room 716",
     "aliases": ["716", "seven sixteen"], "corridor": "7_west"},
    {"id": "717", "type": "room", "floor": 7, "label": "Room 717",
     "aliases": ["717", "seven seventeen"], "corridor": "7_west"},
    {"id": "718", "type": "room", "floor": 7, "label": "Room 718",
     "aliases": ["718", "seven eighteen"], "corridor": "7_west"},

    # ── North corridor rooms ──
    {"id": "721", "type": "room", "floor": 7, "label": "Room 721",
     "aliases": ["721", "seven twenty one"], "corridor": "7_north_west"},
    {"id": "722", "type": "room", "floor": 7, "label": "Room 722",
     "aliases": ["722", "seven twenty two"], "corridor": "7_north_west"},
    {"id": "724", "type": "room", "floor": 7, "label": "Room 724",
     "aliases": ["724", "seven twenty four"], "corridor": "7_inner_north"},
    {"id": "725", "type": "room", "floor": 7, "label": "Room 725",
     "aliases": ["725", "seven twenty five"], "corridor": "7_north"},
    {"id": "727", "type": "room", "floor": 7, "label": "Room 727",
     "aliases": ["727", "seven twenty seven"], "corridor": "7_north"},

    # ── Extended wing rooms (741-747) ──
    {"id": "741", "type": "room", "floor": 7, "label": "Room 741",
     "aliases": ["741", "seven forty one"], "corridor": "7_wing_a"},
    {"id": "742", "type": "room", "floor": 7, "label": "Room 742",
     "aliases": ["742", "seven forty two"], "corridor": "7_wing_a"},
    {"id": "743", "type": "room", "floor": 7, "label": "Room 743",
     "aliases": ["743", "seven forty three"], "corridor": "7_wing_a"},
    {"id": "744", "type": "room", "floor": 7, "label": "Room 744",
     "aliases": ["744", "seven forty four"], "corridor": "7_wing_a"},
    {"id": "746", "type": "room", "floor": 7, "label": "Room 746",
     "aliases": ["746", "seven forty six"], "corridor": "7_wing_a"},
    {"id": "747", "type": "room", "floor": 7, "label": "Room 747",
     "aliases": ["747", "seven forty seven"], "corridor": "7_wing_a"},

    # ── Extended wing rooms (751-755) ──
    {"id": "751", "type": "room", "floor": 7, "label": "Room 751",
     "aliases": ["751", "seven fifty one"], "corridor": "7_wing_b"},
    {"id": "752", "type": "room", "floor": 7, "label": "Room 752",
     "aliases": ["752", "seven fifty two"], "corridor": "7_wing_b"},
    {"id": "753", "type": "room", "floor": 7, "label": "Room 753",
     "aliases": ["753", "seven fifty three"], "corridor": "7_wing_b"},
    {"id": "754", "type": "room", "floor": 7, "label": "Room 754",
     "aliases": ["754", "seven fifty four"], "corridor": "7_wing_b"},
    {"id": "755", "type": "room", "floor": 7, "label": "Room 755",
     "aliases": ["755", "seven fifty five"], "corridor": "7_wing_b"},

    # ── Landmarks ──
    {"id": "Prayer_Hall", "type": "landmark", "floor": 7, "label": "Prayer Hall",
     "aliases": ["prayer hall", "prayer room"], "corridor": "7_north"},
    {"id": "Assembly_Hall", "type": "landmark", "floor": 7,
     "label": "Assembly Hall",
     "aliases": ["assembly hall", "assembly"], "corridor": "7_north"},
    {"id": "Dept_of_Psychology", "type": "landmark", "floor": 7,
     "label": "Department of Psychology",
     "aliases": ["department of psychology", "dept of psychology",
                 "psychology department", "psychology"],
     "corridor": "7_west"},
    {"id": "School_of_Education", "type": "landmark", "floor": 7,
     "label": "School of Education",
     "aliases": ["school of education", "education"], "corridor": "7_north"},
    {"id": "Assoc_Dean_Sciences", "type": "landmark", "floor": 7,
     "label": "Associate Dean, School of Sciences",
     "aliases": ["associate dean school of sciences", "associate dean sciences",
                 "Associate_Dean_School_of_Sciences"],
     "corridor": "7_north"},

    # ── Infrastructure ──
    {"id": "Lift_7NE", "type": "lift", "floor": 7, "label": "Lift (NE, Floor 7)",
     "aliases": ["lift", "elevator"], "corridor": "7_north"},
    {"id": "Lift_7C", "type": "lift", "floor": 7, "label": "Lift (Center, Floor 7)",
     "aliases": ["lift", "elevator", "center lift"], "corridor": "7_south"},
    {"id": "Steps_7NE", "type": "steps", "floor": 7,
     "label": "Steps (NE, Floor 7)",
     "aliases": ["steps", "stairs"], "corridor": "7_inner_north"},
    {"id": "Steps_7E", "type": "steps", "floor": 7,
     "label": "Steps (East, Floor 7)",
     "aliases": ["steps", "stairs"], "corridor": "7_south"},
    {"id": "Gents_Toilet_7E", "type": "toilet", "floor": 7,
     "label": "Gents Toilet (East Wing, F7)",
     "aliases": ["gents toilet", "mens toilet"], "corridor": "7_east"},
    {"id": "Ladies_Toilet_7E", "type": "toilet", "floor": 7,
     "label": "Ladies Toilet (East Wing, F7)",
     "aliases": ["ladies toilet", "womens toilet"], "corridor": "7_east"},
    {"id": "Gents_Toilet_7W", "type": "toilet", "floor": 7,
     "label": "Gents Toilet (West Wing, F7)",
     "aliases": ["gents toilet", "mens toilet"], "corridor": "7_west"},
    {"id": "Ladies_Toilet_7W", "type": "toilet", "floor": 7,
     "label": "Ladies Toilet (West Wing, F7)",
     "aliases": ["ladies toilet", "womens toilet"], "corridor": "7_west"},
]


def _build_floor7_edges():
    """Build edges for Floor 7 (inferred from dataset : no floor plan)."""
    edges = []

    # ── South corridor (west → east) ──
    _add_bidir_edge(edges, "Lift_7C", "701", "east", "7_south")
    _add_bidir_edge(edges, "701", "702", "east", "7_south")
    _add_bidir_edge(edges, "702", "703", "east", "7_south")
    _add_bidir_edge(edges, "703", "704", "east", "7_south")
    _add_bidir_edge(edges, "704", "Steps_7E", "east", "7_south")

    # ── SE corner ──
    _add_bidir_edge(edges, "705", "Steps_7E", "south", "7_se_junc")

    # ── East wing (north → south) ──
    _add_bidir_edge(edges, "Gents_Toilet_7E", "Ladies_Toilet_7E", "south", "7_east")
    _add_bidir_edge(edges, "Ladies_Toilet_7E", "709C", "south", "7_east")
    _add_bidir_edge(edges, "709C", "708", "south", "7_east")
    _add_bidir_edge(edges, "708", "707", "south", "7_east")
    _add_bidir_edge(edges, "707", "705", "south", "7_east")

    # ── SW corner ──
    _add_bidir_edge(edges, "710", "Lift_7C", "east", "7_sw_junc")

    # ── West wing (south → north) ──
    _add_bidir_edge(edges, "710", "711", "north", "7_west")
    _add_bidir_edge(edges, "711", "713", "north", "7_west")
    _add_bidir_edge(edges, "713", "714", "north", "7_west")
    _add_bidir_edge(edges, "714", "715", "north", "7_west")
    _add_bidir_edge(edges, "715", "716", "north", "7_west")
    _add_bidir_edge(edges, "716", "717", "north", "7_west")
    _add_bidir_edge(edges, "717", "718", "north", "7_west")
    _add_bidir_edge(edges, "718", "Ladies_Toilet_7W", "north", "7_west")
    _add_bidir_edge(edges, "Ladies_Toilet_7W", "Gents_Toilet_7W", "north", "7_west")
    _add_bidir_edge(edges, "Gents_Toilet_7W", "722", "north", "7_west")

    # Dept of Psychology : near west wing
    _add_bidir_edge(edges, "Dept_of_Psychology", "715", "south", "7_west")

    # ── NW corner ──
    _add_bidir_edge(edges, "722", "721", "east", "7_nw_junc")

    # ── North corridor (west → east) ──
    _add_bidir_edge(edges, "721", "Prayer_Hall", "east", "7_north")
    _add_bidir_edge(edges, "Prayer_Hall", "Assembly_Hall", "east", "7_north")
    _add_bidir_edge(edges, "Assembly_Hall", "725", "east", "7_north")
    _add_bidir_edge(edges, "725", "727", "east", "7_north")
    _add_bidir_edge(edges, "727", "School_of_Education", "east", "7_north")
    _add_bidir_edge(edges, "School_of_Education", "Assoc_Dean_Sciences", "east", "7_north")
    _add_bidir_edge(edges, "Assoc_Dean_Sciences", "Lift_7NE", "east", "7_north")

    # ── Inner north ──
    _add_bidir_edge(edges, "725", "724", "south", "7_inner_north")
    _add_bidir_edge(edges, "724", "Steps_7NE", "east", "7_inner_north")

    # ── NE corner ──
    _add_bidir_edge(edges, "Lift_7NE", "Steps_7NE", "south", "7_ne_junc")
    _add_bidir_edge(edges, "Steps_7NE", "Gents_Toilet_7E", "south", "7_ne_junc")

    # ── Extended wing A (741-747) : connected at north corridor ──
    _add_bidir_edge(edges, "741", "742", "east", "7_wing_a")
    _add_bidir_edge(edges, "742", "743", "east", "7_wing_a")
    _add_bidir_edge(edges, "743", "744", "east", "7_wing_a")
    _add_bidir_edge(edges, "744", "746", "east", "7_wing_a")
    _add_bidir_edge(edges, "746", "747", "east", "7_wing_a")
    # Connect wing A to main building (near 727 / School of Education area)
    _add_bidir_edge(edges, "727", "741", "north", "7_wing_a_junc")

    # ── Extended wing B (751-755) : connected near wing A ──
    _add_bidir_edge(edges, "751", "752", "east", "7_wing_b")
    _add_bidir_edge(edges, "752", "753", "east", "7_wing_b")
    _add_bidir_edge(edges, "753", "754", "east", "7_wing_b")
    _add_bidir_edge(edges, "754", "755", "east", "7_wing_b")
    # Connect wing B to wing A (near 747)
    _add_bidir_edge(edges, "747", "751", "north", "7_wing_b_junc")

    return edges


#  CROSS-FLOOR CONNECTIONS
def _build_cross_floor_edges():
    """Build edges connecting floors via lifts and steps."""
    edges = []

    # ── Lifts (NE corner) ──
    _add_bidir_edge(edges, "Lift_5NE", "Lift_6NE", "up", "lift_NE", distance=2)
    _add_bidir_edge(edges, "Lift_6NE", "Lift_7NE", "up", "lift_NE", distance=2)

    # ── Lifts (Center) ──
    _add_bidir_edge(edges, "Lift_5C", "Lift_6C", "up", "lift_C", distance=2)
    _add_bidir_edge(edges, "Lift_6C", "Lift_7C", "up", "lift_C", distance=2)

    # ── Steps (NE area) ──
    _add_bidir_edge(edges, "Steps_5NE", "Steps_6NE", "up", "steps_NE", distance=3)
    _add_bidir_edge(edges, "Steps_6NE", "Steps_7NE", "up", "steps_NE", distance=3)

    # ── Steps (East / SE) ──
    _add_bidir_edge(edges, "Steps_5SE", "Steps_6E", "up", "steps_E", distance=3)
    _add_bidir_edge(edges, "Steps_6E", "Steps_7E", "up", "steps_E", distance=3)

    return edges


#  GRAPH BUILDER & UTILITIES
ALL_NODES = FLOOR_5_NODES + FLOOR_6_NODES + FLOOR_7_NODES


def build_graph() -> nx.DiGraph:
    """Build the complete building knowledge graph from floor plan data.

    Floor mapping:
        5xx rooms = Ground Floor
        6xx rooms = Second Floor
        7xx rooms = Third Floor

    Returns:
        A networkx DiGraph with all nodes and directional edges.
    """
    G = nx.DiGraph()

    # Add nodes
    for node in ALL_NODES:
        G.add_node(node["id"], **{k: v for k, v in node.items() if k != "id"})

    # Enrich every node with floor_name and update infrastructure labels
    for node_id, data in G.nodes(data=True):
        floor_num = data.get("floor")
        floor_name = FLOOR_NAMES.get(floor_num, f"Floor {floor_num}")
        data["floor_name"] = floor_name

        # Update labels like "Lift (NE, Floor 5)" → "Lift (NE, Ground Floor)"
        label = data.get("label", "")
        if f"F{floor_num}" in label:
            data["label"] = label.replace(f"F{floor_num}", floor_name)
        elif f"Floor {floor_num}" in label:
            data["label"] = label.replace(f"Floor {floor_num}", floor_name)

    # Add edges
    all_edges = (
        _build_floor5_edges()
        + _build_floor6_edges()
        + _build_floor7_edges()
        + _build_cross_floor_edges()
    )
    for edge in all_edges:
        G.add_edge(
            edge["from"], edge["to"],
            direction=edge["direction"],
            corridor_segment=edge["corridor_segment"],
            distance=edge["distance"],
        )

    return G


def save_graph(graph: nx.DiGraph, path: Optional[str] = None):
    """Save the graph to a JSON file.

    Args:
        graph: The networkx DiGraph to save.
        path:  Output file path. Defaults to building_graph.json in project root.
    """
    if path is None:
        path = Path(__file__).resolve().parent / "building_graph.json"
    else:
        path = Path(path)

    data = {
        "metadata": {
            "description": "WayLens building knowledge graph",
            "floors": {"5": "Ground Floor", "6": "First Floor", "7": "Second Floor"},
            "total_nodes": graph.number_of_nodes(),
            "total_edges": graph.number_of_edges(),
        },
        "nodes": [],
        "edges": [],
    }

    for node_id, attrs in graph.nodes(data=True):
        data["nodes"].append({"id": node_id, **attrs})

    for u, v, attrs in graph.edges(data=True):
        data["edges"].append({"from": u, "to": v, **attrs})

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    print(f"✓ Graph saved to {path}")
    print(f"  Nodes: {graph.number_of_nodes()}, Edges: {graph.number_of_edges()}")


def load_graph(path: Optional[str] = None) -> nx.DiGraph:
    """Load the graph from a JSON file.

    Args:
        path: Input file path. Defaults to building_graph.json in project root.

    Returns:
        A networkx DiGraph reconstructed from the JSON.
    """
    if path is None:
        try:
            from config import Config
            path = Config.GRAPH_JSON_PATH
        except Exception:
            path = Path(__file__).resolve().parent / "building_graph.json"
            if not path.exists():
                path = Path(__file__).resolve().parent.parent / "data" / "building_graph.json"
    else:
        path = Path(path)

    if not path.exists():
        # Fallback search in data directory or root
        alt_paths = [
            Path(__file__).resolve().parent.parent / "data" / "building_graph.json",
            Path(__file__).resolve().parent.parent / "building_graph.json",
            Path(__file__).resolve().parent / "building_graph.json",
        ]
        for p in alt_paths:
            if p.exists():
                path = p
                break

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    G = nx.DiGraph()

    for node in data["nodes"]:
        node_id = node.pop("id")
        G.add_node(node_id, **node)

    for edge in data["edges"]:
        u = edge.pop("from")
        v = edge.pop("to")
        G.add_edge(u, v, **edge)

    return G


def get_node_info(graph: nx.DiGraph, node_id: str) -> Optional[dict]:
    """Get all attributes for a node.

    Returns:
        Dict of node attributes, or None if node not found.
    """
    if node_id in graph:
        return {"id": node_id, **dict(graph.nodes[node_id])}
    return None


def get_adjacent_nodes(graph: nx.DiGraph, node_id: str) -> list[dict]:
    """Get all nodes adjacent to the given node, with edge info.

    Returns:
        List of dicts: [{id, direction, distance, corridor_segment}, ...]
    """
    if node_id not in graph:
        return []

    adjacent = []
    for _, neighbor, edge_data in graph.out_edges(node_id, data=True):
        adjacent.append({
            "id": neighbor,
            "direction": edge_data.get("direction"),
            "distance": edge_data.get("distance", 1),
            "corridor_segment": edge_data.get("corridor_segment"),
        })
    return adjacent


def get_all_room_ids(graph: nx.DiGraph) -> set[str]:
    """Get all valid node IDs that a user can navigate to.

    Returns rooms, landmarks, and other named navigable locations.
    """
    navigable_types = {"room", "landmark"}
    return {
        node_id for node_id, data in graph.nodes(data=True)
        if data.get("type") in navigable_types
    }


def get_all_node_ids(graph: nx.DiGraph) -> set[str]:
    """Get all node IDs in the graph (including infrastructure)."""
    return set(graph.nodes())


def get_floor(graph: nx.DiGraph, node_id: str) -> Optional[int]:
    """Get the floor number for a node."""
    if node_id in graph:
        return graph.nodes[node_id].get("floor")
    return None


def find_node_by_alias(graph: nx.DiGraph, alias: str) -> Optional[str]:
    """Find a node ID by matching an alias (case-insensitive).

    Args:
        alias: The alias string to search for.

    Returns:
        The matching node ID, or None.
    """
    alias_lower = alias.lower().strip()
    for node_id, data in graph.nodes(data=True):
        # Check node ID directly
        if node_id.lower() == alias_lower:
            return node_id
        # Check aliases
        for a in data.get("aliases", []):
            if a.lower() == alias_lower:
                return node_id
    return None


#  VALIDATION
def validate_graph(graph: nx.DiGraph) -> bool:
    """Validate the building graph for structural integrity.

    Checks:
        1. All nodes are reachable (weakly connected)
        2. All edges have required metadata
        3. No self-loops
        4. All node IDs are unique
        5. Per-floor connectivity

    Returns:
        True if all checks pass.
    """
    issues = []
    print("=" * 60)
    print("  WayLens Building Graph : Validation Report")
    print("=" * 60)

    # ── Basic stats ──
    print(f"\n  Total nodes: {graph.number_of_nodes()}")
    print(f"  Total edges: {graph.number_of_edges()}")

    # Count by floor
    floor_counts = {}
    for _, data in graph.nodes(data=True):
        f = data.get("floor", "?")
        floor_counts[f] = floor_counts.get(f, 0) + 1
    for f in sorted(floor_counts.keys()):
        print(f"  Floor {f}: {floor_counts[f]} nodes")

    # Count by type
    type_counts = {}
    for _, data in graph.nodes(data=True):
        t = data.get("type", "?")
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"\n  By type: {dict(sorted(type_counts.items()))}")

    # ── Check 1: Weak connectivity ──
    undirected = graph.to_undirected()
    if nx.is_connected(undirected):
        print("\n  ✓ Graph is connected (all nodes reachable)")
    else:
        components = list(nx.connected_components(undirected))
        print(f"\n  ✗ Graph is NOT connected : {len(components)} components:")
        for i, comp in enumerate(components):
            print(f"    Component {i+1} ({len(comp)} nodes): "
                  f"{sorted(list(comp))[:10]}...")
        issues.append("Graph not connected")

    # ── Check 2: Edge metadata ──
    edges_missing_dir = 0
    edges_missing_seg = 0
    for u, v, data in graph.edges(data=True):
        if "direction" not in data:
            edges_missing_dir += 1
        if "corridor_segment" not in data:
            edges_missing_seg += 1

    if edges_missing_dir == 0:
        print("  ✓ All edges have direction metadata")
    else:
        print(f"  ✗ {edges_missing_dir} edges missing direction metadata")
        issues.append("Missing direction metadata")

    if edges_missing_seg == 0:
        print("  ✓ All edges have corridor_segment metadata")
    else:
        print(f"  ✗ {edges_missing_seg} edges missing corridor_segment metadata")
        issues.append("Missing corridor_segment metadata")

    # ── Check 3: Self-loops ──
    self_loops = list(nx.selfloop_edges(graph))
    if not self_loops:
        print("  ✓ No self-loops")
    else:
        print(f"  ✗ Found {len(self_loops)} self-loops: {self_loops}")
        issues.append("Self-loops found")

    # ── Check 4: Bidirectional edges ──
    unmatched = 0
    for u, v in graph.edges():
        if not graph.has_edge(v, u):
            unmatched += 1
    if unmatched == 0:
        print("  ✓ All edges are bidirectional")
    else:
        print(f"  ✗ {unmatched} edges without reverse direction")
        issues.append("Non-bidirectional edges")

    # ── Check 5: Per-floor shortest path test ──
    print("\n  Sample shortest paths:")
    test_paths = [
        ("501", "527", "same floor, south→north"),
        ("513", "Seminar_Hall", "west wing → north corridor"),
        ("501", "601", "cross-floor via lift/steps"),
        ("501", "705", "cross two floors"),
    ]
    for src, dst, desc in test_paths:
        if src in graph and dst in graph:
            try:
                path = nx.shortest_path(undirected, src, dst)
                print(f"    {src} → {dst} ({desc}): {len(path)-1} hops")
                print(f"      Path: {' → '.join(path)}")
            except nx.NetworkXNoPath:
                print(f"    ✗ {src} → {dst}: NO PATH FOUND")
                issues.append(f"No path {src} → {dst}")

    # ── Summary ──
    print("\n" + "=" * 60)
    if issues:
        print(f"  ✗ VALIDATION FAILED : {len(issues)} issue(s):")
        for issue in issues:
            print(f"    - {issue}")
    else:
        print("  ✓ ALL CHECKS PASSED")
    print("=" * 60)

    return len(issues) == 0


#  CLI
def main():
    """CLI entry point: build, save, and validate the building graph."""
    import argparse

    parser = argparse.ArgumentParser(
        description="WayLens Building Knowledge Graph"
    )
    parser.add_argument(
        "--validate", action="store_true",
        help="Validate the graph and print a report"
    )
    parser.add_argument(
        "--rebuild", action="store_true",
        help="Rebuild the graph from code and save to JSON"
    )
    parser.add_argument(
        "--info", type=str, metavar="NODE_ID",
        help="Print info for a specific node"
    )
    parser.add_argument(
        "--neighbors", type=str, metavar="NODE_ID",
        help="Print adjacent nodes for a specific node"
    )
    parser.add_argument(
        "--path", nargs=2, metavar=("FROM", "TO"),
        help="Find shortest path between two nodes"
    )
    parser.add_argument(
        "--list-rooms", action="store_true",
        help="List all navigable rooms and landmarks"
    )

    args = parser.parse_args()
    graph_path = Path(__file__).resolve().parent / "building_graph.json"

    # Rebuild if requested or if JSON doesn't exist
    if args.rebuild or not graph_path.exists():
        print("Building graph from floor plan data...")
        graph = build_graph()
        save_graph(graph, graph_path)
        print()

    # Load graph
    if graph_path.exists():
        graph = load_graph(graph_path)
    else:
        graph = build_graph()

    # Handle commands
    if args.validate:
        validate_graph(graph)

    elif args.info:
        info = get_node_info(graph, args.info)
        if info:
            print(json.dumps(info, indent=2))
        else:
            print(f"Node '{args.info}' not found.")

    elif args.neighbors:
        adj = get_adjacent_nodes(graph, args.neighbors)
        if adj:
            print(f"Nodes adjacent to '{args.neighbors}':")
            for n in adj:
                print(f"  → {n['id']} ({n['direction']}, "
                      f"segment: {n['corridor_segment']})")
        else:
            print(f"Node '{args.neighbors}' not found or has no neighbors.")

    elif args.path:
        src, dst = args.path
        try:
            undirected = graph.to_undirected()
            path = nx.shortest_path(undirected, src, dst)
            print(f"Shortest path from {src} to {dst} ({len(path)-1} hops):")
            for i in range(len(path) - 1):
                edge_data = graph.edges[path[i], path[i + 1]]
                direction = edge_data.get("direction", "?")
                print(f"  {path[i]} → {path[i+1]} (go {direction})")
            print(f"  Arrived at {dst}!")
        except nx.NetworkXNoPath:
            print(f"No path found from {src} to {dst}.")
        except nx.NodeNotFound as e:
            print(f"Node not found: {e}")

    elif args.list_rooms:
        rooms = sorted(get_all_room_ids(graph))
        print(f"Navigable locations ({len(rooms)}):")
        for r in rooms:
            info = get_node_info(graph, r)
            print(f"  {r:30s}  Floor {info['floor']}  ({info['type']})")

    else:
        # Default: rebuild + validate
        if not args.rebuild:
            print("Building graph from floor plan data...")
            graph = build_graph()
            save_graph(graph, graph_path)
            print()
        validate_graph(graph)


if __name__ == "__main__":
    main()
