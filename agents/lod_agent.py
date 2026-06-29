import logging
import uuid
from typing import Any, Dict, List
from core.state_manager import StateManager, LODViolation

logger = logging.getLogger(__name__)

LOD_REQUIREMENTS = {
    "IfcColumn": {
        "required_lod": 300,
        "required_attributes": [
            "LoadBearing", "Material", "CrossSectionWidth",
            "CrossSectionHeight", "Height"
        ]
    },
    "IfcBeam": {
        "required_lod": 300,
        "required_attributes": [
            "LoadBearing", "Material", "CrossSectionWidth",
            "CrossSectionHeight", "Span"
        ]
    },
    "IfcSlab": {
        "required_lod": 300,
        "required_attributes": [
            "Thickness", "Material", "LoadBearing", "SpanDirection"
        ]
    },
    "IfcWall": {
        "required_lod": 200,
        "required_attributes": [
            "IsExternal", "Material", "Width", "Height"
        ]
    },
    "IfcDuctSegment": {
        "required_lod": 300,
        "required_attributes": [
            "FlowRate", "Size", "Material", "InsulationThickness",
            "SystemType"
        ]
    },
    "IfcPipeSegment": {
        "required_lod": 300,
        "required_attributes": [
            "Diameter", "Material", "FluidType",
            "WallThickness", "Insulation"
        ]
    },
    "IfcDoor": {
        "required_lod": 200,
        "required_attributes": [
            "Width", "Height", "Material", "FireRating"
        ]
    },
    "IfcWindow": {
        "required_lod": 200,
        "required_attributes": [
            "Width", "Height", "GlazingType", "UValue"
        ]
    }
}

LOD_SCORE_MAP = {
    0: 100,
    1: 90,
    2: 75,
    3: 60,
    4: 40,
    5: 20
}


class LODAgent:
    def __init__(self, state_manager: StateManager):
        self.name = "LODAgent"
        self.state = state_manager

    def _check_lod(self, element: Dict) -> Dict[str, Any]:
        element_type = element.get("type", "")
        requirements = LOD_REQUIREMENTS.get(element_type)

        if not requirements:
            return {"has_violation": False}

        props = element.get("properties", {})
        required_attrs = requirements["required_attributes"]
        required_lod = requirements["required_lod"]
        missing = [a for a in required_attrs if a not in props or not props[a]]

        if not missing:
            return {"has_violation": False}

        total = len(required_attrs)
        present = total - len(missing)
        completeness = present / total

        if completeness >= 0.8:
            actual_lod = required_lod - 50
            severity = "minor"
        elif completeness >= 0.6:
            actual_lod = required_lod - 100
            severity = "major"
        else:
            actual_lod = required_lod - 150
            severity = "critical"

        return {
            "has_violation": True,
            "required_lod": required_lod,
            "actual_lod": max(actual_lod, 100),
            "missing_attributes": missing,
            "severity": severity,
            "completeness_percent": round(completeness * 100, 1)
        }

    def run(self, elements: List[Dict[str, Any]]) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Starting LOD check on {len(elements)} elements")
        self.state.update(pipeline_stage="lod_check")

        violations = []
        critical = []
        major = []
        minor = []

        for element in elements:
            result = self._check_lod(element)
            if result["has_violation"]:
                violation = LODViolation(
                    element_id=element["id"],
                    element_type=element["type"],
                    required_lod=result["required_lod"],
                    actual_lod=result["actual_lod"],
                    missing_attributes=result["missing_attributes"],
                    severity=result["severity"]
                )
                self.state.add_lod_violation(violation)
                violations.append({
                    "element_name": element["name"],
                    "element_type": element["type"],
                    "discipline": element["discipline"],
                    "required_lod": result["required_lod"],
                    "actual_lod": result["actual_lod"],
                    "missing_attributes": result["missing_attributes"],
                    "severity": result["severity"],
                    "completeness": result["completeness_percent"]
                })
                if result["severity"] == "critical":
                    critical.append(violation)
                elif result["severity"] == "major":
                    major.append(violation)
                else:
                    minor.append(violation)

        self.state.log_agent_action(
            self.name,
            "check_lod",
            (f"Found {len(violations)} LOD violations — "
             f"Critical: {len(critical)}, "
             f"Major: {len(major)}, "
             f"Minor: {len(minor)}"),
            "success"
        )

        logger.info(f"[{self.name}] Complete — {len(violations)} LOD violations found")
        return {
            "success": True,
            "total_violations": len(violations),
            "critical": len(critical),
            "major": len(major),
            "minor": len(minor),
            "violations": violations
        }