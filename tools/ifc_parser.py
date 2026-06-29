import logging
import uuid
from typing import Any, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import ifcopenshell
    IFC_AVAILABLE = True
except ImportError:
    IFC_AVAILABLE = False
    logger.warning("ifcopenshell not available. Using mock data for development.")

class IFCParser:
    DISCIPLINE_MAP = {
        "IfcWall": "architectural",
        "IfcSlab": "structural",
        "IfcColumn": "structural",
        "IfcBeam": "structural",
        "IfcFoundation": "structural",
        "IfcDoor": "architectural",
        "IfcWindow": "architectural",
        "IfcStair": "architectural",
        "IfcRoof": "architectural",
        "IfcPipeSegment": "mep",
        "IfcDuctSegment": "mep",
        "IfcCableSegment": "mep",
        "IfcFlowTerminal": "mep",
        "IfcFlowFitting": "mep",
        "IfcPump": "mep",
        "IfcBoiler": "mep",
        "IfcFan": "mep",
        "IfcLightFixture": "mep",
        "IfcSite": "civil",
        "IfcRoad": "civil",
    }

    def __init__(self, model_path: str):
        self.model_path = Path(model_path)
        self.model = None
        self.elements = []
        self.disciplines = set()

    def load(self) -> bool:
        if not IFC_AVAILABLE:
            logger.info("ifcopenshell not available — running in mock mode")
            self._generate_mock_data()
            return True
        if not self.model_path.exists():
            logger.warning(f"Model file not found: {self.model_path} — running in mock mode")
            self._generate_mock_data()
            return True
        try:
            self.model = ifcopenshell.open(str(self.model_path))
            logger.info(f"IFC model loaded: {self.model_path.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to load IFC model: {e}")
            self._generate_mock_data()
            return True

    def extract_elements(self) -> List[Dict[str, Any]]:
        if self.model is None:
            return self.elements
        for ifc_type, discipline in self.DISCIPLINE_MAP.items():
            try:
                entities = self.model.by_type(ifc_type)
                for entity in entities:
                    element = {
                        "id": str(entity.GlobalId),
                        "type": ifc_type,
                        "name": entity.Name or f"{ifc_type}_{entity.id()}",
                        "discipline": discipline,
                        "properties": self._extract_properties(entity),
                        "location": self._extract_location(entity)
                    }
                    self.elements.append(element)
                    self.disciplines.add(discipline)
            except Exception as e:
                logger.warning(f"Could not extract {ifc_type}: {e}")
        logger.info(f"Extracted {len(self.elements)} elements across {len(self.disciplines)} disciplines")
        return self.elements

    def _extract_properties(self, entity) -> Dict[str, Any]:
        props = {}
        try:
            for rel in entity.IsDefinedBy:
                if rel.is_a("IfcRelDefinesByProperties"):
                    prop_set = rel.RelatingPropertyDefinition
                    if prop_set.is_a("IfcPropertySet"):
                        for prop in prop_set.HasProperties:
                            if hasattr(prop, "NominalValue") and prop.NominalValue:
                                props[prop.Name] = prop.NominalValue.wrappedValue
        except Exception:
            pass
        return props

    def _extract_location(self, entity) -> Dict[str, float]:
        try:
            placement = entity.ObjectPlacement
            if placement and hasattr(placement, "RelativePlacement"):
                loc = placement.RelativePlacement.Location
                if loc:
                    coords = loc.Coordinates
                    return {
                        "x": round(coords[0], 3),
                        "y": round(coords[1], 3),
                        "z": round(coords[2], 3)
                    }
        except Exception:
            pass
        return {"x": 0.0, "y": 0.0, "z": 0.0}

    def _generate_mock_data(self):
        mock_elements = [
            {
                "id": str(uuid.uuid4()),
                "type": "IfcColumn",
                "name": "COL-001",
                "discipline": "structural",
                "properties": {"LoadBearing": True, "Material": "Concrete M25"},
                "location": {"x": 5.0, "y": 0.0, "z": 0.0}
            },
            {
                "id": str(uuid.uuid4()),
                "type": "IfcColumn",
                "name": "COL-002",
                "discipline": "structural",
                "properties": {"LoadBearing": True, "Material": "Concrete M25"},
                "location": {"x": 10.0, "y": 0.0, "z": 0.0}
            },
            {
                "id": str(uuid.uuid4()),
                "type": "IfcBeam",
                "name": "BM-001",
                "discipline": "structural",
                "properties": {"LoadBearing": True, "Material": "Steel IS 2062"},
                "location": {"x": 7.5, "y": 0.0, "z": 3.0}
            },
            {
                "id": str(uuid.uuid4()),
                "type": "IfcDuctSegment",
                "name": "HVAC-DUCT-001",
                "discipline": "mep",
                "properties": {"FlowRate": "500 CFM", "Size": "600x400"},
                "location": {"x": 7.5, "y": 0.0, "z": 3.1}
            },
            {
                "id": str(uuid.uuid4()),
                "type": "IfcPipeSegment",
                "name": "PIPE-CW-001",
                "discipline": "mep",
                "properties": {"Diameter": "150mm", "FluidType": "Chilled Water"},
                "location": {"x": 5.0, "y": 1.0, "z": 3.0}
            },
            {
                "id": str(uuid.uuid4()),
                "type": "IfcWall",
                "name": "WALL-EXT-001",
                "discipline": "architectural",
                "properties": {"IsExternal": True, "Material": "Brick 230mm"},
                "location": {"x": 0.0, "y": 0.0, "z": 0.0}
            },
            {
                "id": str(uuid.uuid4()),
                "type": "IfcSlab",
                "name": "SLAB-01",
                "discipline": "structural",
                "properties": {"Thickness": 150, "Material": "Concrete M30"},
                "location": {"x": 0.0, "y": 0.0, "z": 3.0}
            },
            {
                "id": str(uuid.uuid4()),
                "type": "IfcPipeSegment",
                "name": "PIPE-SS-001",
                "discipline": "mep",
                "properties": {"Diameter": "100mm", "FluidType": "Sanitary"},
                "location": {"x": 10.0, "y": 2.0, "z": 3.05}
            },
        ]
        self.elements = mock_elements
        self.disciplines = {"structural", "mep", "architectural"}
        logger.info(f"Mock data generated: {len(self.elements)} elements")

    def get_disciplines(self) -> List[str]:
        return list(self.disciplines)

    def get_element_count(self) -> int:
        return len(self.elements)

    def get_elements_by_discipline(self, discipline: str) -> List[Dict]:
        return [e for e in self.elements if e["discipline"] == discipline]