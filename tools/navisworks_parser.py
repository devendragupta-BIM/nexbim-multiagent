import logging
import uuid
from typing import Any, Dict, List, Optional
from pathlib import Path
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

CATEGORY_DISCIPLINE_MAP = {
    "Ducts": "mep",
    "Duct Fittings": "mep",
    "Duct Accessories": "mep",
    "Pipe": "mep",
    "Pipes": "mep",
    "Pipe Fittings": "mep",
    "Pipe Accessories": "mep",
    "Cable Trays": "mep",
    "Conduit": "mep",
    "Mechanical Equipment": "mep",
    "Plumbing Fixtures": "mep",
    "Sprinklers": "mep",
    "Structural Framing": "structural",
    "Structural Columns": "structural",
    "Structural Foundations": "structural",
    "Floors": "structural",
    "Structural Beam Systems": "structural",
    "Walls": "architectural",
    "Doors": "architectural",
    "Windows": "architectural",
    "Ceilings": "architectural",
    "Roofs": "architectural",
    "Stairs": "architectural",
    "Railings": "architectural",
}

SEVERITY_MAP = {
    "hard": {
        "large":  {"threshold": 0.1,  "severity": "critical"},
        "medium": {"threshold": 0.025, "severity": "major"},
        "small":  {"threshold": 0.0,   "severity": "minor"}
    },
    "clearance": {
        "large":  {"threshold": 0.05,  "severity": "major"},
        "small":  {"threshold": 0.0,   "severity": "minor"}
    }
}


class NavisworksParser:
    def __init__(self, xml_path: str):
        self.xml_path = Path(xml_path)
        self.clashes: List[Dict[str, Any]] = []
        self.test_name = ""
        self.total_tests = 0

    def _get_discipline(self, category: str) -> str:
        return CATEGORY_DISCIPLINE_MAP.get(category, "unknown")

    def _get_severity(self, test_type: str,
                      distance: float) -> str:
        abs_distance = abs(distance)
        if test_type == "hard":
            if abs_distance >= 0.1:
                return "critical"
            elif abs_distance >= 0.025:
                return "major"
            else:
                return "minor"
        else:
            if abs_distance <= 0.025:
                return "major"
            else:
                return "minor"

    def _parse_object(self, obj_elem) -> Dict[str, Any]:
        attrs = {}
        for attr in obj_elem.findall("objectattribute"):
            name_elem = attr.find("name")
            value_elem = attr.find("value")
            if name_elem is not None and value_elem is not None:
                if name_elem.text and value_elem.text:
                    attrs[name_elem.text.strip()] = \
                        value_elem.text.strip()
        return attrs

    def _parse_position(self, clash_elem) -> Dict[str, float]:
        try:
            point = clash_elem.find(".//pos3f")
            if point is not None:
                return {
                    "x": float(point.get("x", 0)),
                    "y": float(point.get("y", 0)),
                    "z": float(point.get("z", 0))
                }
        except Exception:
            pass
        return {"x": 0.0, "y": 0.0, "z": 0.0}

    def parse(self) -> List[Dict[str, Any]]:
        if not self.xml_path.exists():
            logger.error(f"XML file not found: {self.xml_path}")
            return []

        try:
            tree = ET.parse(str(self.xml_path))
            root = tree.getroot()
        except ET.ParseError as e:
            logger.error(f"Failed to parse XML: {e}")
            return []

        self.test_name = root.get("name", "Navisworks Clash Test")
        clash_tests = root.findall(".//clashtest")
        self.total_tests = len(clash_tests)

        for test in clash_tests:
            test_name = test.get("name", "Unknown Test")
            test_type = test.get("test_type", "hard")

            for clash_result in test.findall(".//clashresult"):
                clash_name = clash_result.get("name", "")
                clash_status = clash_result.get("status", "new")
                distance_str = clash_result.get("distance", "0")

                try:
                    distance = float(distance_str)
                except ValueError:
                    distance = 0.0

                if clash_status in ["resolved", "approved"]:
                    continue

                objects = clash_result.findall("clashobjects/clashobject")
                if len(objects) < 2:
                    continue

                obj1_attrs = self._parse_object(objects[0])
                obj2_attrs = self._parse_object(objects[1])
                position = self._parse_position(clash_result)
                severity = self._get_severity(test_type, distance)

                elem1_name = obj1_attrs.get("Item Name", "Unknown")
                elem2_name = obj2_attrs.get("Item Name", "Unknown")
                elem1_cat = obj1_attrs.get("Category", "")
                elem2_cat = obj2_attrs.get("Category", "")
                elem1_disc = self._get_discipline(elem1_cat)
                elem2_disc = self._get_discipline(elem2_cat)

                clash_type = (
                    "hard_clash" if test_type == "hard"
                    else "clearance_clash"
                )

                clash = {
                    "clash_id": f"NWC-{str(uuid.uuid4())[:8].upper()}",
                    "source": "navisworks",
                    "test_name": test_name,
                    "clash_name": clash_name,
                    "clash_type": clash_type,
                    "status": clash_status,
                    "distance_m": round(distance, 4),
                    "severity": severity,
                    "location": position,
                    "element_1_id": obj1_attrs.get("Element ID", ""),
                    "element_1_name": elem1_name,
                    "element_1_type": elem1_cat,
                    "element_1_discipline": elem1_disc,
                    "element_1_level": obj1_attrs.get("Level", ""),
                    "element_1_attrs": obj1_attrs,
                    "element_2_id": obj2_attrs.get("Element ID", ""),
                    "element_2_name": elem2_name,
                    "element_2_type": elem2_cat,
                    "element_2_discipline": elem2_disc,
                    "element_2_level": obj2_attrs.get("Level", ""),
                    "element_2_attrs": obj2_attrs,
                    "description": (
                        f"{clash_type.replace('_', ' ').title()} between "
                        f"{elem1_name} ({elem1_disc}) and "
                        f"{elem2_name} ({elem2_disc}) — "
                        f"distance: {abs(distance)*1000:.0f}mm"
                    )
                }
                self.clashes.append(clash)
                logger.debug(
                    f"Parsed clash: {clash['clash_id']} — "
                    f"{elem1_name} vs {elem2_name} — {severity}"
                )

        critical = len([c for c in self.clashes if c["severity"] == "critical"])
        major = len([c for c in self.clashes if c["severity"] == "major"])
        minor = len([c for c in self.clashes if c["severity"] == "minor"])

        logger.info(
            f"Navisworks parser complete — "
            f"{len(self.clashes)} clashes parsed "
            f"(Critical: {critical}, Major: {major}, Minor: {minor})"
        )

        return sorted(
            self.clashes,
            key=lambda x: {"critical": 0, "major": 1, "minor": 2}[x["severity"]]
        )

    def get_summary(self) -> Dict[str, Any]:
        return {
            "test_name": self.test_name,
            "total_tests": self.total_tests,
            "total_clashes": len(self.clashes),
            "critical": len([c for c in self.clashes if c["severity"] == "critical"]),
            "major": len([c for c in self.clashes if c["severity"] == "major"]),
            "minor": len([c for c in self.clashes if c["severity"] == "minor"]),
            "disciplines": list(set(
                [c["element_1_discipline"] for c in self.clashes] +
                [c["element_2_discipline"] for c in self.clashes]
            ))
        }