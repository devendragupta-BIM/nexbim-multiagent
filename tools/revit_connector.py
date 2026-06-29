import logging
import json
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

REVIT_AVAILABLE = False
try:
    import clr
    clr.AddReference("RevitAPI")
    clr.AddReference("RevitAPIUI")
    from Autodesk.Revit.DB import (
        FilteredElementCollector,
        BuiltInCategory,
        ElementId,
        Transaction,
        TransactionGroup,
        XYZ,
        ElementTransformUtils,
        BoundingBoxXYZ,
        BuiltInParameter
    )
    REVIT_AVAILABLE = True
    logger.info("Revit API connected successfully")
except Exception as e:
    logger.warning(f"Revit API not available: {e} — running in simulation mode")


class RevitConnector:
    def __init__(self, doc=None, uidoc=None):
        self.doc = doc
        self.uidoc = uidoc
        self.available = REVIT_AVAILABLE and doc is not None
        self.executed_fixes = []
        self.failed_fixes = []

    def get_all_elements(self) -> List[Dict[str, Any]]:
        if not self.available:
            logger.info("Revit not available — returning empty list")
            return []
        elements = []
        try:
            collector = FilteredElementCollector(self.doc)\
                .WhereElementIsNotElementType()
            for elem in collector:
                try:
                    bbox = elem.get_BoundingBox(None)
                    location = {"x": 0.0, "y": 0.0, "z": 0.0}
                    if bbox:
                        center = (bbox.Min + bbox.Max) * 0.5
                        location = {
                            "x": round(center.X * 0.3048, 3),
                            "y": round(center.Y * 0.3048, 3),
                            "z": round(center.Z * 0.3048, 3)
                        }
                    elements.append({
                        "id": str(elem.Id.IntegerValue),
                        "name": elem.Name or f"Element_{elem.Id}",
                        "type": elem.GetType().Name,
                        "category": str(elem.Category.Name)
                        if elem.Category else "Unknown",
                        "location": location
                    })
                except Exception:
                    continue
        except Exception as e:
            logger.error(f"Error collecting elements: {e}")
        return elements

    def move_element(self, element_id: str,
                     translation: Dict[str, float],
                     description: str = "") -> bool:
        if not self.available:
            logger.info(
                f"[SIMULATION] Would move element {element_id} "
                f"by {translation}"
            )
            self.executed_fixes.append({
                "element_id": element_id,
                "action": "move",
                "translation": translation,
                "description": description,
                "status": "simulated"
            })
            return True
        try:
            elem_id = ElementId(int(element_id))
            elem = self.doc.GetElement(elem_id)
            if not elem:
                logger.error(f"Element {element_id} not found")
                return False
            move_vec = XYZ(
                translation.get("x", 0) / 0.3048,
                translation.get("y", 0) / 0.3048,
                translation.get("z", 0) / 0.3048
            )
            with Transaction(self.doc, f"NexBIM: {description}") as t:
                t.Start()
                ElementTransformUtils.MoveElement(
                    self.doc, elem_id, move_vec
                )
                t.Commit()
            self.executed_fixes.append({
                "element_id": element_id,
                "action": "move",
                "translation": translation,
                "description": description,
                "status": "executed"
            })
            logger.info(f"Moved element {element_id} successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to move element {element_id}: {e}")
            self.failed_fixes.append({
                "element_id": element_id,
                "error": str(e)
            })
            return False

    def set_parameter(self, element_id: str,
                      param_name: str, value: Any) -> bool:
        if not self.available:
            logger.info(
                f"[SIMULATION] Would set {param_name} = {value} "
                f"on element {element_id}"
            )
            self.executed_fixes.append({
                "element_id": element_id,
                "action": "set_parameter",
                "parameter": param_name,
                "value": value,
                "status": "simulated"
            })
            return True
        try:
            elem_id = ElementId(int(element_id))
            elem = self.doc.GetElement(elem_id)
            if not elem:
                return False
            param = elem.LookupParameter(param_name)
            if not param:
                logger.warning(
                    f"Parameter {param_name} not found on {element_id}"
                )
                return False
            with Transaction(
                self.doc,
                f"NexBIM: Set {param_name}"
            ) as t:
                t.Start()
                if isinstance(value, str):
                    param.Set(value)
                elif isinstance(value, (int, float)):
                    param.Set(float(value))
                t.Commit()
            self.executed_fixes.append({
                "element_id": element_id,
                "action": "set_parameter",
                "parameter": param_name,
                "value": value,
                "status": "executed"
            })
            return True
        except Exception as e:
            logger.error(f"Failed to set parameter: {e}")
            self.failed_fixes.append({
                "element_id": element_id,
                "error": str(e)
            })
            return False

    def get_execution_summary(self) -> Dict[str, Any]:
        return {
            "total_executed": len(self.executed_fixes),
            "total_failed": len(self.failed_fixes),
            "executed_fixes": self.executed_fixes,
            "failed_fixes": self.failed_fixes,
            "mode": "live" if self.available else "simulation"
        }