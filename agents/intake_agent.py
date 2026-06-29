import logging
from typing import Any, Dict
from core.state_manager import StateManager
from tools.ifc_parser import IFCParser

logger = logging.getLogger(__name__)

class IntakeAgent:
    def __init__(self, state_manager: StateManager):
        self.name = "IntakeAgent"
        self.state = state_manager

    def run(self, model_path: str) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Starting — model: {model_path}")
        self.state.update(pipeline_stage="intake", pipeline_status="running")

        parser = IFCParser(model_path)
        loaded = parser.load()

        if not loaded:
            self.state.update(pipeline_status="error")
            self.state.log_agent_action(
                self.name, "load_model", "Failed to load model", "error"
            )
            return {"success": False, "error": "Could not load model"}

        elements = parser.extract_elements()
        disciplines = parser.get_disciplines()

        self.state.update(
            model_path=model_path,
            total_elements=parser.get_element_count(),
            disciplines_detected=disciplines
        )

        self.state.log_agent_action(
            self.name,
            "parse_model",
            f"Extracted {len(elements)} elements across: {', '.join(disciplines)}",
            "success"
        )

        logger.info(f"[{self.name}] Complete — {len(elements)} elements found")
        return {
            "success": True,
            "elements": elements,
            "element_count": len(elements),
            "disciplines": disciplines
        }