import uuid
import logging
import math
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)

CLASH_RULES = {
    ("structural", "mep"): {
        "min_clearance_mm": 50,
        "critical_threshold_mm": 0,
        "major_threshold_mm": 25
    },
    ("architectural", "mep"): {
        "min_clearance_mm": 25,
        "critical_threshold_mm": 0,
        "major_threshold_mm": 10
    },
    ("structural", "architectural"): {
        "min_clearance_mm": 10,
        "critical_threshold_mm": 0,
        "major_threshold_mm": 5
    },
    ("mep", "mep"): {
        "min_clearance_mm": 75,
        "critical_threshold_mm": 0,
        "major_threshold_mm": 50
    }
}

ELEMENT_SIZES = {
    "IfcBeam": {"width": 0.3, "height": 0.5, "depth": 5.0},
    "IfcColumn": {"width": 0.3, "height": 3.0, "depth": 0.3},
    "IfcDuctSegment": {"width": 0.6, "height": 0.4, "depth": 3.0},
    "IfcPipeSegment": {"width": 0.15, "height": 0.15, "depth": 3.0},
    "IfcSlab": {"width": 10.0, "height": 0.15, "depth": 10.0},
    "IfcWall": {"width": 0.23, "height": 3.0, "depth": 5.0},
    "IfcCableSegment": {"width": 0.05, "height": 0.05, "depth": 3.0},
}

def _get_bounding_box(element: Dict) -> Dict:
    loc = element.get("location", {"x": 0, "y": 0, "z": 0})
    size = ELEMENT_SIZES.get(element["type"], {"width": 0.3, "height": 0.3, "depth": 0.3})
    return {
        "min_x": loc["x"] - size["width"] / 2,
        "max_x": loc["x"] + size["width"] / 2,
        "min_y": loc["y"] - size["depth"] / 2,
        "max_y": loc["y"] + size["depth"] / 2,
        "min_z": loc["z"] - size["height"] / 2,
        "max_z": loc["z"] + size["height"] / 2,
    }

def _boxes_overlap(box1: Dict, box2: Dict) -> Tuple[bool, float]:
    overlap_x = max(0, min(box1["max_x"], box2["max_x"]) - max(box1["min_x"], box2["min_x"]))
    overlap_y = max(0, min(box1["max_y"], box2["max_y"]) - max(box1["min_y"], box2["min_y"]))
    overlap_z = max(0, min(box1["max_z"], box2["max_z"]) - max(box1["min_z"], box2["min_z"]))
    if overlap_x > 0 and overlap_y > 0 and overlap_z > 0:
        penetration = min(overlap_x, overlap_y, overlap_z) * 1000
        return True, round(penetration, 1)
    gap_x = max(0, max(box1["min_x"], box2["min_x"]) - min(box1["max_x"], box2["max_x"]))
    gap_y = max(0, max(box1["min_y"], box2["min_y"]) - min(box1["max_y"], box2["max_y"]))
    gap_z = max(0, max(box1["min_z"], box2["min_z"]) - min(box1["max_z"], box2["max_z"]))
    clearance = math.sqrt(gap_x**2 + gap_y**2 + gap_z**2) * 1000
    return False, round(clearance, 1)

def _determine_severity(clash_type: str, penetration_mm: float,
                        disc1: str, disc2: str) -> str:
    pair = tuple(sorted([disc1, disc2]))
    rules = CLASH_RULES.get(pair, {"critical_threshold_mm": 0, "major_threshold_mm": 25})
    if clash_type == "hard_clash":
        if penetration_mm > 100:
            return "critical"
        elif penetration_mm > 25:
            return "major"
        else:
            return "minor"
    else:
        if penetration_mm < rules["critical_threshold_mm"]:
            return "critical"
        elif penetration_mm < rules["major_threshold_mm"]:
            return "major"
        else:
            return "minor"

def detect_clashes(elements: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    clashes = []
    checked_pairs = set()
    for i, elem1 in enumerate(elements):
        for j, elem2 in enumerate(elements):
            if i >= j:
                continue
            pair_key = tuple(sorted([elem1["id"], elem2["id"]]))
            if pair_key in checked_pairs:
                continue
            checked_pairs.add(pair_key)
            if elem1["discipline"] == elem2["discipline"]:
                if elem1["discipline"] != "mep":
                    continue
            box1 = _get_bounding_box(elem1)
            box2 = _get_bounding_box(elem2)
            overlapping, measurement = _boxes_overlap(box1, box2)
            disc_pair = tuple(sorted([elem1["discipline"], elem2["discipline"]]))
            rules = CLASH_RULES.get(disc_pair, {"min_clearance_mm": 50})
            if overlapping:
                clash_type = "hard_clash"
                severity = _determine_severity(clash_type, measurement,
                                               elem1["discipline"], elem2["discipline"])
                clash = {
                    "clash_id": f"CLH-{str(uuid.uuid4())[:8].upper()}",
                    "element_1_id": elem1["id"],
                    "element_1_name": elem1["name"],
                    "element_1_type": elem1["type"],
                    "element_2_id": elem2["id"],
                    "element_2_name": elem2["name"],
                    "element_2_type": elem2["type"],
                    "element_1_discipline": elem1["discipline"],
                    "element_2_discipline": elem2["discipline"],
                    "clash_type": "hard_clash",
                    "severity": severity,
                    "penetration_mm": measurement,
                    "location": elem1.get("location", {}),
                    "description": (f"Hard clash between {elem1['name']} ({elem1['discipline']}) "
                                   f"and {elem2['name']} ({elem2['discipline']}) "
                                   f"with {measurement}mm penetration"),
                    "status": "open"
                }
                clashes.append(clash)
            elif measurement < rules["min_clearance_mm"]:
                severity = _determine_severity("clearance_clash", measurement,
                                               elem1["discipline"], elem2["discipline"])
                clash = {
                    "clash_id": f"CLH-{str(uuid.uuid4())[:8].upper()}",
                    "element_1_id": elem1["id"],
                    "element_1_name": elem1["name"],
                    "element_1_type": elem1["type"],
                    "element_2_id": elem2["id"],
                    "element_2_name": elem2["name"],
                    "element_2_type": elem2["type"],
                    "element_1_discipline": elem1["discipline"],
                    "element_2_discipline": elem2["discipline"],
                    "clash_type": "clearance_clash",
                    "severity": severity,
                    "clearance_mm": measurement,
                    "required_clearance_mm": rules["min_clearance_mm"],
                    "location": elem1.get("location", {}),
                    "description": (f"Clearance violation between {elem1['name']} ({elem1['discipline']}) "
                                   f"and {elem2['name']} ({elem2['discipline']}). "
                                   f"Clearance {measurement}mm, required {rules['min_clearance_mm']}mm"),
                    "status": "open"
                }
                clashes.append(clash)
    logger.info(f"Clash detection complete: {len(clashes)} clashes found")
    return sorted(clashes, key=lambda x: {"critical": 0, "major": 1, "minor": 2}[x["severity"]])